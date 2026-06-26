from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk, BooleanVar

from translator_pro.api.client import LLMClient
from translator_pro.utils.exporter import export_docx, export_txt
from translator_pro.utils.tasks import TaskState
from translator_pro.utils.defaults import APP_NAME
from translator_pro.gui.ui_style import (
    pair, font, card, soft_frame, modern_button, modern_option_menu, label,
    bind_focus_glow, apply_textbox_typography, setup_ttk_style, apply_recursive_fonts
)


PROVIDERS = ["openai_compatible", "anthropic", "gemini"]
LANGS = ["中文", "English"]


def _entry(parent, value: Any = "", width: int = 260, show: str | None = None):
    e = ctk.CTkEntry(parent, width=width, show=show, font=font(parent, 13), corner_radius=8)
    e.insert(0, "" if value is None else str(value))
    bind_focus_glow(e)
    return e


def _bool(parent, value: bool = False, text: str = ""):
    var = BooleanVar(value=bool(value))
    cb = ctk.CTkCheckBox(parent, text=text, variable=var, font=font(parent, 13))
    return cb, var


class BaseDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, size: str = "760x560") -> None:
        super().__init__(master)
        self.title(title)
        self.geometry(size)
        self.configure(fg_color=pair("bg"))
        setup_ttk_style(self)
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.after(100, self.lift)
        self.after(180, lambda: apply_recursive_fonts(self, self))


