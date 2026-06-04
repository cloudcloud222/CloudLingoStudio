# TranslatorPro

TranslatorPro 是一个基于 Python 和 CustomTkinter 开发的桌面端文档翻译工具。

项目最开始是为了解决自己处理英文论文、技术文档和长文档材料时遇到的一些实际问题：网页端大模型适合临时问答，但在长文档翻译时会遇到上下文长度限制、术语前后不一致、结果不方便保存、Prompt 需要反复复制等问题。

因此我把常用的文档翻译流程封装成了一个本地桌面工具，方便进行文本输入、文档上传、模型配置、Agent Prompt 配置、术语管理、历史记录和译文导出。

项目本身不训练翻译模型，重点放在大模型 API 的应用层封装和长文档处理流程上。

## 主要功能

* 支持普通文本翻译和文档翻译两种使用方式
* 支持导入 `.txt`、`.docx`、`.pdf` 文件
* 支持 OpenAI-compatible 接口，适配 DeepSeek、OpenAI、OpenRouter、本地 vLLM/Ollama 网关等兼容接口
* 支持基础的 Anthropic Claude 和 Google Gemini 接口配置
* 支持流式输出，翻译过程可以逐步显示结果
* 支持 reasoning_content 展示，用于查看部分模型返回的思考过程
* 支持 Agent Prompt 配置，可针对不同翻译场景切换提示词
* 支持术语库管理，用于提升技术文档、专利材料等场景下的术语一致性
* 支持历史记录保存，便于查看和复用之前的翻译结果
* 支持长文档分块、后台任务、暂停、继续和取消
* 支持译文导出为 TXT、DOCX 或 PDF
* 支持 PyInstaller 打包为 Windows 桌面程序

## 技术栈

* Python 3.10+
* CustomTkinter
* requests
* python-docx
* PyMuPDF / pdfplumber
* reportlab
* PyInstaller

## 项目结构

```text
TranslatorPro/
├── app.py
├── translator_pro/
│   ├── api/              # 大模型 API 调用与 Provider 适配
│   ├── doc_translator/   # 文档解析、分块、翻译与导出
│   ├── gui/              # CustomTkinter 桌面界面
│   └── utils/            # 配置存储、任务管理、文本处理等工具函数
├── requirements.txt
├── build_translator_pro.spec
└── README.md
```

## 安装与运行

克隆项目后进入目录：

```bash
git clone https://github.com/cloudcloud222/TranslatorPro.git
cd TranslatorPro
```

创建并激活虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
pip install -r requirements.txt
```

运行程序：

```bash
python app.py
```

首次启动后，程序会在用户目录下生成本地配置文件：

```text
~/.translator_pro/config.json
```

文档翻译的输出结果默认保存在：

```text
~/.translator_pro/outputs/
```

## 基本使用流程

1. 启动程序后，先进入 `设置 → API 配置`
2. 新增一个 API 配置，填写 Provider、Base URL、API Key、模型名等信息
3. 在主界面输入文本，或上传 `.txt`、`.docx`、`.pdf` 文档
4. 选择合适的 Agent Prompt，例如忠实翻译、技术文档翻译、专利法律翻译等
5. 点击翻译，等待流式输出或后台任务完成
6. 根据需要复制结果，或导出为 TXT / DOCX / PDF 文件

## Agent Prompt

项目里的 Agent 更偏向“场景化 Prompt 模板”，不是复杂的多智能体框架。

目前预设了几类常用翻译场景：

* 忠实还原
* 技术文档翻译
* 专利法律翻译
* 文学翻译
* 文言文翻译

每个 Agent 可以配置系统提示词，也可以绑定默认 API 和模型。这样做的目的是减少重复写 Prompt 的成本，并让不同类型文档有相对稳定的翻译风格。

## 术语库

在翻译技术文档、论文或专利材料时，同一个术语如果前后翻译不一致，会影响阅读体验。因此项目加入了简单的术语库功能。

使用时可以提前维护一些固定译法，例如：

```text
large language model -> 大语言模型
retrieval-augmented generation -> 检索增强生成
knowledge base -> 知识库
```

翻译时程序会把术语约束注入 Prompt 中，尽量让模型保持前后一致。

## 长文档处理

长文档不能简单一次性丢给模型处理，主要原因有三个：

1. 容易超过模型上下文长度
2. 失败后重试成本较高
3. 用户无法感知任务进度

因此 TranslatorPro 会先对文档进行文本抽取，再按段落和长度进行分块。每个分块单独调用模型，最后再合并结果并导出。

当前版本主要关注文本内容处理。对于复杂 PDF 版式，例如双栏论文、扫描件、复杂表格和公式，暂时不能保证完整还原排版。

## 流式输出与后台任务

普通短文本翻译可以直接在主界面显示结果。对于长文档翻译，程序会进入后台任务流程，避免界面卡死。

流式输出主要用于提升交互体验：模型生成内容时，结果可以逐步显示，而不是等全部生成后一次性返回。

后台任务支持：

* 任务进度展示
* 暂停
* 继续
* 取消
* 输出路径记录

## 打包

项目提供了 PyInstaller 的 spec 文件，可以用于打包 Windows 可执行程序：

```bash
pyinstaller build_translator_pro.spec --clean --noconfirm
```

打包产物会生成在 `dist/` 目录下。

如果只做源码运行，不需要执行这一步。

## 隐私与安全说明

请不要把自己的 API Key、个人配置文件、翻译历史记录或私人文档上传到公开仓库。

项目中建议忽略以下内容：

```text
.env
config.json
secrets.json
api_keys.json
.venv/
build/
dist/
__pycache__/
```

如果需要公开展示项目，可以只保留源码、README、requirements.txt、示例配置和脱敏截图。

## 当前限制

这个项目目前更偏个人工具和学习项目，还不是完整的商业级产品。当前主要限制包括：

* PDF 复杂版式处理能力有限
* 术语一致性主要依赖 Prompt 和术语库，没有做自动质量评估
* 历史记录采用本地文件存储，适合个人使用，不适合多用户协作
* 部分 Provider 只是基础适配，不同模型的字段兼容仍需要继续完善

后续可以继续优化的方向：

* 引入 SQLite 管理历史记录和任务状态
* 增加术语命中率检查和翻译质量评估
* 增强 PDF 版式解析与表格处理
* 支持更完整的本地模型部署
* 增加 token 估算和调用成本统计

## 项目定位

TranslatorPro 更适合作为一个 LLM 应用开发项目来理解。它的重点不是模型训练，而是围绕真实文档处理场景，完成模型接入、Prompt 管理、文件解析、长文本分块、流式输出、历史记录和结果导出等工程流程封装。
