from __future__ import annotations

APP_NAME = "CloudLingo Studio"
CONFIG_DIR_NAME = ".cloudlingo_studio"
CONFIG_FILE_NAME = "config.json"
HISTORY_LIMIT = 50
DEFAULT_LONG_DOC_THRESHOLD = 5000

DEFAULT_APIS = [
    {
        "id": "deepseek-default",
        "api_name": "DeepSeek Reasoner",
        "provider": "openai_compatible",
        "api_key": "",
        "base_url": "https://api.deepseek.com/v1",
        "model_name": "deepseek-reasoner",
        "temperature": 0.2,
        "max_tokens": 4096,
        "stream_enabled": True,
        "supports_reasoning": True,
        "enabled": True,
        "http_proxy": "",
        "https_proxy": "",
        "timeout": 60,
        "last_status": "未测试",
        "last_latency_ms": None,
    },
    {
        "id": "deepseek-chat-default",
        "api_name": "DeepSeek Chat",
        "provider": "openai_compatible",
        "api_key": "",
        "base_url": "https://api.deepseek.com/v1",
        "model_name": "deepseek-chat",
        "temperature": 0.2,
        "max_tokens": 4096,
        "stream_enabled": True,
        "supports_reasoning": False,
        "enabled": True,
        "http_proxy": "",
        "https_proxy": "",
        "timeout": 60,
        "last_status": "未测试",
        "last_latency_ms": None,
    },
    {
        "id": "openai-default",
        "api_name": "OpenAI GPT",
        "provider": "openai_compatible",
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4.1-mini",
        "temperature": 0.2,
        "max_tokens": 4096,
        "stream_enabled": True,
        "supports_reasoning": False,
        "enabled": False,
        "http_proxy": "",
        "https_proxy": "",
        "timeout": 60,
        "last_status": "未测试",
        "last_latency_ms": None,
    },
]

DEFAULT_AGENTS = [
    {
        "id": "faithful",
        "name": "忠实还原",
        "default_api_id": "deepseek-chat-default",
        "default_model": "deepseek-chat",
        "prompt": (
            "你是一名严谨的专业翻译。请准确传达原文意思，不增不减，不擅自解释，"
            "译文风格尽量贴近原文。保持段落、列表、编号、标点层级和术语一致性。"
        ),
    },
    {
        "id": "patent-law",
        "name": "专利法律翻译",
        "default_api_id": "deepseek-chat-default",
        "default_model": "deepseek-chat",
        "prompt": (
            "你是一名专利法律翻译专家。翻译时必须注意权利要求范围和法律风险，"
            "不得扩大或缩小原文含义，尽量逐字逐句直译，保留原文结构、术语、编号、"
            "引用关系和限定语。对于 claim、wherein、comprising 等专利表达应保持法律等效性。"
        ),
    },
    {
        "id": "literary",
        "name": "文学翻译",
        "default_api_id": "deepseek-chat-default",
        "default_model": "deepseek-chat",
        "prompt": (
            "你是一名文学翻译家。请在忠实保留原文核心含义的基础上，使译文流畅、优美、"
            "具有文学美感。可适度意译，但不得改变人物关系、叙事视角、情绪走向和重要意象。"
        ),
    },
    {
        "id": "classical-chinese",
        "name": "文言文翻译",
        "default_api_id": "deepseek-chat-default",
        "default_model": "deepseek-chat",
        "prompt": (
            "你是一名古汉语与现代汉语互译专家。若源文本为现代语言，请译为典雅、准确的文言文；"
            "若源文本为文言文，请译为通顺准确的现代语言。保持原文意思和语气。"
        ),
    },
    {
        "id": "technical-doc",
        "name": "技术文档翻译",
        "default_api_id": "deepseek-chat-default",
        "default_model": "deepseek-chat",
        "prompt": (
            "你是一名技术文档翻译专家。请精准翻译技术术语、参数、代码标识符、接口名称、"
            "缩写和流程逻辑，保持 Markdown、表格、编号、代码块、路径、命令和变量名格式不变。"
        ),
    },
]

DEFAULT_GLOSSARY = [
    {"id": "term-agent", "source": "AI Agent", "target": "智能体", "note": "AI 产品/Agent 场景"},
    {"id": "term-prompt", "source": "Prompt", "target": "提示词", "note": "提示词工程"},
    {"id": "term-token", "source": "Token", "target": "令牌", "note": "模型调用计量单位"},
    {"id": "term-rag", "source": "RAG", "target": "检索增强生成", "note": "知识库问答"},
    {"id": "term-embedding", "source": "Embedding", "target": "向量表示", "note": "语义检索"},
]


DEFAULT_SETTINGS = {
    "theme": "light",
    "language": "zh",
    "long_doc_threshold": DEFAULT_LONG_DOC_THRESHOLD,
    "max_concurrent_doc_tasks": 2,
    "auto_retry": 1,
    "default_source_lang": "自动检测",
    "default_target_lang": "中文",
    "show_reasoning_panel": True,
    "task_output_dir": "",
    "last_api_id": "deepseek-chat-default",
    "last_agent_id": "faithful",
}

DEFAULT_CONFIG = {
    "apis": DEFAULT_APIS,
    "agents": DEFAULT_AGENTS,
    "glossary": DEFAULT_GLOSSARY,
    "history": [],
    "settings": DEFAULT_SETTINGS,
}