class APIConfigDialog(BaseDialog):
    def __init__(self, master, storage, on_change: Callable[[], None]) -> None:
        super().__init__(master, "设置 → API 配置", "920x680")
        self.minsize(860, 560)
        self.storage = storage
        self.on_change = on_change
        self.selected_id: Optional[str] = None
        self.vars: Dict[str, Any] = {}
        self._build()
        self.refresh_list()

    def _build(self) -> None:
        root = card(self, corner_radius=16)
        root.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        left = card(root, corner_radius=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        left.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left, text="API 列表", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.listbox = ctk.CTkScrollableFrame(left, width=260, corner_radius=12, fg_color=pair("card_soft"), border_color=pair("border"), border_width=1)
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        modern_button(btns, text="新增", command=self.new_api, width=78).pack(side="left", padx=4)
        modern_button(btns, text="删除", command=self.delete_api, width=78, kind="danger").pack(side="left", padx=4)

        # 右侧配置项较多，原来使用 CTkFrame 在部分屏幕缩放下会超出窗口，
        # 导致底部按钮被遮挡且无法滚动。改为 CTkScrollableFrame。
        right = ctk.CTkScrollableFrame(root, corner_radius=14, width=620, fg_color=pair("card"), border_color=pair("border"), border_width=1)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(1, weight=1)
        labels = [
            ("API 名称", "api_name"), ("Provider", "provider"), ("API Key", "api_key"),
            ("Base URL", "base_url"), ("模型名称", "model_name"), ("温度", "temperature"),
            ("max_tokens", "max_tokens"), ("HTTP 代理", "http_proxy"), ("HTTPS 代理", "https_proxy"),
            ("超时秒数", "timeout"),
        ]
        for i, (lab, key) in enumerate(labels):
            ctk.CTkLabel(right, text=lab).grid(row=i, column=0, padx=12, pady=7, sticky="e")
            if key == "provider":
                self.vars[key] = modern_option_menu(right, values=PROVIDERS, width=460)
            else:
                self.vars[key] = _entry(right, "", width=460, show="*" if key == "api_key" else None)
            self.vars[key].grid(row=i, column=1, padx=12, pady=7, sticky="ew")
        self.enabled_cb, self.vars["enabled"] = _bool(right, False, "启用该 API")
        self.enabled_cb.grid(row=10, column=1, padx=12, pady=6, sticky="w")
        self.stream_cb, self.vars["stream_enabled"] = _bool(right, True, "启用流式输出")
        self.stream_cb.grid(row=11, column=1, padx=12, pady=6, sticky="w")
        self.reasoning_cb, self.vars["supports_reasoning"] = _bool(right, False, "支持 reasoning_content 思考展示")
        self.reasoning_cb.grid(row=12, column=1, padx=12, pady=6, sticky="w")

        self.status_label = ctk.CTkLabel(right, text="连接状态：未测试")
        self.status_label.grid(row=13, column=0, columnspan=2, padx=12, pady=(10, 4), sticky="w")
        bottom = ctk.CTkFrame(right, fg_color="transparent")
        bottom.grid(row=14, column=0, columnspan=2, padx=12, pady=12, sticky="ew")
        modern_button(bottom, text="测试连接", command=self.test_api).pack(side="left", padx=4)
        modern_button(bottom, text="保存", command=self.save_api).pack(side="right", padx=4)
        modern_button(bottom, text="关闭", command=self.destroy, kind="secondary").pack(side="right", padx=4)

    def refresh_list(self) -> None:
        for w in self.listbox.winfo_children():
            w.destroy()
        apis = self.storage.get_apis()
        for api in apis:
            name = api.get("api_name", "未命名")
            status = api.get("last_status", "未测试")
            text = f"{name}\n{api.get('model_name', '')} | {status}"
            btn = modern_button(self.listbox, text=text, anchor="w", height=54, command=lambda x=api: self.load_api(x))
            btn.pack(fill="x", pady=5)
        if apis and self.selected_id is None:
            self.load_api(apis[0])

    def new_api(self) -> None:
        self.selected_id = None
        self._fill({
            "api_name": "新 API", "provider": "openai_compatible", "api_key": "", "base_url": "",
            "model_name": "", "temperature": 0.2, "max_tokens": 4096, "enabled": True,
            "stream_enabled": True, "supports_reasoning": False, "http_proxy": "", "https_proxy": "", "timeout": 60,
        })
        self.status_label.configure(text="连接状态：未测试")

    def load_api(self, api: Dict[str, Any]) -> None:
        self.selected_id = api.get("id")
        self._fill(api)
        latency = api.get("last_latency_ms")
        lat = f"，耗时 {latency} ms" if latency is not None else ""
        self.status_label.configure(text=f"连接状态：{api.get('last_status', '未测试')}{lat}")

    def _fill(self, api: Dict[str, Any]) -> None:
        for key, widget in self.vars.items():
            if isinstance(widget, BooleanVar):
                widget.set(bool(api.get(key)))
            elif key == "provider":
                widget.set(api.get(key, "openai_compatible"))
            else:
                widget.delete(0, "end")
                widget.insert(0, "" if api.get(key) is None else str(api.get(key)))

    def _collect(self) -> Dict[str, Any]:
        def to_float(v: str, default: float) -> float:
            try:
                return float(v)
            except Exception:
                return default
        def to_int(v: str, default: int) -> int:
            try:
                return int(v)
            except Exception:
                return default
        api = {
            "id": self.selected_id,
            "api_name": self.vars["api_name"].get().strip() or "未命名 API",
            "provider": self.vars["provider"].get(),
            "api_key": self.vars["api_key"].get().strip(),
            "base_url": self.vars["base_url"].get().strip(),
            "model_name": self.vars["model_name"].get().strip(),
            "temperature": to_float(self.vars["temperature"].get(), 0.2),
            "max_tokens": to_int(self.vars["max_tokens"].get(), 4096),
            "enabled": self.vars["enabled"].get(),
            "stream_enabled": self.vars["stream_enabled"].get(),
            "supports_reasoning": self.vars["supports_reasoning"].get(),
            "http_proxy": self.vars["http_proxy"].get().strip(),
            "https_proxy": self.vars["https_proxy"].get().strip(),
            "timeout": to_int(self.vars["timeout"].get(), 60),
            "last_status": "未测试",
            "last_latency_ms": None,
        }
        return api

    def save_api(self) -> None:
        api = self._collect()
        old = self.storage.get_api(api["id"]) if api.get("id") else None
        if old:
            api["last_status"] = old.get("last_status", "未测试")
            api["last_latency_ms"] = old.get("last_latency_ms")
        saved = self.storage.upsert_api(api)
        self.selected_id = saved.get("id")
        self.on_change()
        self.refresh_list()
        messagebox.showinfo("已保存", "API 配置已保存。")

    def delete_api(self) -> None:
        if not self.selected_id:
            return
        if messagebox.askyesno("确认删除", "确定删除当前 API 配置吗？"):
            self.storage.delete_api(self.selected_id)
            self.selected_id = None
            self.on_change()
            self.refresh_list()
            self.new_api()

    def test_api(self) -> None:
        api = self._collect()
        self.status_label.configure(text="连接状态：测试中…")
        self.update_idletasks()
        ok, msg, ms = LLMClient(api).test_connection()
        api["last_status"] = "成功" if ok else f"失败：{msg[:120]}"
        api["last_latency_ms"] = ms
        saved = self.storage.upsert_api(api)
        self.selected_id = saved.get("id")
        self.status_label.configure(text=f"连接状态：{api['last_status']}，耗时 {ms} ms")
        self.on_change()
        self.refresh_list()


class AgentConfigDialog(BaseDialog):
    def __init__(self, master, storage, on_change: Callable[[], None]) -> None:
        super().__init__(master, "设置 → Agent 配置", "880x600")
        self.storage = storage
        self.on_change = on_change
        self.selected_id: Optional[str] = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = card(self, corner_radius=16)
        root.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)
        left = card(root, corner_radius=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(left, text="Agent 列表", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.listbox = ctk.CTkScrollableFrame(left, width=240, corner_radius=12, fg_color=pair("card_soft"), border_color=pair("border"), border_width=1)
        self.listbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        b = ctk.CTkFrame(left, fg_color="transparent")
        b.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        modern_button(b, text="新增", command=self.new_agent, width=76).pack(side="left", padx=4)
        modern_button(b, text="删除", command=self.delete_agent, width=76, kind="danger").pack(side="left", padx=4)
        # 右侧配置项较多，原来使用 CTkFrame 在部分屏幕缩放下会超出窗口，
        # 导致底部按钮被遮挡且无法滚动。改为 CTkScrollableFrame。
        right = ctk.CTkScrollableFrame(root, corner_radius=14, width=620, fg_color=pair("card"), border_color=pair("border"), border_width=1)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(1, weight=1)
        right.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(right, text="Agent 名称").grid(row=0, column=0, padx=12, pady=8, sticky="e")
        self.name_entry = _entry(right, width=480)
        self.name_entry.grid(row=0, column=1, padx=12, pady=8, sticky="ew")
        ctk.CTkLabel(right, text="默认 API").grid(row=1, column=0, padx=12, pady=8, sticky="e")
        self.api_menu = modern_option_menu(right, values=["无"], width=480)
        self.api_menu.grid(row=1, column=1, padx=12, pady=8, sticky="ew")
        ctk.CTkLabel(right, text="默认模型").grid(row=2, column=0, padx=12, pady=8, sticky="e")
        self.model_entry = _entry(right, width=480)
        self.model_entry.grid(row=2, column=1, padx=12, pady=8, sticky="ew")
        ctk.CTkLabel(right, text="系统提示词 Prompt").grid(row=3, column=0, padx=12, pady=8, sticky="ne")
        self.prompt_box = ctk.CTkTextbox(right, height=320, corner_radius=12, font=font(right, 14), fg_color=pair("card"), border_color=pair("border"), border_width=1, text_color=pair("text"))
        self.prompt_box.grid(row=3, column=1, padx=12, pady=8, sticky="nsew")
        bottom = ctk.CTkFrame(right, fg_color="transparent")
        bottom.grid(row=4, column=0, columnspan=2, padx=12, pady=12, sticky="ew")
        modern_button(bottom, text="保存", command=self.save_agent).pack(side="right", padx=4)
        modern_button(bottom, text="关闭", command=self.destroy, kind="secondary").pack(side="right", padx=4)

    def refresh_api_menu(self) -> None:
        self.apis = self.storage.get_apis()
        names = [a.get("api_name", "未命名") for a in self.apis] or ["无"]
        self.api_menu.configure(values=names)
        self.api_menu.set(names[0])

    def refresh(self) -> None:
        self.refresh_api_menu()
        for w in self.listbox.winfo_children():
            w.destroy()
        agents = self.storage.get_agents()
        for ag in agents:
            modern_button(self.listbox, text=ag.get("name", "未命名"), anchor="w", height=42, command=lambda x=ag: self.load_agent(x)).pack(fill="x", pady=5)
        if agents and self.selected_id is None:
            self.load_agent(agents[0])

    def new_agent(self) -> None:
        self.selected_id = None
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, "新 Agent")
        self.model_entry.delete(0, "end")
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", "你是一名专业翻译。请准确翻译用户输入。")

    def load_agent(self, ag: Dict[str, Any]) -> None:
        self.selected_id = ag.get("id")
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, ag.get("name", ""))
        self.model_entry.delete(0, "end")
        self.model_entry.insert(0, ag.get("default_model", ""))
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", ag.get("prompt", ""))
        api_id = ag.get("default_api_id")
        for api in self.apis:
            if api.get("id") == api_id:
                self.api_menu.set(api.get("api_name", "未命名"))
                break

    def _selected_api_id(self) -> str:
        name = self.api_menu.get()
        for api in self.apis:
            if api.get("api_name") == name:
                return api.get("id", "")
        return ""

    def save_agent(self) -> None:
        ag = {
            "id": self.selected_id,
            "name": self.name_entry.get().strip() or "未命名 Agent",
            "default_api_id": self._selected_api_id(),
            "default_model": self.model_entry.get().strip(),
            "prompt": self.prompt_box.get("1.0", "end").strip(),
        }
        saved = self.storage.upsert_agent(ag)
        self.selected_id = saved.get("id")
        self.on_change()
        self.refresh()
        messagebox.showinfo("已保存", "Agent 配置已保存。")

    def delete_agent(self) -> None:
        if self.selected_id and messagebox.askyesno("确认删除", "确定删除当前 Agent 吗？"):
            self.storage.delete_agent(self.selected_id)
            self.selected_id = None
            self.on_change()
            self.refresh()
            self.new_agent()


