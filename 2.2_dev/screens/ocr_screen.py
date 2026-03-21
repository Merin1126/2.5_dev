import os
import sys
import subprocess
import json
import base64
import threading
import hashlib
from urllib import request, error
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageTk
from docx import Document

from components.ui.button import Button
from config.api_key_store import load_google_api_key

class OCRScreen(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.master = master
        self.google_api_key = os.getenv("GOOGLE_VISION_API_KEY", "").strip()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.download_dir = os.path.join(base_dir, "JACAR_Downloads")
        self.ocr_cache_dir = os.path.join(base_dir, "OCR_Cache")
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        if not os.path.exists(self.ocr_cache_dir):
            os.makedirs(self.ocr_cache_dir)

        self.current_pdf = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.tk_image = None
        self.current_image_item = None
        self.pdf_files = []
        self.selected_pdf_path = None
        self.ocr_cancel_event = threading.Event()
        self.ocr_task_id = 0

        self._setup_ui()
        self._load_file_list()

    def _setup_ui(self):
        self.paned_window = tk.PanedWindow(
            self, 
            orient="horizontal", 
            bg="#1a1a1a",
            sashwidth=8,
            sashrelief="flat",
            sashcursor="sb_h_double_arrow",
            borderwidth=0
        )
        self.paned_window.pack(fill="both", expand=True, padx=5, pady=5)

        self.left_frame = ctk.CTkFrame(self.paned_window, corner_radius=10)
        self.paned_window.add(self.left_frame, minsize=150, stretch="always")
        
        ctk.CTkLabel(self.left_frame, text="📁 史料文件库", font=("Arial", 16, "bold")).pack(pady=10)
        
        list_container = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        list_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.v_scrollbar = ctk.CTkScrollbar(list_container, orientation="vertical")
        self.h_scrollbar = ctk.CTkScrollbar(list_container, orientation="horizontal")
        
        self.file_listbox = tk.Listbox(
            list_container, 
            yscrollcommand=self.v_scrollbar.set,
            xscrollcommand=self.h_scrollbar.set,
            bg="#2b2b2b", fg="white", selectbackground="#1F6AA5",
            font=("Arial", 12), borderwidth=0, highlightthickness=0
        )
        
        self.v_scrollbar.configure(command=self.file_listbox.yview)
        self.h_scrollbar.configure(command=self.file_listbox.xview)
        
        self.v_scrollbar.pack(side="right", fill="y")
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.file_listbox.pack(side="left", fill="both", expand=True)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        list_action_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        list_action_frame.pack(fill="x", padx=8, pady=(0, 10))

        Button(
            list_action_frame,
            text="打开史料文件库",
            height=38,
            command=self.open_download_folder
        ).pack(fill="x", pady=(0, 6))

        Button(
            list_action_frame,
            text="刷新列表",
            height=38,
            command=self.refresh_file_list
        ).pack(fill="x")

        self.mid_frame = ctk.CTkFrame(self.paned_window, corner_radius=10)
        self.paned_window.add(self.mid_frame, minsize=400, stretch="always")
        
        toolbar = ctk.CTkFrame(self.mid_frame, fg_color="transparent")
        toolbar.pack(fill="x", pady=5, padx=5)
        
        Button(toolbar, text="➖ 缩小", width=60, height=30, command=self.zoom_out).pack(side="left", padx=5)
        Button(toolbar, text="➕ 放大", width=60, height=30, command=self.zoom_in).pack(side="left", padx=5)
        
        self.page_label = ctk.CTkLabel(toolbar, text="页码: 0 / 0", font=("Arial", 13, "bold"))
        self.page_label.pack(side="left", expand=True)
        
        Button(toolbar, text="◀ 上一页", width=80, height=30, command=self.prev_page).pack(side="left", padx=5)
        Button(toolbar, text="▶ 下一页", width=80, height=30, command=self.next_page).pack(side="left", padx=5)
        
        self.canvas = tk.Canvas(self.mid_frame, bg="#2b2b2b", highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_motion)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.right_frame = ctk.CTkFrame(self.paned_window, corner_radius=10)
        self.paned_window.add(self.right_frame, minsize=200, stretch="always")
        
        ctk.CTkLabel(self.right_frame, text="📝 OCR 文字校对区", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.text_editor = ctk.CTkTextbox(self.right_frame, wrap="word", font=("Arial", 14), corner_radius=8)
        self.text_editor.pack(fill="both", expand=True, padx=10, pady=10)
        self.text_editor.insert("0.0", "👈 请在左侧选择一份已下载的史料 PDF 文件。\n\n此处将显示 Google API 提取的文本...")

        self.ocr_progress_label = ctk.CTkLabel(
            self.right_frame,
            text="OCR 状态：等待选择文件",
            font=("Arial", 12)
        )
        self.ocr_progress_label.pack(fill="x", padx=10, pady=(0, 8))

        self.ocr_progress_bar = ctk.CTkProgressBar(self.right_frame)
        self.ocr_progress_bar.pack(fill="x", padx=10, pady=(0, 10))
        self.ocr_progress_bar.set(0)

        self.btn_start_ocr = Button(
            self.right_frame,
            text="开始 OCR 识别",
            fg_color="#15803d",
            hover_color="#166534",
            width=200,
            height=40,
            command=self.start_ocr_recognition
        )
        self.btn_start_ocr.pack(pady=(0, 10), padx=10, fill="x")

        self.btn_cancel_ocr = Button(
            self.right_frame,
            text="取消任务",
            fg_color="#b45309",
            hover_color="#92400e",
            width=200,
            height=40,
            command=self.cancel_ocr_task
        )
        self.btn_cancel_ocr.pack(pady=(0, 10), padx=10, fill="x")

        self.btn_clear_cache = Button(
            self.right_frame,
            text="清空缓存",
            fg_color="#4b5563",
            hover_color="#374151",
            width=200,
            height=40,
            command=self.clear_ocr_cache
        )
        self.btn_clear_cache.pack(pady=(0, 10), padx=10, fill="x")

        self.btn_export = Button(
            self.right_frame, text="💾 确认并导出文档", 
            fg_color="#1F6AA5", hover_color="#144870",
            width=200, height=45, command=self.export_document
        )
        self.btn_export.pack(pady=15, padx=10, fill="x")

    def _load_file_list(self):
        self.file_listbox.delete(0, tk.END)
        self.pdf_files.clear()
        
        if not os.path.exists(self.download_dir): return

        pdf_list = [f for f in os.listdir(self.download_dir) if f.lower().endswith('.pdf')]
        pdf_list.sort()

        for index, filename in enumerate(pdf_list, start=1):
            file_path = os.path.join(self.download_dir, filename)
            self.pdf_files.append(file_path)
            display_text = f"   {index}. {filename}"
            self.file_listbox.insert(tk.END, display_text)

    def refresh_file_list(self):
        """手动刷新左侧文件列表"""
        self._load_file_list()
        messagebox.showinfo("提示", "史料文件库列表已刷新。")

    def open_download_folder(self):
        """在系统文件管理器中打开史料文件库目录"""
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

        try:
            if sys.platform.startswith("darwin"):
                subprocess.run(["open", self.download_dir], check=True)
            elif os.name == "nt":
                os.startfile(self.download_dir)
            else:
                subprocess.run(["xdg-open", self.download_dir], check=True)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹:\n{e}")
            
    def on_file_select(self, event):
        """处理列表点击事件"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            file_path = self.pdf_files[index]
            self.open_pdf(file_path)

    def open_pdf(self, file_path):
        self.cancel_ocr_task(silent=True)

        if self.current_pdf:
            self.current_pdf.close()
        try:
            self.current_pdf = fitz.open(file_path)
            self.current_page = 0
            self.zoom_factor = 1.0
            self.selected_pdf_path = file_path
            self.render_page()

            self.text_editor.delete("0.0", "end")
            self.text_editor.insert("0.0", f"已加载文件：{os.path.basename(file_path)}\n点击“开始 OCR 识别”后将调用 Google API。")
            self.ocr_progress_label.configure(text="OCR 状态：文件已就绪，等待开始")
            self.ocr_progress_bar.set(0)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开 PDF 文件: {e}")

    def start_ocr_recognition(self):
        if not self.selected_pdf_path:
            messagebox.showwarning("提示", "请先在左侧选择一个 PDF 文件。")
            return
        self.ocr_task_id += 1
        task_id = self.ocr_task_id
        self.ocr_cancel_event = threading.Event()
        self.text_editor.delete("0.0", "end")
        self.text_editor.insert("0.0", f"正在调用 Google API 提取 {os.path.basename(self.selected_pdf_path)} 的文字...\n请稍候，正在逐页识别。")
        self.ocr_progress_label.configure(text="OCR 状态：准备开始")
        self.ocr_progress_bar.set(0)
        self._start_ocr_worker(self.selected_pdf_path, task_id)

    def _start_ocr_worker(self, file_path, task_id):
        worker = threading.Thread(target=self._run_ocr_worker, args=(file_path, task_id), daemon=True)
        worker.start()

    def _run_ocr_worker(self, file_path, task_id):
        try:
            ocr_text, from_cache = self._extract_text_with_google_ocr(file_path, task_id)
            self.after(0, lambda: self._show_ocr_text_result(ocr_text, task_id, from_cache))
        except RuntimeError as e:
            err_msg = str(e)
            if str(e) == "OCR_CANCELLED":
                self.after(0, lambda: self._handle_ocr_cancelled(task_id))
                return
            self.after(0, lambda msg=err_msg: self._handle_ocr_failed(task_id, msg))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._handle_ocr_failed(task_id, msg))

    def _show_ocr_text_result(self, ocr_text, task_id, from_cache):
        if task_id != self.ocr_task_id:
            return
        self.text_editor.delete("0.0", "end")
        if ocr_text.strip():
            self.text_editor.insert("0.0", ocr_text)
        else:
            self.text_editor.insert("0.0", "未识别到文本内容。")
        if from_cache:
            self.ocr_progress_label.configure(text="OCR 状态：已完成（来自本地缓存）")
            self.ocr_progress_bar.set(1)
        else:
            self.ocr_progress_label.configure(text="OCR 状态：已完成")
            self.ocr_progress_bar.set(1)

    def _handle_ocr_cancelled(self, task_id):
        if task_id != self.ocr_task_id:
            return
        self.ocr_progress_label.configure(text="OCR 状态：已取消")
        self.ocr_progress_bar.set(0)
        self.text_editor.delete("0.0", "end")
        self.text_editor.insert("0.0", "OCR 任务已取消，已清理本次半成品文本。")

    def _handle_ocr_failed(self, task_id, reason):
        if task_id != self.ocr_task_id:
            return
        self.ocr_progress_label.configure(text="OCR 状态：失败")
        self.ocr_progress_bar.set(0)
        messagebox.showerror("OCR 失败", reason)
        self.text_editor.insert("end", "\n\nOCR 失败，请检查网络连接和 GOOGLE_VISION_API_KEY 配置。")

    def _extract_text_with_google_ocr(self, pdf_path, task_id):
        api_key = os.getenv("GOOGLE_VISION_API_KEY", "").strip() or load_google_api_key()
        if not api_key:
            raise RuntimeError("未检测到 GOOGLE_VISION_API_KEY。请先在系统环境变量中配置后再使用 OCR。")

        cache_path = self._build_cache_path(pdf_path)
        if os.path.exists(cache_path):
            self.after(0, lambda: self.ocr_progress_label.configure(text="OCR 状态：读取本地缓存中..."))
            self.after(0, lambda: self.ocr_progress_bar.set(1))
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read(), True

        with fitz.open(pdf_path) as doc:
            if len(doc) == 0:
                return "", False

            all_text_parts = []
            total_pages = len(doc)
            for page_index in range(total_pages):
                self._ensure_active_task(task_id)
                self._update_ocr_progress(task_id, page_index, total_pages)
                page = doc[page_index]

                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                image_bytes = pix.tobytes("png")
                page_text = self._detect_text_from_image(image_bytes, api_key)

                title = f"\n\n===== 第 {page_index + 1} / {total_pages} 页 =====\n"
                all_text_parts.append(title + (page_text.strip() if page_text else "（本页未识别到文本）"))

        result_text = "".join(all_text_parts).strip()
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(result_text)
        return result_text, False

    def _build_cache_path(self, pdf_path):
        stat = os.stat(pdf_path)
        cache_key = f"{pdf_path}|{stat.st_mtime_ns}|{stat.st_size}"
        name = hashlib.sha256(cache_key.encode("utf-8")).hexdigest() + ".txt"
        return os.path.join(self.ocr_cache_dir, name)

    def _ensure_active_task(self, task_id):
        if task_id != self.ocr_task_id or self.ocr_cancel_event.is_set():
            raise RuntimeError("OCR_CANCELLED")

    def _update_ocr_progress(self, task_id, page_index, total_pages):
        if task_id != self.ocr_task_id:
            return
        text = f"OCR 状态：正在识别第 {page_index + 1} / {total_pages} 页"
        self.after(0, lambda: self.ocr_progress_label.configure(text=text))
        ratio = 0 if total_pages <= 0 else ((page_index + 1) / total_pages)
        self.after(0, lambda: self.ocr_progress_bar.set(ratio))

    def cancel_ocr_task(self, silent=False):
        self.ocr_cancel_event.set()
        if not silent:
            self.ocr_progress_label.configure(text="OCR 状态：正在取消...")
            self.ocr_progress_bar.set(0)

    def clear_ocr_cache(self):
        if not os.path.exists(self.ocr_cache_dir):
            os.makedirs(self.ocr_cache_dir)
            messagebox.showinfo("提示", "缓存目录不存在，已自动创建。")
            return

        removed_count = 0
        failed_count = 0
        for filename in os.listdir(self.ocr_cache_dir):
            path = os.path.join(self.ocr_cache_dir, filename)
            if not os.path.isfile(path):
                continue
            try:
                os.remove(path)
                removed_count += 1
            except OSError:
                failed_count += 1

        if failed_count > 0:
            messagebox.showwarning("提示", f"已清理 {removed_count} 个缓存文件，另有 {failed_count} 个文件删除失败。")
            return
        messagebox.showinfo("提示", f"缓存已清空，共删除 {removed_count} 个文件。")

    def _detect_text_from_image(self, image_bytes, api_key):
        endpoint = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "requests": [
                {
                    "image": {"content": encoded},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
                }
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as http_err:
            detail = http_err.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Google OCR 请求失败（HTTP {http_err.code}）: {detail}") from http_err
        except Exception as e:
            raise RuntimeError(f"Google OCR 请求异常: {e}") from e

        responses = body.get("responses", [])
        if not responses:
            return ""
        first = responses[0]
        if "error" in first:
            msg = first["error"].get("message", "未知错误")
            raise RuntimeError(f"Google OCR 返回错误: {msg}")

        full_text = first.get("fullTextAnnotation", {}).get("text", "")
        if full_text:
            return full_text

        legacy_text = first.get("textAnnotations", [])
        if legacy_text:
            return legacy_text[0].get("description", "")
        return ""

    def render_page(self):
        if not self.current_pdf: return
        page = self.current_pdf[self.current_page]
        self.page_label.configure(text=f"页码: {self.current_page + 1} / {len(self.current_pdf)}")
        
        mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=mat)
        
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        self.tk_image = ImageTk.PhotoImage(img)
        
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        cx = self.canvas.winfo_width() // 2
        cy = self.canvas.winfo_height() // 2
        self.current_image_item = self.canvas.create_image(cx, cy, anchor="center", image=self.tk_image)

    def on_drag_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def on_drag_motion(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_mouse_wheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        self.zoom_factor = min(5.0, self.zoom_factor + 0.2)
        self.render_page()

    def zoom_out(self):
        self.zoom_factor = max(0.4, self.zoom_factor - 0.2)
        self.render_page()

    def prev_page(self):
        if self.current_pdf and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def next_page(self):
        if self.current_pdf and self.current_page < len(self.current_pdf) - 1:
            self.current_page += 1
            self.render_page()

    def export_document(self):
        text_content = self.text_editor.get("0.0", "end").strip()
        if not text_content:
            messagebox.showwarning("提示", "导出内容为空！")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word 文档", "*.docx"), ("Markdown 文件", "*.md")],
            title="保存提取的文字"
        )
        if not file_path: return
            
        try:
            if file_path.endswith('.md'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
            elif file_path.endswith('.docx'):
                doc = Document()
                doc.add_paragraph(text_content)
                doc.save(file_path)
            messagebox.showinfo("成功", f"文件已成功保存至:\n{file_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"保存出错:\n{e}")