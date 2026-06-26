\# CloudLingo Studio（云译工坊）



CloudLingo Studio 是一个用 Python 和 CustomTkinter 写的桌面端翻译工具。



最开始做这个项目的原因比较简单：我平时看英文论文、技术文档比较多，也用过知云这类翻译工具，但 DeepSeek 翻译等功能需要会员。后来我发现很多大模型 API 本身已经可以完成不错的翻译效果，所以就尝试自己做一个本地桌面端工具，把 DeepSeek 或其他兼容 OpenAI 接口的模型接进来，用自己的 API Key 完成翻译。



一开始它只是一个简单的文本翻译窗口，后面在使用过程中慢慢加了一些功能，比如文档上传、术语库、Agent Prompt、历史记录、长文档后台任务和结果导出。现在这个项目更像是一个面向论文、技术文档和学习资料的个人翻译工作台。



这个项目不训练模型，也不是要做一个完整的商业翻译产品。它主要解决我自己在学习和科研过程中遇到的几个问题：



\* 翻译工具收费，或者免费额度不够用；

\* 网页端大模型翻译长文档不方便；

\* 专业术语前后翻译不一致；

\* 不同类型文本需要不同翻译风格；

\* 翻译结果不方便保存和复用；

\* 长文档处理时看不到进度，失败后也不方便重新处理。



\## 界面预览



主界面：



!\[CloudLingo Studio 主界面](docs/screenshots/01\_cloudlingo\_main.png)



后台任务中心：



!\[后台任务中心](docs/screenshots/03\_cloudlingo\_task\_panel.png)



更多截图可以在 `docs/screenshots/` 目录下查看，包括术语库、Agent 配置和偏好设置页面。



\## 主要功能



目前已经做好的功能包括：



\* 普通文本翻译；

\* `.txt`、`.docx`、`.pdf` 文档上传；

\* 多 Provider API 配置；

\* 支持 OpenAI-compatible 接口，方便接入 DeepSeek、OpenAI、OpenRouter、本地模型网关等；

\* 基础支持 Claude 和 Gemini 的接口配置；

\* 支持流式输出；

\* 支持 Agent Prompt 配置；

\* 支持术语库管理；

\* 支持历史记录保存；

\* 支持固定对比；

\* 支持长文档分块翻译；

\* 支持后台任务中心，能查看多个任务的处理进度；

\* 支持设置后台任务输出目录；

\* 支持导出 TXT、DOCX、PDF；

\* 支持 PyInstaller 打包为 Windows 桌面程序。



\## 技术栈



主要用到：



\* Python 3.10+

\* CustomTkinter

\* requests

\* python-docx

\* PyMuPDF / pdfplumber

\* reportlab

\* PyInstaller



项目整体还是一个个人桌面端工具，没有引入复杂后端，也没有使用数据库。配置、术语库和历史记录主要存储在本地文件中。



\## 项目结构



```text

CloudLingoStudio/

├── app.py

├── translator\_pro/

│   ├── api/              # 大模型 API 调用与不同 Provider 适配

│   ├── agents/           # Agent Prompt 管理

│   ├── doc\_translator/   # 文档解析、分块、翻译流程

│   ├── gui/              # CustomTkinter 界面

│   └── utils/            # 配置、存储、任务、导出等工具函数

├── docs/

│   └── screenshots/      # 项目截图

├── requirements.txt

├── build\_translator\_pro.spec

└── README.md

```



\## 安装与运行



克隆项目：



```bash

git clone https://github.com/cloudcloud222/CloudLingoStudio.git

cd CloudLingoStudio

```



创建虚拟环境：



```bash

python -m venv .venv

```



Windows PowerShell 激活虚拟环境：



```powershell

.venv\\Scripts\\Activate.ps1

```



安装依赖：



```bash

pip install -r requirements.txt

```



运行程序：



```bash

python app.py

```



第一次启动后，程序会在用户目录下生成本地配置文件：



```text

\~/.cloudlingo\_studio/config.json

```



后台任务默认输出目录为：



```text

\~/.cloudlingo\_studio/outputs/

```



也可以在软件的偏好设置或后台任务中心里修改输出文件夹。



\## 基本使用方式



大致流程是：



1\. 启动程序；

2\. 进入 API 配置，填入 Provider、Base URL、API Key 和模型名；