class GlossaryDialog(BaseDialog):
    def __init__(self, master, storage, on_change: Callable[[], None]) -> None:
        super().__init__(master, "设置 → 术语库管理", "780x560")
        self.storage = storage
        self.on_change = on_change
        self.selected_id: Optional[str] = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = card(self, corner_radius=16)
        root.grid(row=0, column=0, padx=14, pady=14, sticky="nsew")
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)
        self.table = ttk.Treeview(root, columns=("source", "target", "note"), show="headings", height=14)
        self.table.heading("source", text="原术语")
        self.table.heading("target", text="目标译名")
        self.table.heading("note", text="备注")
        self.table.column("source", width=180)
        self.table.column("target", width=180)
        self.table.column("note", width=300)
        self.table.grid(row=0, column=0, columnspan=4, padx=12, pady=12, sticky="nsew")
        self.table.bind("<<TreeviewSelect>>", self.on_select)
        ctk.CTkLabel(root, text="原术语").grid(row=1, column=0, padx=12, pady=4, sticky="w")
        self.source_entry = _entry(root, width=220)
        self.source_entry.grid(row=2, column=0, padx=12, pady=4, sticky="ew")
        ctk.CTkLabel(root, text="目标译名").grid(row=1, column=1, padx=12, pady=4, sticky="w")
        self.target_entry = _entry(root, width=220)
        self.target_entry.grid(row=2, column=1, padx=12, pady=4, sticky="ew")
        ctk.CTkLabel(root, text="备注").grid(row=1, column=2, padx=12, pady=4, sticky="w")
        self.note_entry = _entry(root, width=250)
        self.note_entry.grid(row=2, column=2, padx=12, pady=4, sticky="ew")
        modern_button(root, text="保存术语", command=self.save_term).grid(row=2, column=3, padx=6, pady=4)
        b = ctk.CTkFrame(root, fg_color="transparent")
        b.grid(row=3, column=0, columnspan=4, padx=12, pady=12, sticky="ew")
        modern_button(b, text="新增", command=self.new_term).pack(side="left", padx=4)
        modern_button(b, text="删除", command=self.delete_term, kind="danger").pack(side="left", padx=4)
        modern_button(b, text="关闭", command=self.destroy, kind="secondary").pack(side="right", padx=4)

    def refresh(self) -> None:
        for row in self.table.get_children():
            self.table.delete(row)
        for term in self.storage.get_glossary():
            self.table.insert("", "end", iid=term.get("id"), values=(term.get("source", ""), term.get("target", ""), term.get("note", "")))

    def on_select(self, _event=None) -> None:
        sel = self.table.selection()
        if not sel:
            return
        self.selected_id = sel[0]
        vals = self.table.item(sel[0], "values")
        self.source_entry.delete(0, "end"); self.source_entry.insert(0, vals[0])
        self.target_entry.delete(0, "end"); self.target_entry.insert(0, vals[1])
        self.note_entry.delete(0, "end"); self.note_entry.insert(0, vals[2])

    def new_term(self) -> None:
        self.selected_id = None
        for e in (self.source_entry, self.target_entry, self.note_entry):
            e.delete(0, "end")

    def save_term(self) -> None:
        src = self.source_entry.get().strip()
        tgt = self.target_entry.get().strip()
        if not src or not tgt:
            messagebox.showwarning("缺少内容", "原术语和目标译名不能为空。")
            return
        self.storage.upsert_term({"id": self.selected_id, "source": src, "target": tgt, "note": self.note_entry.get().strip()})
        self.on_change()
        self.refresh()
        self.new_term()

    def delete_term(self) -> None:
        if self.selected_id:
            self.storage.delete_term(self.selected_id)
            self.on_change()
            self.refresh()
            self.new_term()


