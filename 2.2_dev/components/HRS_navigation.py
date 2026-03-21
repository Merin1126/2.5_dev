import customtkinter as ctk

class Navigation(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        # 继承原作者的深色导航栏风格
        super().__init__(master, width=220, corner_radius=0, fg_color="#212121", **kwargs)
        self.master = master

        # ================= 顶部 Logo/标题区 =================
        self.title_label = ctk.CTkLabel(
            self, text="HRS V2.2", 
            font=("Arial", 26, "bold"), text_color="white"
        )
        self.title_label.pack(pady=(40, 30))

        # ================= 中间 导航按钮区 =================
        # 我们使用 CTkButton 完美复刻原作者的 Button 样式
        self.btn_scraper = ctk.CTkButton(
            self, text="🚀  史料高并发抓取", font=("Arial", 15, "bold"),
            fg_color="transparent", text_color="gray", hover_color="#333333",
            height=45, anchor="w", command=lambda: self.navigate("scraper")
        )
        self.btn_scraper.pack(pady=5, padx=15, fill="x")

        self.btn_ocr = ctk.CTkButton(
            self, text="👁️  史料 OCR 校对", font=("Arial", 15, "bold"),
            fg_color="transparent", text_color="gray", hover_color="#333333",
            height=45, anchor="w", command=lambda: self.navigate("ocr")
        )
        self.btn_ocr.pack(pady=5, padx=15, fill="x")
        
        self.btn_setting = ctk.CTkButton(
            self, text="⚙️  系统与环境设置", font=("Arial", 15, "bold"),
            fg_color="transparent", text_color="gray", hover_color="#333333",
            height=45, anchor="w", command=lambda: self.navigate("setting")
        )
        self.btn_setting.pack(pady=5, padx=15, fill="x")

        # ================= 底部 主题切换区 =================
        # 保留原作者切换 Light/Dark 的优良传统
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            self, values=["System", "Dark", "Light"],
            command=self.change_appearance_mode_event,
            fg_color="#333333", button_color="#1F6AA5"
        )
        self.appearance_mode_menu.pack(side="bottom", pady=30, padx=15, fill="x")

    def navigate(self, screen_name: str) -> None:
        """
        核心路由与按钮高亮逻辑（致敬原代码的 getObjectNavButtonCurrentScreen）
        """
        # 1. 重置所有按钮为未激活状态 (暗灰色)
        for btn in [self.btn_scraper, self.btn_ocr, self.btn_setting]:
            btn.configure(fg_color="transparent", text_color="gray")

        # 2. 高亮当前点击的按钮 (亮蓝色底，白字)
        if screen_name == "scraper":
            self.btn_scraper.configure(fg_color="#1F6AA5", text_color="white")
        elif screen_name == "ocr":
            self.btn_ocr.configure(fg_color="#1F6AA5", text_color="white")
        elif screen_name == "setting":
            self.btn_setting.configure(fg_color="#1F6AA5", text_color="white")

        # 3. 通知右侧的“屏幕大管家”切换页面
        if hasattr(self.master, "screen_manager"):
            self.master.screen_manager.change_screen(screen_name)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        """处理主题颜色切换"""
        ctk.set_appearance_mode(new_appearance_mode)