from __future__ import annotations

import os
import sys
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

from translator_pro.api.client import LLMClient, StreamDelta
from translator_pro.doc_translator import DocumentFormatError, DocumentTranslator
from translator_pro.gui.dialogs import (
    APIConfigDialog,
    AgentConfigDialog,
    GlossaryDialog,
    HistoryDialog,
    PreferencesDialog,
    TaskManagerDialog,
    GlossaryCheckDialog,
    AboutDialog,
)
from translator_pro.gui.ui_style import (
    install_modern_theme,
    pair,
    font,
    card,
    soft_frame,
    modern_button,
    modern_option_menu,
    label,
    apply_textbox_typography,
    bind_focus_glow,
    install_textbox_placeholder,
    textbox_get_clean,
    textbox_clear,
    textbox_insert_user_text,
    setup_ttk_style,
)
from translator_pro.utils.glossary import glossary_to_prompt, analyze_glossary_hits
from translator_pro.utils.i18n import I18n
from translator_pro.utils.storage import AppStorage
from translator_pro.utils.tasks import BackgroundTask, BackgroundTaskManager
from translator_pro.utils.text import count_chars, estimate_tokens
from translator_pro.utils.exporter import export_docx, export_txt
from translator_pro.utils.defaults import APP_NAME


LANG_OPTIONS = ["自动检测", "中文", "英文", "日文", "韩文", "法文", "德文", "西班牙文", "俄文", "文言文"]
TARGET_LANG_OPTIONS = ["中文", "英文", "日文", "韩文", "法文", "德文", "西班牙文", "俄文", "文言文"]
SPINNER_FRAMES = ["", ".", "..", "..."]