class GlossaryCheckDialog(BaseDialog):
    def __init__(self, master, analysis: Dict[str, Any]) -> None:
        super().__init__(master, "术语命中率检查", "880x600")
        self.analysis = analysis
        self._build()

    def _build(self) -> None:
        root = card(self, corner_radius=16)
        root.grid(row=0, column=0, padx=14, pady=14, sticky="nsew")
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)

        relevant = int(self.analysis.get("relevant_terms", 0) or 0)
        hit = int(self.analysis.get("hit_terms", 0) or 0)
        missing = int(self.analysis.get("missing_terms", 0) or 0)
        valid = int(self.analysis.get("valid_terms", 0) or 0)
        rate = float(self.analysis.get("hit_rate", 0.0) or 0.0)

        label(root, "术语命中率检查", size=20, weight="bold").grid(row=0, column=0, padx=14, pady=(14, 4), sticky="w")
        summary = (
            f"术语库共 {valid} 条；本次原文命中 {relevant} 条相关术语；"
            f"译文命中 {hit} 条，未命中 {missing} 条，命中率 {rate:.0%}。"
        )
        label(root, summary, size=13, secondary=True, wraplength=760, justify="left").grid(row=1, column=0, padx=14, pady=(0, 10), sticky="w")

        self.table = ttk.Treeview(
            root,
            columns=("status", "source", "target", "expected", "direction", "note"),
            show="headings",
            height=15,
        )
        headings = [
            ("status", "状态", 70),
            ("source", "原术语", 150),
            ("target", "目标译名", 150),
            ("expected", "本次期望出现", 150),
            ("direction", "判断方向", 130),
            ("note", "备注", 180),
        ]
        for col, title, width in headings:
            self.table.heading(col, text=title)
            self.table.column(col, width=width)
        self.table.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="nsew")

        for idx, row in enumerate(self.analysis.get("rows", [])):
            self.table.insert("", "end", iid=str(idx), values=(
                row.get("status", ""),
                row.get("source", ""),
                row.get("target", ""),
                row.get("expected", ""),
                row.get("direction", ""),
                row.get("note", ""),
            ))

        tips = (
            "说明：这里做的是简单字符串匹配，主要用于翻译后快速自查。"
            "如果模型用了同义表达、大小写或空格变化，可能需要人工确认。"
        )
        label(root, tips, size=12, secondary=True, wraplength=760, justify="left").grid(row=3, column=0, padx=14, pady=(0, 8), sticky="w")

        bottom = ctk.CTkFrame(root, fg_color="transparent")
        bottom.grid(row=4, column=0, padx=14, pady=(0, 14), sticky="ew")
        modern_button(bottom, text="复制报告", command=self.copy_report, kind="secondary").pack(side="left", padx=4)
        modern_button(bottom, text="关闭", command=self.destroy, kind="secondary").pack(side="right", padx=4)

    def copy_report(self) -> None:
        relevant = int(self.analysis.get("relevant_terms", 0) or 0)
        hit = int(self.analysis.get("hit_terms", 0) or 0)
        missing = int(self.analysis.get("missing_terms", 0) or 0)
        rate = float(self.analysis.get("hit_rate", 0.0) or 0.0)
        lines = [f"术语命中率：{hit}/{relevant}，未命中 {missing}，命中率 {rate:.0%}"]
        for row in self.analysis.get("rows", []):
            if row.get("hit") is False:
                lines.append(f"未命中：{row.get('source', '')} -> {row.get('target', '')}，期望出现：{row.get('expected', '')}")
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        messagebox.showinfo("已复制", "术语检查报告已复制到剪贴板。")