3\. 在主界面输入文本，或者上传 txt、docx、pdf 文档；

4\. 选择源语言和目标语言；

5\. 根据文本类型选择合适的 Agent Prompt；

6\. 点击翻译；

7\. 短文本会直接在主界面显示结果；

8\. 长文档可以放到后台任务中心处理；

9\. 翻译完成后复制结果，或者导出为 TXT、DOCX、PDF。



\## 为什么加 Agent Prompt



这里的 Agent 不是复杂的多智能体框架，更准确地说是“场景化 Prompt 模板”。



我一开始只做了普通翻译，后来发现不同类型文本对翻译要求不一样。比如论文和技术文档更强调准确、术语统一；专利文本更强调格式和表达严谨；文学内容则更关注语感。如果每次都手动写 Prompt 会比较麻烦，所以就把常用翻译策略做成了可配置的 Agent。



目前预设了几类：



\* 忠实还原；

\* 技术文档翻译；

\* 专利法律翻译；

\* 文学翻译；

\* 文言文翻译。



每个 Agent 可以设置系统 Prompt，也可以绑定默认 API 和模型。这样做的好处是：同一种材料可以尽量使用稳定的翻译风格，不用每次重新写提示词。



\## 为什么加术语库



翻译论文和技术文档时，术语不一致是一个很常见的问题。比如同一个词前面翻译成“检索增强生成”，后面又变成“检索增强式生成”，阅读体验会很差。



所以项目里加了一个简单的术语库。使用时可以提前维护一些固定译法，例如：



```text

large language model -> 大语言模型

retrieval-augmented generation -> 检索增强生成

knowledge base -> 知识库

prompt -> 提示词

agent -> 智能体

```



翻译时程序会把这些术语约束拼进 Prompt 中，让模型尽量保持一致。这个方案不是百分百可靠，但对论文、课程材料和技术文档翻译已经有一定帮助。



\## 长文档处理



长文档不能简单一次性丢给模型，主要有几个原因：



\* 容易超过上下文长度；

\* 一次失败后重试成本高；

\* 用户看不到处理进度；

\* 大段文本输出不方便保存；

\* 多个文件处理时容易混乱。



所以项目会先从文档中抽取文本，再按段落和长度进行分块，每个分块单独翻译，最后合并结果并导出。



当前版本更关注“把文字翻译出来”。对于复杂 PDF 排版、双栏论文、扫描件、复杂表格和公式，目前不能保证还原效果。



\## 后台任务中心



长文档翻译时，界面如果一直等待模型返回结果，会显得很卡，所以后面加了后台任务中心。



目前后台任务中心支持：



\* 查看多个任务；

\* 显示任务状态和进度；

\* 暂停、继续、取消任务；

\* 设置输出文件夹；

\* 打开输出文件夹；

\* 记录任务输出路径。



这个功能主要是为了解决长文档翻译时“看不到进度”和“找不到结果文件”的问题。



\## 打包



项目提供了 PyInstaller 的 spec 文件，可以打包为 Windows 桌面程序：



```bash

pyinstaller build\_translator\_pro.spec --clean --noconfirm

```



打包产物会在 `dist/` 目录下生成。



如果只是源码运行，不需要执行打包。



\## 隐私和安全



请不要把自己的 API Key、个人配置文件、翻译历史或私人文档上传到公开仓库。



建议忽略这些内容：



```text

.env

config.json

secrets.json

api\_keys.json

.venv/

build/

dist/

\_\_pycache\_\_/

.cloudlingo\_studio/

outputs/

```



当前仓库只保留源码、运行说明和脱敏截图。



\## 目前的不足



这个项目还有很多不完善的地方：



\* PDF 复杂排版处理能力一般；

\* 扫描版 PDF 暂时不能识别；

\* 术语一致性主要依赖 Prompt，并没有做自动检查；

\* 历史记录和任务状态还是本地文件存储；

\* Provider 适配还比较基础；

\* 没有做 token 消耗统计；

\* 没有完整的自动化测试；

\* UI 还有继续优化空间。



后续比较想做的优化：



\* 增加术语命中率检查；

\* 增加翻译质量简单评分；

\* 增加 token 估算和调用成本统计；

\* 用 SQLite 管理历史记录和任务状态；

\* 优化 PDF 和 DOCX 的结构保留；

\* 增加更多真实文档场景的测试样例。