class TranslatorProApp(ctk.CTk):
    def __init__(self) -> None:
        install_modern_theme()
        self.storage = AppStorage()
        settings = self.storage.get_settings()
        ctk.set_appearance_mode("dark" if settings.get("theme") == "dark" else "light")
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1320x820")
        self.minsize(1120, 720)
        self.configure(fg_color=pair("bg"))
        setup_ttk_style(self)

        self.i18n = I18n(settings.get("language", "zh"))
        self.ui_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.current_translation_thread: Optional[threading.Thread] = None
        self.pinned_result: str = ""
        self.is_reasoning_visible = bool(settings.get("show_reasoning_panel", True))
        # 固定默认显示 AI 思考区，避免历史配置 show_reasoning_panel=False 导致界面不可见
        self.is_reasoning_visible = True        
        self._dropdown: Optional[ctk.CTkToplevel] = None
        self._spinner_index = 0
        self._reasoning_buffer: List[str] = []
        self._reasoning_typing = False
        self._thinking_tick = 0

        self.doc_translator = DocumentTranslator(self.storage)
        self.task_manager = BackgroundTaskManager(settings.get("max_concurrent_doc_tasks", 2))
        self.is_task_panel_visible = False
        self._task_dropdown: Optional[ctk.CTkToplevel] = None

        self._build_menu()  # 自定义顶部二级菜单，不使用原生菜单栏，避免古旧 Windows 风格。
        self._build_layout()
        self._bind_shortcuts()
        self.refresh_selectors()
        self._install_optional_dnd()
        self._poll_ui_queue()
        self._poll_task_events()
        self._spin_task_icon()
        self.update_status()

    def _build_menu(self) -> None:
        # 保留方法名以兼容旧结构；真正的菜单在 _build_titlebar 中创建。
        return None

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_titlebar()
        self._build_main_area()
        self._build_statusbar()

    def _build_titlebar(self) -> None:
        top = ctk.CTkFrame(self, corner_radius=0, height=64, fg_color=pair("bg"), border_width=0)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=0)
        top.grid_columnconfigure(1, weight=1)
        top.grid_columnconfigure(2, weight=0)

        left_nav = ctk.CTkFrame(top, fg_color="transparent")
        left_nav.grid(row=0, column=0, padx=18, pady=12, sticky="w")
        self.settings_btn = modern_button(left_nav, "设置", command=lambda: self._show_dropdown(self.settings_btn, [
            ("API 配置", self.open_api_config),
            ("Agent 配置", self.open_agent_config),
            ("术语库管理", self.open_glossary),
            ("偏好设置", self.open_preferences),
            ("退出", self.destroy),
        ]), kind="secondary", width=92, height=36)
        self.settings_btn.pack(side="left", padx=(0, 8))
        self.agent_btn = modern_button(left_nav, "Agent", command=lambda: self._show_dropdown(self.agent_btn, [
            ("管理 Agent", self.open_agent_config),
            ("历史记录", self.open_history),
        ]), kind="secondary", width=76, height=36)
        self.agent_btn.pack(side="left", padx=(0, 8))
        self.help_btn = modern_button(left_nav, "帮助", command=lambda: AboutDialog(self), kind="secondary", width=70, height=36)
        self.help_btn.pack(side="left")

        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.grid(row=0, column=1, pady=10)
        label(title_box, APP_NAME, size=18, weight="bold").pack()
        label(title_box, "AI 文档翻译与术语管理工作台", size=12, secondary=True).pack(pady=(1, 0))

        right_nav = ctk.CTkFrame(top, fg_color="transparent")
        right_nav.grid(row=0, column=2, padx=18, pady=12, sticky="e")
        self.theme_switch = ctk.CTkSwitch(right_nav, text="深色主题", command=self.toggle_theme, font=font(self, 13))
        self.theme_switch.pack(side="right")
        if self.storage.get_settings().get("theme") == "dark":
            self.theme_switch.select()

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, fg_color=pair("bg"), border_width=0)
        main.grid(row=1, column=0, sticky="nsew", padx=20, pady=(8, 12))
        main.grid_columnconfigure(0, weight=5)
        main.grid_columnconfigure(1, weight=0)
        main.grid_columnconfigure(2, weight=5)
        main.grid_rowconfigure(0, weight=1)

        self._build_source_card(main)
        self._build_control_card(main)
        self._build_result_card(main)

    def _build_source_card(self, main) -> None:
        self.left_card = card(main)
        self.left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=2)
        self.left_card.grid_columnconfigure(0, weight=1)
        self.left_card.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.left_card, fg_color="transparent", border_width=0)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)
        label(header, "原文输入", size=18, weight="bold").grid(row=0, column=0, sticky="w")
        self.upload_btn = modern_button(header, "上传文档", command=self.upload_document, kind="secondary", width=104, height=34)
        self.upload_btn.grid(row=0, column=1, sticky="e")

        self.source_text = ctk.CTkTextbox(
            self.left_card,
            corner_radius=12,
            wrap="word",
            fg_color=pair("card"),
            border_color=pair("border"),
            border_width=1,
            text_color=pair("text"),
        )
        self.source_text.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 12))
        apply_textbox_typography(self.source_text, size=14)
        bind_focus_glow(self.source_text)
        install_textbox_placeholder(self.source_text, "在这里输入需要翻译的内容，或将 .docx / .pdf / .txt 文档拖拽到此区域。")

        footer = ctk.CTkFrame(self.left_card, fg_color="transparent", border_width=0)
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)
        self.char_label = label(footer, "字符数：0 | 估算 token：0", size=12, secondary=True)
        self.char_label.grid(row=0, column=0, sticky="w")
        self.clear_btn = modern_button(footer, "清空", width=78, height=32, command=self.clear_source, kind="secondary")
        self.clear_btn.grid(row=0, column=1, padx=(8, 0))
        self.source_text.bind("<KeyRelease>", lambda _e: self.update_char_count(), add="+")

    def _build_control_card(self, main) -> None:
        ctrl_card = card(main, width=284)
        ctrl_card.grid(row=0, column=1, sticky="ns", padx=0, pady=2)
        ctrl_card.grid_propagate(False)
        ctrl_card.grid_columnconfigure(0, weight=1)
        ctrl_card.grid_rowconfigure(0, weight=1)

        # 中间控制区内容较多，在低分辨率或系统缩放较高时底部按钮会被遮挡。
        # 改成可滚动控制面板，保证“导出译文 / 后台任务”等入口始终可通过滚轮访问。
        ctrl = ctk.CTkScrollableFrame(
            ctrl_card,
            corner_radius=16,
            fg_color=pair("card"),
            border_color=pair("border"),
            border_width=0,
        )
        ctrl.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        ctrl.grid_columnconfigure(0, weight=1)

        label(ctrl, "翻译控制", size=18, weight="bold").grid(row=0, column=0, padx=20, pady=(20, 14), sticky="w")

        label(ctrl, "源语言", size=13, weight="bold").grid(row=1, column=0, padx=20, pady=(0, 6), sticky="w")
        self.source_lang_menu = modern_option_menu(ctrl, values=LANG_OPTIONS)
        self.source_lang_menu.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.source_lang_menu.set(self.storage.get_settings().get("default_source_lang", "自动检测"))

        self.swap_btn = modern_button(ctrl, "交换语言", command=self.swap_languages, kind="secondary", height=34)
        self.swap_btn.grid(row=3, column=0, padx=20, pady=(0, 12), sticky="ew")

        label(ctrl, "目标语言", size=13, weight="bold").grid(row=4, column=0, padx=20, pady=(0, 6), sticky="w")
        self.target_lang_menu = modern_option_menu(ctrl, values=TARGET_LANG_OPTIONS)
        self.target_lang_menu.grid(row=5, column=0, padx=20, pady=(0, 16), sticky="ew")
        self.target_lang_menu.set(self.storage.get_settings().get("default_target_lang", "中文"))

        label(ctrl, "Agent", size=13, weight="bold").grid(row=6, column=0, padx=20, pady=(0, 6), sticky="w")
        self.agent_menu = modern_option_menu(ctrl, values=["忠实还原"], command=self.on_agent_changed)
        self.agent_menu.grid(row=7, column=0, padx=20, pady=(0, 12), sticky="ew")

        label(ctrl, "API / 模型", size=13, weight="bold").grid(row=8, column=0, padx=20, pady=(0, 6), sticky="w")
        self.api_menu = modern_option_menu(ctrl, values=["无"], command=self.on_api_changed)
        self.api_menu.grid(row=9, column=0, padx=20, pady=(0, 8), sticky="ew")
        self.model_entry = ctk.CTkEntry(ctrl, placeholder_text="模型名称", font=font(self, 13), corner_radius=8)
        self.model_entry.grid(row=10, column=0, padx=20, pady=(0, 18), sticky="ew")
        bind_focus_glow(self.model_entry)

        self.translate_button = modern_button(ctrl, "翻译  Ctrl+Enter", height=46, command=self.translate_text, kind="primary")
        self.translate_button.grid(row=11, column=0, padx=20, pady=(0, 10), sticky="ew")
        modern_button(ctrl, "复制结果", command=self.copy_result, kind="secondary", height=36).grid(row=12, column=0, padx=20, pady=5, sticky="ew")
        self.pin_compare_btn = modern_button(ctrl, "固定对比", command=self.pin_compare, kind="secondary", height=36)
        self.pin_compare_btn.grid(row=13, column=0, padx=20, pady=5, sticky="ew")
        modern_button(ctrl, "导出译文", command=self.export_result, kind="secondary", height=36).grid(row=14, column=0, padx=20, pady=5, sticky="ew")
        modern_button(ctrl, "术语检查", command=self.check_glossary_hits, kind="secondary", height=36).grid(row=15, column=0, padx=20, pady=5, sticky="ew")
        self.task_btn = modern_button(ctrl, "后台任务中心", command=self.toggle_task_panel, kind="secondary", height=36)
        self.task_btn.grid(row=16, column=0, padx=20, pady=(5, 20), sticky="ew")

    def _build_result_card(self, main) -> None:
        self.right_card = card(main)
        self.right_card.grid(row=0, column=2, sticky="nsew", padx=(12, 0), pady=2)
        self.right_card.grid_columnconfigure(0, weight=1)
        self.right_card.grid_rowconfigure(1, weight=4)
        self.right_card.grid_rowconfigure(3, weight=2)

        header = ctk.CTkFrame(self.right_card, fg_color="transparent", border_width=0)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)
        label(header, "翻译结果", size=18, weight="bold").grid(row=0, column=0, sticky="w")

        self.reasoning_toggle_btn = modern_button(
            header,
            "隐藏思考区",
            width=104,
            height=34,
            command=self.toggle_reasoning,
            kind="secondary"
        )
        self.reasoning_toggle_btn.grid(row=0, column=1, padx=(8, 8), sticky="e")

        modern_button(
            header,
            "重新翻译",
            width=92,
            height=34,
            command=self.translate_text,
            kind="secondary"
        ).grid(row=0, column=2, sticky="e")

        self.result_text = ctk.CTkTextbox(
            self.right_card,
            corner_radius=12,
            wrap="word",
            fg_color=pair("card"),
            border_color=pair("border"),
            border_width=1,
            text_color=pair("text"),
        )
        self.result_text.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 12))
        apply_textbox_typography(self.result_text, size=14)
        bind_focus_glow(self.result_text)
        install_textbox_placeholder(self.result_text, "译文将显示在这里。翻译完成后可直接编辑、复制或导出。")

        self.compare_frame = soft_frame(self.right_card)
        self.compare_frame.grid_columnconfigure(0, weight=1)
        self.compare_frame.grid_columnconfigure(1, weight=1)
        label(self.compare_frame, "上一次固定结果", size=12, weight="bold", secondary=True).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")
        label(self.compare_frame, "当前结果", size=12, weight="bold", secondary=True).grid(row=0, column=1, padx=12, pady=(10, 4), sticky="w")
        self.pinned_text = ctk.CTkTextbox(self.compare_frame, height=92, corner_radius=10, font=font(self, 13), wrap="word")
        self.current_compare_text = ctk.CTkTextbox(self.compare_frame, height=92, corner_radius=10, font=font(self, 13), wrap="word")
        self.pinned_text.grid(row=1, column=0, padx=(12, 6), pady=(0, 12), sticky="nsew")
        self.current_compare_text.grid(row=1, column=1, padx=(6, 12), pady=(0, 12), sticky="nsew")
        self.compare_frame.grid_remove()

        self.reasoning_panel = soft_frame(self.right_card, fg_color=pair("reasoning_bg"))
        self.reasoning_panel.grid_columnconfigure(1, weight=1)
        self.reasoning_panel.grid_rowconfigure(1, weight=1)
        accent_line = ctk.CTkFrame(self.reasoning_panel, width=3, corner_radius=2, fg_color=pair("accent"), border_width=0)
        accent_line.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(12, 8), pady=12)
        reasoning_header = ctk.CTkFrame(self.reasoning_panel, fg_color="transparent", border_width=0)
        reasoning_header.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(10, 0))
        reasoning_header.grid_columnconfigure(0, weight=1)
        label(reasoning_header, "AI 思考过程 / 状态", size=13, weight="bold").grid(row=0, column=0, sticky="w")
        modern_button(reasoning_header, "折叠", command=self.toggle_reasoning, kind="secondary", width=64, height=28).grid(row=0, column=1, sticky="e")
        self.reasoning_text = ctk.CTkTextbox(
            self.reasoning_panel,
            corner_radius=10,
            wrap="word",
            height=150,
            font=font(self, 13),
            fg_color=pair("reasoning_bg"),
            text_color=pair("reasoning_text"),
            border_color=pair("border"),
            border_width=1,
        )
        self.reasoning_text.grid(row=1, column=1, sticky="nsew", padx=(0, 12), pady=(8, 12))
        apply_textbox_typography(self.reasoning_text, size=13)
        self.reasoning_text.insert("1.0", "AI 思考过程将在这里实时流式显示；不支持 reasoning_content 的模型将显示翻译状态。")
        self.reasoning_text.configure(state="disabled")
        if self.is_reasoning_visible:
            self.reasoning_panel.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 18))
        else:
            self.reasoning_panel.grid_remove()

    def _build_statusbar(self) -> None:
        status = ctk.CTkFrame(self, corner_radius=0, height=36, fg_color=pair("bg"), border_width=0)
        status.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 4))
        status.grid_columnconfigure(1, weight=1)
        self.status_task_icon = label(status, "", size=12, secondary=True)
        self.status_task_icon.grid(row=0, column=0, padx=(20, 4), pady=6, sticky="w")
        self.status_label = label(status, "就绪", size=12, secondary=True, anchor="w")
        self.status_label.grid(row=0, column=1, padx=(0, 20), pady=6, sticky="ew")

    def _show_dropdown(self, anchor, items: List[tuple[str, Any]]) -> None:
        if self._dropdown is not None and self._dropdown.winfo_exists():
            self._dropdown.destroy()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 8
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        try:
            menu.attributes("-alpha", 0.98)
        except Exception:
            pass
        menu.configure(fg_color=pair("bg"))
        box = card(menu)
        box.pack(padx=2, pady=2, fill="both", expand=True)
        for text, cmd in items:
            def run(c=cmd):
                try:
                    menu.destroy()
                finally:
                    c()
            modern_button(box, text, command=run, kind="secondary", anchor="w", height=34, width=168).pack(fill="x", padx=8, pady=4)
        menu.geometry(f"184x{len(items) * 42 + 12}+{x}+{y}")
        self._dropdown = menu
        menu.after(200, lambda: menu.focus_force())
        menu.bind("<FocusOut>", lambda _e: menu.destroy(), add="+")

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-Return>", lambda _e: self.translate_text())
        self.bind_all("<Control-Shift-C>", lambda _e: self.copy_result())

    def _install_optional_dnd(self) -> None:
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            TkinterDnD._require(self)
            target = getattr(self.source_text, "_textbox", self.source_text)
            target.drop_target_register(DND_FILES)
            target.dnd_bind("<<Drop>>", lambda e: self.handle_dropped_file(e.data))
        except Exception:
            pass

    def handle_dropped_file(self, raw: str) -> None:
        path = raw.strip().strip("{}").split()[0]
        if path:
            self.start_document_translation(path)

    def refresh_selectors(self) -> None:
        self.apis = self.storage.get_apis()
        enabled = [a for a in self.apis if a.get("enabled", True)] or self.apis
        api_names = [a.get("api_name", "未命名") for a in enabled] or ["无"]
        self.api_menu.configure(values=api_names)
        last_api_id = self.storage.get_settings().get("last_api_id")
        selected_api = None
        for a in enabled:
            if a.get("id") == last_api_id:
                selected_api = a
                break
        selected_api = selected_api or (enabled[0] if enabled else None)
        if selected_api:
            self.api_menu.set(selected_api.get("api_name", "未命名"))
            self.model_entry.delete(0, "end")
            self.model_entry.insert(0, selected_api.get("model_name", ""))

        self.agents = self.storage.get_agents()
        agent_names = [a.get("name", "未命名") for a in self.agents] or ["无"]
        self.agent_menu.configure(values=agent_names)
        last_agent_id = self.storage.get_settings().get("last_agent_id")
        selected_agent = None
        for a in self.agents:
            if a.get("id") == last_agent_id:
                selected_agent = a
                break
        selected_agent = selected_agent or (self.agents[0] if self.agents else None)
        if selected_agent:
            self.agent_menu.set(selected_agent.get("name", "未命名"))
            if selected_agent.get("default_api_id"):
                for api in enabled:
                    if api.get("id") == selected_agent.get("default_api_id"):
                        self.api_menu.set(api.get("api_name", "未命名"))
                        self.model_entry.delete(0, "end")
                        self.model_entry.insert(0, selected_agent.get("default_model") or api.get("model_name", ""))
                        break
        self.update_status()

    def get_selected_api(self) -> Optional[Dict[str, Any]]:
        name = self.api_menu.get()
        for api in self.apis:
            if api.get("api_name") == name:
                api = dict(api)
                if self.model_entry.get().strip():
                    api["model_name"] = self.model_entry.get().strip()
                return api
        return None

    def get_selected_agent(self) -> Optional[Dict[str, Any]]:
        name = self.agent_menu.get()
        for agent in self.agents:
            if agent.get("name") == name:
                return dict(agent)
        return None

    def on_agent_changed(self, _value: str) -> None:
        agent = self.get_selected_agent()
        if not agent:
            return
        self.storage.update_settings(last_agent_id=agent.get("id"))
        api_id = agent.get("default_api_id")
        if api_id:
            for api in self.apis:
                if api.get("id") == api_id:
                    self.api_menu.set(api.get("api_name", "未命名"))
                    self.model_entry.delete(0, "end")
                    self.model_entry.insert(0, agent.get("default_model") or api.get("model_name", ""))
                    self.storage.update_settings(last_api_id=api.get("id"))
                    break
        self.update_status()

    def on_api_changed(self, _value: str) -> None:
        name = self.api_menu.get()
        api = None
        for item in self.apis:
            if item.get("api_name") == name:
                api = item
                break
        if api:
            self.model_entry.delete(0, "end")
            self.model_entry.insert(0, api.get("model_name", ""))
            self.storage.update_settings(last_api_id=api.get("id"))
        self.update_status()

    def update_char_count(self) -> None:
        text = textbox_get_clean(self.source_text)
        self.char_label.configure(text=f"字符数：{count_chars(text)} | 估算 token：{estimate_tokens(text)}")

    def update_status(self, extra: str = "") -> None:
        api = self.get_selected_api()
        api_name = api.get("api_name", "无") if api else "无"
        model = self.model_entry.get().strip() or (api.get("model_name", "") if api else "")
        conn = api.get("last_status", "未测试") if api else "未配置"
        running = self._running_task_count()
        msg = f"当前 API：{api_name}    模型：{model or '-'}    连接：{conn}    后台任务：{running}"
        if extra:
            msg += f"    {extra}"
        self.status_label.configure(text=msg)

    def _running_task_count(self) -> int:
        return sum(1 for t in self.task_manager.all().values() if str(t.state.value if hasattr(t.state, "value") else t.state) in ["pending", "running", "paused"])

    def toggle_theme(self) -> None:
        is_dark = self.theme_switch.get() == 1
        # after 延迟切换可以避免大量控件同时重绘造成的闪烁感。
        self.after(30, lambda: ctk.set_appearance_mode("dark" if is_dark else "light"))
        self.storage.update_settings(theme="dark" if is_dark else "light")
        self._show_toast("主题已切换", "已保存，下次启动将自动使用当前主题。")

    def toggle_reasoning(self) -> None:
        current = bool(self.reasoning_panel.winfo_ismapped())
        self.is_reasoning_visible = not current

        if self.is_reasoning_visible:
            self.reasoning_panel.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 18))
            if hasattr(self, "reasoning_toggle_btn"):
                self.reasoning_toggle_btn.configure(text="隐藏思考区")
        else:
            self.reasoning_panel.grid_remove()
            if hasattr(self, "reasoning_toggle_btn"):
                self.reasoning_toggle_btn.configure(text="显示思考区")

        self.storage.update_settings(show_reasoning_panel=self.is_reasoning_visible)

    def clear_source(self) -> None:
        textbox_clear(self.source_text, placeholder=True)
        self.update_char_count()

    def swap_languages(self) -> None:
        src = self.source_lang_menu.get()
        tgt = self.target_lang_menu.get()
        if src == "自动检测":
            self._show_toast("无法交换", "源语言为自动检测时暂不能交换语言。")
            return
        if src in TARGET_LANG_OPTIONS:
            self.target_lang_menu.set(src)
        if tgt in LANG_OPTIONS:
            self.source_lang_menu.set(tgt)

    def set_reasoning(self, text: str, append: bool = False, typewriter: bool = False) -> None:
        self.reasoning_text.configure(state="normal")
        if not append:
            self.reasoning_text.delete("1.0", "end")
        if typewriter:
            self._reasoning_buffer.append(text)
            if not self._reasoning_typing:
                self._type_reasoning()
        else:
            self.reasoning_text.insert("end", text)
            self.reasoning_text.see("end")
        self.reasoning_text.configure(state="disabled")

    def _type_reasoning(self) -> None:
        self._reasoning_typing = True
        if not self._reasoning_buffer:
            self._reasoning_typing = False
            return
        self.reasoning_text.configure(state="normal")
        chunk = self._reasoning_buffer[0]
        take = min(6, len(chunk))
        self.reasoning_text.insert("end", chunk[:take])
        self.reasoning_text.see("end")
        self.reasoning_text.configure(state="disabled")
        self._reasoning_buffer[0] = chunk[take:]
        if not self._reasoning_buffer[0]:
            self._reasoning_buffer.pop(0)
        self.after(16, self._type_reasoning)

    def append_result(self, text: str) -> None:
        textbox_insert_user_text(self.result_text, text, "end")
        self.result_text.see("end")

    def translate_text(self) -> None:
        source = textbox_get_clean(self.source_text)
        if not source:
            self._shake_widget(self.left_card)
            self._show_toast("请先输入原文", "输入文本后可按 Ctrl+Enter 开始翻译。")
            return
        api = self.get_selected_api()
        agent = self.get_selected_agent()
        if not api:
            messagebox.showwarning("缺少 API", "请先在 设置 → API 配置 中添加并启用 API。")
            return
        if not api.get("api_key"):
            if not messagebox.askyesno("API Key 为空", "当前 API Key 为空，请确认你是否使用本地或免 Key 服务。是否继续？"):
                return
        if not agent:
            messagebox.showwarning("缺少 Agent", "请先配置 Agent。")
            return

        textbox_clear(self.result_text)
        self._reasoning_buffer.clear()
        self.set_reasoning("翻译中…\n")
        self.translate_button.configure(state="disabled", text="翻译中…")
        self.update_status("翻译中")

        source_lang = self.source_lang_menu.get()
        target_lang = self.target_lang_menu.get()
        self.storage.update_settings(default_source_lang=source_lang, default_target_lang=target_lang)
        glossary_prompt = glossary_to_prompt(self.storage.get_glossary())
        system_prompt = (
            f"{agent.get('prompt', '')}\n\n"
            f"当前翻译任务：源语言={source_lang}，目标语言={target_lang}。"
            "请只输出译文，不要输出解释、标题、前后缀说明。"
            f"{glossary_prompt}"
        )
        user_prompt = f"请翻译以下文本：\n\n{source}"
        stream = bool(api.get("stream_enabled"))
        retry = int(self.storage.get_settings().get("auto_retry", 1))

        def worker() -> None:
            final_holder: List[str] = []
            reasoning_seen = False
            try:
                client = LLMClient(api)
                def on_delta(delta: StreamDelta) -> None:
                    nonlocal reasoning_seen
                    if delta.reasoning:
                        reasoning_seen = True
                        self.ui_queue.put({"type": "reasoning", "text": delta.reasoning})
                    if delta.content:
                        final_holder.append(delta.content)
                        self.ui_queue.put({"type": "content", "text": delta.content})
                result = client.complete(system_prompt, user_prompt, stream=stream, on_delta=on_delta, retry=retry)
                if not stream and result and not final_holder:
                    final_holder.append(result)
                    self.ui_queue.put({"type": "content", "text": result})
                self.ui_queue.put({
                    "type": "done",
                    "source": source,
                    "result": "".join(final_holder) or result,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "agent": agent.get("name", ""),
                    "api": api.get("api_name", ""),
                    "model": api.get("model_name", ""),
                    "reasoning_seen": reasoning_seen,
                })
            except Exception as exc:
                self.ui_queue.put({"type": "error", "error": str(exc)})
        self.current_translation_thread = threading.Thread(target=worker, daemon=True)
        self.current_translation_thread.start()

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                event = self.ui_queue.get_nowait()
                typ = event.get("type")
                if typ == "reasoning":
                    current = self.reasoning_text.get("1.0", "end").strip()
                    if current.startswith("翻译中"):
                        self.set_reasoning("")
                    self.set_reasoning(event.get("text", ""), append=True, typewriter=True)
                elif typ == "content":
                    self.append_result(event.get("text", ""))
                elif typ == "done":
                    if not event.get("reasoning_seen"):
                        self.set_reasoning("该模型未返回 reasoning_content。翻译已完成。")
                    self.translate_button.configure(state="normal", text="翻译  Ctrl+Enter")
                    self.update_status("翻译完成")
                    self.storage.add_history({
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source_text": event.get("source", ""),
                        "result_text": event.get("result", ""),
                        "source_lang": event.get("source_lang", ""),
                        "target_lang": event.get("target_lang", ""),
                        "agent": event.get("agent", ""),
                        "api": event.get("api", ""),
                        "model": event.get("model", ""),
                    })
                    self._show_toast("翻译完成", "译文已写入结果区，并自动保存到历史记录。")
                elif typ == "error":
                    self.translate_button.configure(state="normal", text="翻译  Ctrl+Enter")
                    self.update_status("翻译失败")
                    self.set_reasoning(f"错误：{event.get('error', '')}")
                    messagebox.showerror("翻译失败", event.get("error", "未知错误"))
        except queue.Empty:
            pass
        self.after(80, self._poll_ui_queue)

    def copy_result(self) -> None:
        result = textbox_get_clean(self.result_text)
        if not result:
            self._show_toast("暂无译文", "翻译完成后再复制结果。")
            return
        self.clipboard_clear()
        self.clipboard_append(result)
        self.update_status("译文已复制")
        self._show_toast("已复制", "译文已复制到剪贴板。")

    def pin_compare(self) -> None:
        # “固定对比”现在作为开关使用：再次点击即可关闭对比区。
        if self.compare_frame.winfo_ismapped():
            self.compare_frame.grid_remove()
            self.pinned_result = ""
            if hasattr(self, "pin_compare_btn"):
                self.pin_compare_btn.configure(text="固定对比")
            self._show_toast("已关闭对比", "固定对比区已收起。")
            return

        result = textbox_get_clean(self.result_text)
        if not result:
            self._show_toast("无法固定", "当前没有可固定的译文。")
            return
        self.pinned_result = result
        self.compare_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.pinned_text.configure(state="normal")
        self.current_compare_text.configure(state="normal")
        self.pinned_text.delete("1.0", "end")
        self.current_compare_text.delete("1.0", "end")
        self.pinned_text.insert("1.0", self.pinned_result)
        self.current_compare_text.insert("1.0", result)
        self.pinned_text.configure(state="disabled")
        self.current_compare_text.configure(state="disabled")
        if hasattr(self, "pin_compare_btn"):
            self.pin_compare_btn.configure(text="关闭对比")
        self._show_toast("已开启对比", "当前译文已固定，可重新翻译后对照查看。")


    def check_glossary_hits(self) -> None:
        source = textbox_get_clean(self.source_text)
        result = textbox_get_clean(self.result_text)
        if not source:
            self._show_toast("无法检查", "原文为空。")
            return
        if not result:
            self._show_toast("无法检查", "译文为空，请先完成翻译。")
            return
        glossary = self.storage.get_glossary()
        if not glossary:
            self._show_toast("暂无术语", "请先在术语库中添加术语。")
            return
        analysis = analyze_glossary_hits(source, result, glossary)
        if int(analysis.get("relevant_terms", 0) or 0) == 0:
            self._show_toast("没有相关术语", "术语库中的词没有出现在本次原文里。")
        GlossaryCheckDialog(self, analysis)

    def export_result(self) -> None:
        result = textbox_get_clean(self.result_text)
        if not result:
            messagebox.showwarning("无译文", "没有可导出的译文。")
            return
        path = filedialog.asksaveasfilename(
            title="导出译文",
            defaultextension=".docx",
            filetypes=[("Word 文档", "*.docx"), ("文本文件", "*.txt")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".txt"):
                export_txt(path, result)
            else:
                export_docx(path, result)
            self._show_toast("导出成功", f"译文已导出：{path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def upload_document(self) -> None:
        path = filedialog.askopenfilename(
            title="选择文档",
            filetypes=[("支持的文档", "*.docx *.doc *.pdf *.txt"), ("Word 文档", "*.docx *.doc"), ("PDF", "*.pdf"), ("文本", "*.txt")],
        )
        if path:
            self.start_document_translation(path)

    def start_document_translation(self, path: str) -> None:
        api = self.get_selected_api()
        agent = self.get_selected_agent()
        if not api or not agent:
            messagebox.showwarning("配置不完整", "请先选择 API 和 Agent。")
            return
        try:
            text = self.doc_translator.extract_text(path)
        except DocumentFormatError as exc:
            messagebox.showwarning("文档格式提示", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))
            return
        chars = count_chars(text)
        threshold = int(self.storage.get_settings().get("long_doc_threshold", 5000))
        if chars > threshold:
            seconds = self.doc_translator.estimate_duration_seconds(chars)
            mins = max(1, seconds // 60)
            ok = messagebox.askyesno(
                "文档较长",
                f"文档约 {chars} 字，翻译可能耗时较久，估算约 {mins} 分钟。是否继续？"
            )
            if not ok:
                return
        output_format = "docx" if Path(path).suffix.lower() in [".docx", ".doc", ".pdf"] else "txt"
        if Path(path).suffix.lower() == ".pdf":
            ok = messagebox.askyesno("PDF 输出说明", "PDF 将尽量抽取文本翻译，复杂版式可能无法保留。是否输出为 docx？选择“否”将输出 txt。")
            output_format = "docx" if ok else "txt"
        task = BackgroundTask(
            title=f"文档翻译：{Path(path).name}",
            kind="document_translation",
            payload={
                "source_path": path,
                "api_config": api,
                "agent": agent,
                "source_lang": self.source_lang_menu.get(),
                "target_lang": self.target_lang_menu.get(),
                "output_format": output_format,
                "retry": int(self.storage.get_settings().get("auto_retry", 1)),
            },
            progress_total=0,
        )
        self.task_manager.add_task(task, self.doc_translator.run_task)
        self.update_status("文档任务已进入后台队列")
        self._show_toast("任务已创建", "文档翻译已进入后台队列，你可以继续使用普通翻译。")

    def _poll_task_events(self) -> None:
        try:
            while True:
                ev = self.task_manager.events.get_nowait()
                self.update_status(ev.get("message", ""))
                self._refresh_task_panel()
                if ev.get("event") == "done" and ev.get("output_path"):
                    self._flash_window()
                    self._show_toast("后台任务完成", f"输出文件：{ev.get('output_path')}")
                elif ev.get("event") == "error":
                    messagebox.showerror("后台任务失败", ev.get("error", "未知错误"))
        except queue.Empty:
            pass
        self.after(600, self._poll_task_events)

    def _spin_task_icon(self) -> None:
        running = self._running_task_count()
        arrow = "▴" if self.is_task_panel_visible else "▾"
        if running > 0:
            self._spinner_index = (self._spinner_index + 1) % len(SPINNER_FRAMES)
            suffix = SPINNER_FRAMES[self._spinner_index]
            self.status_task_icon.configure(text=f"后台任务运行中{suffix}")
            self.task_btn.configure(text=f"后台任务{suffix} {arrow}")
        else:
            self.status_task_icon.configure(text="")
            self.task_btn.configure(text=f"后台任务 {arrow}")
        if self.is_task_panel_visible:
            self._refresh_task_panel()
        self.after(300, self._spin_task_icon)

    def toggle_task_panel(self) -> None:
        # 打开独立的后台任务中心。相比旧版附着式弹层，普通窗口不会被主界面底部遮挡，
        # 可自由拖动、缩放，也更适合展示多个任务进度和输出目录设置。
        self.open_task_manager()

    def _close_task_dropdown(self) -> None:
        if self._task_dropdown is not None and self._task_dropdown.winfo_exists():
            self._task_dropdown.destroy()
        self._task_dropdown = None
        self.is_task_panel_visible = False
        self._spin_task_icon_once()

    def _spin_task_icon_once(self) -> None:
        running = self._running_task_count()
        arrow = "▴" if self.is_task_panel_visible else "▾"
        suffix = "…" if running > 0 else ""
        self.task_btn.configure(text=f"后台任务{suffix} {arrow}")

    def _refresh_task_panel(self) -> None:
        if not hasattr(self, "task_list_frame"):
            return
        for child in self.task_list_frame.winfo_children():
            child.destroy()
        tasks = list(self.task_manager.all().values())
        if not tasks:
            label(self.task_list_frame, "暂无后台任务", size=12, secondary=True).grid(row=0, column=0, padx=8, pady=10, sticky="w")
            return
        for row, task in enumerate(tasks[-6:]):
            state = task.state.value if hasattr(task.state, "value") else str(task.state)
            total = task.progress_total or 0
            done = task.progress_done or 0
            percent = int(done * 100 / total) if total else 0
            title = task.title if len(task.title) <= 18 else task.title[:17] + "…"
            blocks = max(0, min(10, percent // 10))
            bar_text = "█" * blocks + "░" * (10 - blocks)
            info = f"{title}\n{state}  {done}/{total or '-'}  {percent}%  {task.message}\n{bar_text}"
            label(self.task_list_frame, info, size=11, secondary=True, justify="left", wraplength=210).grid(row=row, column=0, columnspan=2, padx=8, pady=(8 if row == 0 else 4, 4), sticky="ew")

    def _get_task_output_dir(self) -> Path:
        settings = self.storage.get_settings()
        configured_dir = str(settings.get("task_output_dir", "") or "").strip()
        out_dir = Path(configured_dir).expanduser() if configured_dir else Path.home() / ".cloudlingo_studio" / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def open_task_output_dir(self) -> None:
        self.open_path(str(self._get_task_output_dir()))

    def _shake_widget(self, widget) -> None:
        try:
            info = widget.grid_info()
            original_padx = info.get("padx", 0)
            seq = [-8, 8, -6, 6, -3, 3, 0]
            def step(i: int = 0):
                if i >= len(seq):
                    widget.grid_configure(padx=original_padx)
                    return
                base_left, base_right = (0, 12)
                if isinstance(original_padx, tuple):
                    base_left, base_right = original_padx
                widget.grid_configure(padx=(base_left + seq[i], base_right - seq[i]))
                self.after(26, lambda: step(i + 1))
            step()
        except Exception:
            pass

    def _show_toast(self, title: str, message: str = "") -> None:
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        try:
            toast.attributes("-alpha", 0.94)
        except Exception:
            pass
        toast.configure(fg_color=pair("bg"))
        box = card(toast)
        box.pack(fill="both", expand=True, padx=2, pady=2)
        label(box, title, size=13, weight="bold").pack(anchor="w", padx=14, pady=(12, 2))
        if message:
            label(box, message, size=12, secondary=True, wraplength=310, justify="left").pack(anchor="w", padx=14, pady=(0, 12))
        w, h = 360, 88 if message else 56
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        start_x = screen_w
        end_x = screen_w - w - 24
        y = self.winfo_rooty() + 72
        toast.geometry(f"{w}x{h}+{start_x}+{y}")
        steps = 12
        def slide(i: int = 0):
            if not toast.winfo_exists():
                return
            if i <= steps:
                x = int(start_x + (end_x - start_x) * (i / steps))
                toast.geometry(f"{w}x{h}+{x}+{y}")
                self.after(14, lambda: slide(i + 1))
            else:
                toast.after(2400, toast.destroy)
        slide()

    def _flash_window(self) -> None:
        try:
            self.attributes("-topmost", True)
            self.after(250, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    def open_task_manager(self) -> None:
        TaskManagerDialog(self, self.task_manager, self.open_path, self.storage, self.open_task_output_dir)

    def open_path(self, path: str) -> None:
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f"open '{path}'")
            else:
                os.system(f"xdg-open '{path}'")
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def open_api_config(self) -> None:
        APIConfigDialog(self, self.storage, self.refresh_selectors)

    def open_agent_config(self) -> None:
        AgentConfigDialog(self, self.storage, self.refresh_selectors)

    def open_glossary(self) -> None:
        GlossaryDialog(self, self.storage, lambda: None)

    def open_preferences(self) -> None:
        def changed():
            s = self.storage.get_settings()
            self.i18n.set_lang(s.get("language", "zh"))
            self.task_manager.configure_concurrency(s.get("max_concurrent_doc_tasks", 2))
            self.update_status("偏好设置已更新")
            self._show_toast("偏好设置已更新", "新的参数已保存。")
        PreferencesDialog(self, self.storage, changed)

    def open_history(self) -> None:
        def reuse(src: str, res: str) -> None:
            textbox_clear(self.source_text)
            textbox_insert_user_text(self.source_text, src, "1.0")
            textbox_clear(self.result_text)
            textbox_insert_user_text(self.result_text, res, "1.0")
            self.update_char_count()
        HistoryDialog(self, self.storage, reuse)


def run_app() -> None:
    app = TranslatorProApp()
    app.mainloop()