class HistoryDialog(BaseDialog):
    def __init__(self, master, storage, on_reuse: Callable[[str, str], None]) -> None:
        super().__init__(master, "历史记录", "900x560")
        self.storage = storage
        self.on_reuse = on_reuse
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = card(self, corner_radius=16)
        root.grid(row=0, column=0, padx=14, pady=14, sticky="nsew")
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)
        self.table = ttk.Treeview(root, columns=("time", "agent", "langs", "source", "result"), show="headings", height=14)
        for col, text, w in [("time", "时间", 140), ("agent", "Agent", 110), ("langs", "语言", 120), ("source", "原文摘要", 240), ("result", "译文摘要", 240)]:
            self.table.heading(col, text=text); self.table.column(col, width=w)
        self.table.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        b = ctk.CTkFrame(root, fg_color="transparent")
        b.grid(row=1, column=0, padx=12, pady=10, sticky="ew")
        modern_button(b, text="复用选中", command=self.reuse).pack(side="left", padx=4)
        modern_button(b, text="清空历史", command=self.clear, kind="danger").pack(side="left", padx=4)
        modern_button(b, text="关闭", command=self.destroy, kind="secondary").pack(side="right", padx=4)

    def refresh(self) -> None:
        for r in self.table.get_children():
            self.table.delete(r)
        for item in reversed(self.storage.get_history()):
            self.table.insert("", "end", iid=item.get("id"), values=(
                item.get("time", ""), item.get("agent", ""), f"{item.get('source_lang', '')}→{item.get('target_lang', '')}",
                (item.get("source_text", "")[:80]).replace("\n", " "),
                (item.get("result_text", "")[:80]).replace("\n", " "),
            ))

    def reuse(self) -> None:
        sel = self.table.selection()
        if not sel:
            return
        item_id = sel[0]
        for item in self.storage.get_history():
            if item.get("id") == item_id:
                self.on_reuse(item.get("source_text", ""), item.get("result_text", ""))
                self.destroy()
                return

    def clear(self) -> None:
        if messagebox.askyesno("确认", "确定清空历史记录吗？"):
            self.storage.clear_history()
            self.refresh()


