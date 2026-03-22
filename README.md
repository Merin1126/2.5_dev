这份 `README.md` 文档将作为你整个 HRS (Historical Records Scraper) 项目的“架构蓝图”和“进化史”。它不仅能帮你梳理思绪，未来如果项目开源或有其他开发者加入，他们也能通过这份文档一秒看懂你的代码库。

以下为你量身定制的 `README.md`，你可以直接将其保存在项目根目录下：

***

# 📚 HRS 史料全自动采集与 AI 校对系统 (v2.4)

**HRS (Historical Records Scraper)** 是一款专为近代史学者、档案研究人员打造的桌面端生产力软件。
本软件致力于解决日本亚洲历史资料中心（JACAR）等档案网站“批量下载难”的问题，并深度集成了 **Google Gemini 3.1 Pro** 大模型，实现了针对大正/昭和时代日文历史档案的“史料级” OCR 识别与排版还原。

---

## ✨ 核心特性 (Features)

* 🚀 **高并发史料抓取**：采用 Selenium（包工头） + 多线程纯 API 请求（打工人）的分离架构，无视繁琐的网页跳转，直接暴力拉取原始 PDF。
* 👁️ **史料级 AI OCR**：接入地表最强多模态大模型 `gemini-3.1-pro-preview`。内置史料级 Prompt 与“安全审查豁免（BLOCK_NONE）”特权，精准识别旧体字、繁体字与草书，保留历史语境，支持残缺字体智能推测与 `【?】` 标记。
* 💾 **智能分页与缓存系统**：采用 `paged_v1` 结构的 JSON 本地缓存。一次识别，永久保存。支持按页阅读、单页/全本导出（`.md` / `.docx`）。
* 🎨 **现代化 GUI 体验**：基于 CustomTkinter 构建。包含平滑折叠侧边栏（贝塞尔曲线动画）、虚拟异步列表渲染、全局 Design Token 控制，提供极佳的交互体验。

---

## 🗺️ 项目架构与模块关系 (Architecture)

本软件严格遵循 **前后端分离** 与 **模块化设计** 原则。项目目录结构及文件调用关系如下：

```text
HRS_Project/
│
├── HRS_app.py                  # 🏁【程序入口】总司令部，初始化窗口、导航栏与路由管家
├── core_scraper.py             # ⚙️【爬虫核心】完全脱离 UI 的纯后台业务逻辑（一号车间）
│
├── screens/                    # 📺【视图层】各大功能主界面
│   ├── HRS_manager.py          # 🔀 路由大管家：控制界面的切换与卸载
│   ├── scraper_screen.py       # 🚀 抓取控制台：接收参数，呼叫 core_scraper 干活
│   ├── ocr_screen.py           # 👁️ OCR 校对台：极其复杂的 PDF 渲染、Gemini 请求与缓存管理
│   └── setting_screen.py       # ⚙️ 系统设置页：用于填写 API Key
│
├── components/                 # 🧱【组件层】复用的 UI 零件
│   ├── HRS_navigation.py       # 🧭 左侧动态折叠导航栏（带动画引擎）
│   └── ui/
│       ├── button.py           # 封装的标准化圆角按钮
│       └── input.py            # 封装的标准化输入框（带回调追踪）
│
└── config/                     # 🛠️【配置层】
    ├── settings.py             # 🎨 全局调色盘 (Color Tokens) 与路由枚举
    └── api_key_store.py        # 🔒 API 秘钥保险箱：负责在 .secrets/ 目录加密存取密钥
```

### 🔍 核心文件关系说明：
1. **视图与后台的隔离**：`scraper_screen.py` 中绝不包含具体的下载逻辑，它只负责组装用户输入的参数，并通过 `threading.Thread` 将任务扔给 `core_scraper.jacar_auto_search` 去后台执行。
2. **状态与渲染的分离**：在 `ocr_screen.py` 中，PDF 的渲染（PyMuPDF/fitz）、API 的网络请求（Gemini）、以及 UI 的状态流转（状态机）被严格分离，确保在进行耗时的网络 OCR 识别时，主界面绝不卡死白屏。
3. **全局样式控制**：所有 UI 组件不再硬编码颜色，而是统一向 `config/settings.py` 索要颜色 Token。

---

## 📈 版本更迭记录 (Changelog)

### v2.4 (当前版本) - 性能与体验的飞跃
* **重构**：引入全局设计 Token（`config/settings.py`），彻底消灭 UI 代码中的硬编码颜色，实现风格统一。
* **重构**：对 `ocr_screen.py` 引入 **异步分批渲染（Batch Rendering）** 技术。解决左侧文件列表在面临海量 PDF（1000+）时引发的主线程卡死问题。
* **新增**：完善 OCR 任务控制状态机。在任务 `RUNNING` 时严格禁用侧边栏与其他无关文件按钮，杜绝多线程竞态崩溃。
* **新增**：**缓存可见化**。左侧列表动态标记 `🟢 [已缓存]`，并拆分“删除全部缓存”、“删除当前缓存”与“强制重新识别”按钮，极大提升用户容错率。
* **优化**：加入可平滑伸缩的左侧导航栏（`HRS_navigation.py`），附带 Ease-out 动画引擎。

### v2.3 - 史料 AI 引擎接入
* **新增**：彻底废弃传统云端 OCR，全面接入 `google-generativeai` 库，启用 `gemini-3.1-pro-preview` 大模型。
* **新增**：史料专用 Prompt 注入，并通过代码层面强行下调 `HarmBlockThreshold`，解决“支那”等历史名词触发 API 报错的问题。
* **新增**：引入 `paged_v1` 本地缓存协议，使用 PDF 路径 + 文件大小 + 修改时间计算 SHA256 哈希值，实现文件的唯一绑定与零延迟读取。
* **新增**：集成 PyMuPDF (`fitz`) 与 `Tkinter.Canvas`，实现原生内置的高清 PDF 阅读器，支持鼠标拖拽与滚轮缩放。

### v2.1/2.2 - 架构解耦与现代化 UI
* **重构**：将原本臃肿的几千行单文件代码，拆分为标准的 MVC 目录结构。
* **视觉**：废弃老旧的内置 Tkinter，全面拥抱 CustomTkinter，确立深色/浅色双轨模式与圆角扁平化设计语言。
* **新增**：增加 API Key 本地安全管理模块（`api_key_store.py`），防止密钥硬编码泄露。

---

## 🔒 隐私与安全说明
* 本软件所有的网络请求仅指向目标档案网站（JACAR）与 Google Gemini 官方 API。
* 用户填写的 `GOOGLE_VISION_API_KEY` 会被存储在项目根目录的隐藏文件夹 `.secrets/api_config.json` 中。
* **注意**：该目录已被加入 `.gitignore`，如果您 Fork 本项目，请务必不要将您的个人密钥上传至公共仓库！

---
*Developed by Merin | HRS Project 2026*