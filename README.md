# Translator Pro

基于 Python 3.10+ 与 customtkinter 的桌面端翻译软件示例工程，支持多 API 配置、Agent Prompt、DeepSeek/OpenAI-compatible 流式输出、reasoning_content 展示、文档后台翻译、术语库、历史记录、主题记忆与 PyInstaller 打包。

## 1. 安装运行

```bash
cd TranslatorPro
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

首次启动会在用户目录生成配置文件：

```text
~/.translator_pro/config.json
```

文档翻译输出目录：

```text
~/.translator_pro/outputs/
```

## 2. API 配置

菜单路径：`设置 → API 配置`。

内置三类 Provider：

- `openai_compatible`：适配 DeepSeek、OpenAI、豆包火山方舟兼容接口、OpenRouter、本地 vLLM/Ollama OpenAI-compatible 网关等。主路径完整支持流式增量和 DeepSeek 风格的 `reasoning_content`。
- `anthropic`：基础适配 Claude Messages API。
- `gemini`：基础适配 Google Gemini generateContent / streamGenerateContent。

每个 API 可配置：API 名称、Provider、Key、Base URL、模型、温度、max_tokens、是否启用、是否流式、是否支持 reasoning_content、HTTP/HTTPS 代理、超时时间。

## 3. Agent 配置

菜单路径：`设置 → Agent 配置`。

预设 Agent 包含：忠实还原、专利法律翻译、文学翻译、文言文翻译、技术文档翻译。每个 Agent 可绑定默认 API 和模型，也可修改系统提示词。

## 4. 文档翻译说明

支持导入：`.docx`、`.pdf`、`.txt`。`.doc` 为旧版二进制格式，程序会提示先转换为 `.docx`。

长文档超过默认 5000 字时会弹窗提醒并给出估算时间。文档翻译自动进入后台任务队列，可暂停、继续、取消。PDF 翻译以文本抽取为主，复杂版式无法保证完全保留。

## 5. 快捷键

- `Ctrl+Enter`：翻译
- `Ctrl+Shift+C`：复制译文

## 6. 打包

推荐先安装 UPX 并放入 PATH，然后使用 spec 打包：

```bash
pyinstaller build_translator_pro.spec --clean --noconfirm
```

体积优化措施：

- 使用 customtkinter，不引入重量级 WebView。
- spec 中排除 matplotlib、numpy、pandas、scipy、notebook、pytest 等非必要模块。
- 采用 onedir 模式更稳定，最终可手动压缩 dist/TranslatorPro。
- PDF 输出依赖 reportlab，如仅需 docx/txt 输出，可从 requirements 和 spec 中移除 reportlab 以进一步减小体积。

## 7. 重要限制

- 不同 API 厂商的响应字段差异较大。DeepSeek/OpenAI-compatible 是完整实现主路径；Claude/Gemini 为基础适配。
- 有些模型不返回 reasoning_content，界面会显示“该模型未返回 reasoning_content”。
- 拖拽上传依赖系统 Tk/TkDND 环境；若环境不支持，可使用“上传文档”按钮。

## 现代 UI 升级说明

当前版本已重构界面层：

- 全局字体动态检测，优先使用 Microsoft YaHei UI / Microsoft YaHei / PingFang SC / Source Han Sans SC / Segoe UI / Inter / Roboto，避免宋体、仿宋、楷体、Times New Roman 等衬线或旧式字体。
- 使用 `translator_pro/gui/ui_style.py` 在运行时生成 customtkinter 主题 JSON，并通过 `ctk.set_default_color_theme()` 加载，不打包任何字体文件。
- 浅色主题采用 `#F5F7FA` 主背景、`#FFFFFF` 卡片、`#3B82F6` 强调色；深色主题采用 `#0F172A` 主背景、`#1E293B` 卡片。
- API 配置窗口右侧表单已改为 `CTkScrollableFrame`，解决字段过多时无法滚动和底部按钮遮挡的问题。
- 主界面加入卡片式输入/输出区、可折叠思考过程面板、后台任务旋转指示、toast 通知、空输入柔和抖动反馈、占位符与焦点高亮。