class PreferencesDialog(BaseDialog):
    def __init__(self, master, storage, on_change: Callable[[], None]) -> None:
        super().__init__(master, "设置 → 偏好设置", "680x430")
        self.storage = storage
        self.on_change = on_change
        self._build()

    def _build(self) -> None:
        s = self.storage.get_settings()
        root = card(self, corner_radius=16)
        root.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        root.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(root, text="界面语言").grid(row=0, column=0, padx=14, pady=12, sticky="e")
        self.lang_menu = modern_option_menu(root, values=LANGS)
        self.lang_menu.set("中文" if s.get("language", "zh") == "zh" else "English")
        self.lang_menu.grid(row=0, column=1, padx=14, pady=12, sticky="ew")
        ctk.CTkLabel(root, text="长文档提醒阈值（字）").grid(row=1, column=0, padx=14, pady=12, sticky="e")
        self.threshold = _entry(root, s.get("long_doc_threshold", 5000), width=240)
        self.threshold.grid(row=1, column=1, padx=14, pady=12, sticky="ew")
        ctk.CTkLabel(root, text="后台任务并发上限").grid(row=2, column=0, padx=14, pady=12, sticky="e")
        self.concurrent = _entry(root, s.get("max_concurrent_doc_tasks", 2), width=240)
        self.concurrent.grid(row=2, column=1, padx=14, pady=12, sticky="ew")
        ctk.CTkLabel(root, text="API 自动重试次数").grid(row=3, column=0, padx=14, pady=12, sticky="e")
        self.retry = _entry(root, s.get("auto_retry", 1), width=240)
        self.retry.grid(row=3, column=1, padx=14, pady=12, sticky="ew")

        ctk.CTkLabel(root, text="后台任务输出目录").grid(row=4, column=0, padx=14, pady=12, sticky="e")
        output_row = ctk.CTkFrame(root, fg_color="transparent")
        output_row.grid(row=4, column=1, padx=14, pady=12, sticky="ew")
        output_row.grid_columnconfigure(0, weight=1)
        default_out = str(Path.home() / ".cloudlingo_studio" / "outputs")
        self.output_dir = _entry(output_row, s.get("task_output_dir") or default_out, width=360)
        self.output_dir.grid(row=0, column=0, sticky="ew")
        modern_button(output_row, text="选择", command=self.choose_output_dir, kind="secondary", width=72).grid(row=0, column=1, padx=(8, 0))

        b = ctk.CTkFrame(root, fg_color="transparent")
        b.grid(row=5, column=0, columnspan=2, padx=14, pady=18, sticky="ew")
        modern_button(b, text="保存", command=self.save).pack(side="right", padx=5)
        modern_button(b, text="关闭", command=self.destroy, kind="secondary").pack(side="right", padx=5)

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择后台任务输出目录")
        if selected:
            self.output_dir.delete(0, "end")
            self.output_dir.insert(0, selected)

    def save(self) -> None:
        def i(v, d):
            try: return int(v)
            except Exception: return d
        self.storage.update_settings(
            language="zh" if self.lang_menu.get() == "中文" else "en",
            long_doc_threshold=max(500, i(self.threshold.get(), 5000)),
            max_concurrent_doc_tasks=max(1, i(self.concurrent.get(), 2)),
            auto_retry=max(0, i(self.retry.get(), 1)),
            task_output_dir=self.output_dir.get().strip(),
        )
        self.on_change()
        messagebox.showinfo("已保存", "偏好设置已保存，部分界面文本将在重启后完全刷新。")


