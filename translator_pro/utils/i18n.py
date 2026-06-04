from __future__ import annotations

TEXT = {
    "zh": {
        "app_title": "Translator Pro 翻译软件",
        "source": "原文",
        "result": "译文",
        "reasoning": "AI 思考过程",
        "translate": "翻译",
        "retranslate": "重新翻译",
        "copy": "复制结果",
        "clear": "清空",
        "export": "导出",
        "pin_compare": "固定对比",
        "tasks": "后台任务",
        "settings": "设置",
        "api_config": "API 配置",
        "agent_config": "Agent 配置",
        "glossary": "术语库管理",
        "history": "历史记录",
        "preferences": "偏好设置",
        "help": "帮助",
        "upload": "上传文档",
        "theme": "深色主题",
        "translating": "翻译中…",
        "ready": "就绪",
        "auto_detect": "自动检测",
    },
    "en": {
        "app_title": "Translator Pro",
        "source": "Source",
        "result": "Translation",
        "reasoning": "AI Reasoning",
        "translate": "Translate",
        "retranslate": "Retranslate",
        "copy": "Copy result",
        "clear": "Clear",
        "export": "Export",
        "pin_compare": "Pin compare",
        "tasks": "Background tasks",
        "settings": "Settings",
        "api_config": "API Configuration",
        "agent_config": "Agent Configuration",
        "glossary": "Glossary Manager",
        "history": "History",
        "preferences": "Preferences",
        "help": "Help",
        "upload": "Upload document",
        "theme": "Dark theme",
        "translating": "Translating…",
        "ready": "Ready",
        "auto_detect": "Auto detect",
    },
}


class I18n:
    def __init__(self, lang: str = "zh") -> None:
        self.lang = lang if lang in TEXT else "zh"

    def set_lang(self, lang: str) -> None:
        self.lang = lang if lang in TEXT else "zh"

    def t(self, key: str) -> str:
        return TEXT.get(self.lang, TEXT["zh"]).get(key, key)
