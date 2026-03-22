# Update 3.22 变更记录

本目录用于归档本轮对话中的重构与优化结果。

## 本次完成的主要改动

- 重构 `screens/ocr_screen.py` 文件列表渲染逻辑：
  - 引入异步分批渲染（每批 30 个，`after(20, ...)`）。
  - 增加渲染会话锁（`_list_render_id`）防止刷新冲突。
  - 增加列表底部加载进度标签（如 `正在加载文件列表 (30/1000)...`）。
  - 保留并优化自动选中逻辑，首批或目标批次出现即触发。

- 引入 OCR 状态机（State Machine）：
  - 新增 `OcrState` 枚举：`IDLE/RUNNING/DONE/ERROR/CANCELLED`。
  - 新增 `_update_ui_by_state()` 统一接管按钮/文件列表可用性。
  - 新增 `_set_ocr_state()`，保证跨线程状态更新通过主线程执行。

- 优化 OCR 缓存可见化与精细控制：
  - 左侧 PDF 列表增加 `🟢 [已缓存]` 标记。
  - “清空缓存”升级为“删除全部缓存”，加入严重警告确认框。
  - 新增“删除当前缓存”按钮与逻辑。
  - 新增“强制重新识别”按钮与逻辑（删除当前缓存后立即重跑 OCR）。
  - 删除当前缓存后，右侧 OCR 文本区与状态提示会即时重置。

- 统一设计令牌（Design Tokens）：
  - 在 `config/settings.py` 的 `Color` 中新增并整理语义化颜色常量。
  - `screens/` 与 `components/` 中 UI 颜色从硬编码切换为 `Color` 引用。
  - 覆盖了单色与明暗元组色值场景。

- 审美向 UI 优化：
  - 全局按钮圆角加大（更圆润）。
  - 按钮色系统一为蓝色系，并确保文字对比度可读。
  - 导航与列表按钮的圆角/高亮风格同步统一。

- 启动稳定性修复：
  - 修复 `components/ui/button.py` 中默认颜色参数与外部传参冲突问题。
  - 使用 `kwargs.setdefault(...)` 设置默认 `text_color/fg_color/hover_color`。

- Gemini SDK 迁移到新版 V2：
  - `ocr_screen.py` 从 `google-generativeai` 迁移到 `google-genai`。
  - 替换为 `from google import genai` 与 `from google.genai import types`。
  - `_detect_text_from_image()` 改用 `genai.Client(api_key=...)`。
  - 请求发送改用 `client.models.generate_content(...)`。
  - 安全设置改为 `types.GenerateContentConfig(safety_settings=[...])` 新格式。

- 文档更新：
  - 重写项目根目录 `README.md`，使其与当前实现保持一致（功能、启动、缓存与安全说明）。

## 说明

- 本次改动集中在 UI 体验、稳定性与 OCR 工作流重构。
- 未改动核心抓取业务逻辑（`core_scraper.py` 的主流程保持原样）。