class TaskManagerDialog(BaseDialog):
    def __init__(self, master, manager, on_open_output: Callable[[str], None], storage=None, on_open_output_dir: Optional[Callable[[], None]] = None) -> None:
        super().__init__(master, "后台任务中心", "960x660")
        self.minsize(820, 560)
        self.manager = manager
        self.on_open_output = on_open_output
        self.storage = storage
        self.on_open_output_dir = on_open_output_dir
        self._build()
        self.refresh()
        self.after(1000, self._tick)

    def _build(self) -> None:
        root = card(self, corner_radius=18)
        root.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.grid(row=0, column=0, padx=18, pady=(18, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        label(header, "后台任务中心", size=20, weight="bold").grid(row=0, column=0, sticky="w")
        label(header, "查看多个文档翻译任务的状态、进度和输出结果", size=12, secondary=True).grid(row=1, column=0, pady=(2, 0), sticky="w")
        modern_button(header, "刷新", command=self.refresh, kind="secondary", width=72, height=32).grid(row=0, column=1, rowspan=2, padx=(8, 8), sticky="e")
        modern_button(header, "关闭", command=self.destroy, kind="secondary", width=72, height=32).grid(row=0, column=2, rowspan=2, sticky="e")

        output = soft_frame(root)
        output.grid(row=1, column=0, padx=18, pady=(0, 12), sticky="ew")
        output.grid_columnconfigure(1, weight=1)
        label(output, "输出文件夹", size=13, weight="bold").grid(row=0, column=0, padx=(14, 10), pady=14, sticky="w")
        self.output_dir_entry = _entry(output, self._current_output_dir(), width=360)
        self.output_dir_entry.grid(row=0, column=1, padx=(0, 8), pady=14, sticky="ew")
        modern_button(output, "选择", command=self.choose_output_dir, kind="secondary", width=72, height=32).grid(row=0, column=2, padx=(0, 8), pady=14)
        modern_button(output, "保存", command=self.save_output_dir, kind="primary", width=72, height=32).grid(row=0, column=3, padx=(0, 8), pady=14)
        modern_button(output, "打开", command=self.open_output_dir, kind="secondary", width=72, height=32).grid(row=0, column=4, padx=(0, 14), pady=14)

        self.task_list = ctk.CTkScrollableFrame(
            root,
            corner_radius=14,
            fg_color=pair("card_soft"),
            border_color=pair("border"),
            border_width=1,
        )
        self.task_list.grid(row=2, column=0, padx=18, pady=(0, 14), sticky="nsew")
        self.task_list.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(root, fg_color="transparent")
        footer.grid(row=3, column=0, padx=18, pady=(0, 18), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        label(footer, "提示：后台任务完成后可直接打开输出文件；未完成任务可暂停、继续或取消。", size=12, secondary=True).grid(row=0, column=0, sticky="w")

    def _current_output_dir(self) -> str:
        default_out = str(Path.home() / ".cloudlingo_studio" / "outputs")
        if self.storage is None:
            return default_out
        settings = self.storage.get_settings()
        return str(settings.get("task_output_dir") or default_out)

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择后台任务输出目录")
        if selected:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, selected)

    def save_output_dir(self) -> None:
        path = self.output_dir_entry.get().strip() or self._current_output_dir()
        try:
            Path(path).expanduser().mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("保存失败", f"输出目录不可用：{exc}")
            return
        if self.storage is not None:
            self.storage.update_settings(task_output_dir=path)
        messagebox.showinfo("已保存", "后台任务输出目录已更新。")

    def open_output_dir(self) -> None:
        self.save_output_dir()
        if self.on_open_output_dir is not None:
            self.on_open_output_dir()
        else:
            self.on_open_output(self.output_dir_entry.get().strip())

    def _state_label(self, state: str) -> str:
        mapping = {
            "pending": "等待中",
            "running": "运行中",
            "paused": "已暂停",
            "done": "已完成",
            "failed": "失败",
            "cancelled": "已取消",
        }
        return mapping.get(state, state)

    def _clear_tasks(self) -> None:
        for child in self.task_list.winfo_children():
            child.destroy()

    def refresh(self) -> None:
        self._clear_tasks()
        tasks = list(self.manager.all().values())
        if not tasks:
            empty = soft_frame(self.task_list)
            empty.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
            empty.grid_columnconfigure(0, weight=1)
            label(empty, "暂无后台任务", size=15, weight="bold").grid(row=0, column=0, padx=18, pady=(20, 4), sticky="w")
            label(empty, "上传长文档并确认后台翻译后，任务进度会显示在这里。", size=12, secondary=True).grid(row=1, column=0, padx=18, pady=(0, 20), sticky="w")
            return
        # 最新任务放在上方，方便用户看到当前状态。
        for row, task in enumerate(reversed(tasks)):
            self._render_task_card(row, task)

    def _render_task_card(self, row: int, task) -> None:
        frame = card(self.task_list, corner_radius=14)
        frame.grid(row=row, column=0, padx=12, pady=(12 if row == 0 else 6, 6), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)

        state = task.state.value if hasattr(task.state, "value") else str(task.state)
        total = int(task.progress_total or 0)
        done = int(task.progress_done or 0)
        ratio = float(done / total) if total else (1.0 if state == "done" else 0.0)
        percent = int(ratio * 100)

        title = task.title or "未命名任务"
        label(frame, title, size=14, weight="bold", wraplength=520, justify="left").grid(row=0, column=0, padx=16, pady=(14, 4), sticky="w")
        state_box = ctk.CTkLabel(
            frame,
            text=self._state_label(state),
            font=font(frame, 12, "bold"),
            corner_radius=999,
            fg_color=pair("accent_soft") if state in ("pending", "running", "paused") else pair("card_soft"),
            text_color=pair("accent") if state in ("pending", "running", "paused") else pair("text_secondary"),
            padx=10,
            pady=4,
        )
        state_box.grid(row=0, column=1, padx=16, pady=(14, 4), sticky="e")

        message = task.message or "等待任务状态更新"
        progress_text = f"{done}/{total}" if total else "-"
        label(frame, f"{message} · 进度 {progress_text} · {percent}%", size=12, secondary=True, wraplength=620, justify="left").grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="w")

        bar = ctk.CTkProgressBar(frame, height=10, corner_radius=999, progress_color=pair("accent"))
        bar.grid(row=2, column=0, columnspan=2, padx=16, pady=(0, 10), sticky="ew")
        bar.set(max(0.0, min(1.0, ratio)))

        output_path = str(task.output_path or "暂无输出文件")
        label(frame, output_path, size=11, secondary=True, wraplength=690, justify="left").grid(row=3, column=0, padx=16, pady=(0, 12), sticky="w")

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=3, column=1, padx=16, pady=(0, 12), sticky="e")
        modern_button(actions, "暂停", command=lambda tid=task.id: self.pause(tid), kind="secondary", width=54, height=28).pack(side="left", padx=3)
        modern_button(actions, "继续", command=lambda tid=task.id: self.resume(tid), kind="secondary", width=54, height=28).pack(side="left", padx=3)
        modern_button(actions, "取消", command=lambda tid=task.id: self.cancel(tid), kind="danger", width=54, height=28).pack(side="left", padx=3)
        open_btn = modern_button(actions, "打开", command=lambda tid=task.id: self.open_output(tid), kind="secondary", width=54, height=28)
        open_btn.pack(side="left", padx=3)
        if not task.output_path:
            open_btn.configure(state="disabled")

    def _tick(self) -> None:
        try:
            self.refresh()
            self.after(1000, self._tick)
        except Exception:
            pass

    def pause(self, task_id: Optional[str] = None) -> None:
        if task_id:
            self.manager.pause(task_id)
        self.refresh()

    def resume(self, task_id: Optional[str] = None) -> None:
        if task_id:
            self.manager.resume(task_id)
        self.refresh()

    def cancel(self, task_id: Optional[str] = None) -> None:
        if task_id:
            self.manager.cancel(task_id)
        self.refresh()

    def open_output(self, task_id: Optional[str] = None) -> None:
        if not task_id:
            return
        task = self.manager.get(task_id)
        if task and task.output_path:
            self.on_open_output(task.output_path)


class AboutDialog(BaseDialog):
    def __init__(self, master) -> None:
        super().__init__(master, "帮助", "560x360")
        box = ctk.CTkTextbox(self, corner_radius=16, font=font(self, 14), fg_color=pair("card"), border_color=pair("border"), border_width=1, text_color=pair("text"))
        box.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        box.insert("1.0", (
            f"{APP_NAME}\n\n"
            "快捷键：\n"
            "Ctrl+Enter：开始翻译\n"
            "Ctrl+Shift+C：复制译文\n\n"
            "菜单路径：\n"
            "设置 → API 配置：增删改 API，测试连接。\n"
            "设置 → Agent 配置：管理翻译 Agent 及其 Prompt。\n"
            "设置 → 术语库管理：维护翻译术语。\n"
            "设置 → 偏好设置：设置并发上限、长文档阈值、输出目录和界面语言。\n\n"
            "说明：PDF 翻译以文本抽取为主，复杂排版可能降级；.doc 需先转换为 .docx。"
        ))
        box.configure(state="disabled")
