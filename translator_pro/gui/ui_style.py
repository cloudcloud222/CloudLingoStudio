from __future__ import annotations

import json
import os
import platform
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Tuple

import customtkinter as ctk
from tkinter import font as tkfont, ttk


LIGHT = {
    "bg": "#F5F7FA",
    "card": "#FFFFFF",
    "card_soft": "#F8FAFC",
    "border": "#E8EDF3",
    "border_hover": "#C8D7EA",
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "accent_soft": "#DBEAFE",
    "text": "#1E293B",
    "text_secondary": "#64748B",
    "placeholder": "#94A3B8",
    "reasoning_bg": "#F0F4FF",
    "reasoning_text": "#475569",
    "shadow": "#E9EEF6",
    "danger": "#DC2626",
    "success": "#16A34A",
    "warning": "#D97706",
}

DARK = {
    "bg": "#0F172A",
    "card": "#1E293B",
    "card_soft": "#172033",
    "border": "#334155",
    "border_hover": "#475569",
    "accent": "#60A5FA",
    "accent_hover": "#93C5FD",
    "accent_soft": "#1D4ED8",
    "text": "#F1F5F9",
    "text_secondary": "#CBD5E1",
    "placeholder": "#94A3B8",
    "reasoning_bg": "#162138",
    "reasoning_text": "#CBD5E1",
    "shadow": "#0B1120",
    "danger": "#F87171",
    "success": "#4ADE80",
    "warning": "#FBBF24",
}


def pair(key: str) -> Tuple[str, str]:
    return (LIGHT[key], DARK[key])


THEME = {
    "CTk": {"fg_color": [LIGHT["bg"], DARK["bg"]]},
    "CTkToplevel": {"fg_color": [LIGHT["bg"], DARK["bg"]]},
    # customtkinter 的 CTkFont 会在 weight=None 时读取该默认项，
    # 自定义主题必须保留该键，否则会触发 KeyError: 'CTkFont'。
    "CTkFont": {
        "family": "Microsoft YaHei UI",
        "size": 13,
        "weight": "normal",
    },
    "CTkFrame": {
        "corner_radius": 12,
        "border_width": 1,
        "fg_color": [LIGHT["card"], DARK["card"]],
        "top_fg_color": [LIGHT["card"], DARK["card"]],
        "border_color": [LIGHT["border"], DARK["border"]],
    },
    "CTkScrollableFrame": {
        "label_fg_color": [LIGHT["card"], DARK["card"]],
        "fg_color": [LIGHT["card"], DARK["card"]],
        "scrollbar_button_color": ["#CBD5E1", "#475569"],
        "scrollbar_button_hover_color": ["#94A3B8", "#64748B"],
        "corner_radius": 12,
        "border_width": 1,
        "border_color": [LIGHT["border"], DARK["border"]],
    },
    "CTkButton": {
        "corner_radius": 8,
        "border_width": 0,
        "fg_color": [LIGHT["accent"], DARK["accent"]],
        "hover_color": [LIGHT["accent_hover"], DARK["accent_hover"]],
        "border_color": [LIGHT["border"], DARK["border"]],
        "text_color": ["#FFFFFF", "#0F172A"],
        "text_color_disabled": ["#94A3B8", "#64748B"],
    },
    "CTkLabel": {
        "corner_radius": 0,
        "fg_color": "transparent",
        "text_color": [LIGHT["text"], DARK["text"]],
    },
    "CTkEntry": {
        "corner_radius": 8,
        "border_width": 1,
        "fg_color": [LIGHT["card"], DARK["card"]],
        "border_color": [LIGHT["border"], DARK["border"]],
        "text_color": [LIGHT["text"], DARK["text"]],
        "placeholder_text_color": [LIGHT["placeholder"], DARK["placeholder"]],
    },
    "CTkCheckBox": {
        "corner_radius": 6,
        "border_width": 2,
        "fg_color": [LIGHT["accent"], DARK["accent"]],
        "hover_color": [LIGHT["accent_hover"], DARK["accent_hover"]],
        "border_color": [LIGHT["border_hover"], DARK["border_hover"]],
        "checkmark_color": ["#FFFFFF", "#0F172A"],
        "text_color": [LIGHT["text"], DARK["text"]],
        "text_color_disabled": ["#94A3B8", "#64748B"],
    },
    "CTkSwitch": {
        "corner_radius": 1000,
        "border_width": 2,
        "button_length": 0,
        "fg_color": ["#CBD5E1", "#475569"],
        "progress_color": [LIGHT["accent"], DARK["accent"]],
        "button_color": ["#FFFFFF", "#F8FAFC"],
        "button_hover_color": ["#F8FAFC", "#E2E8F0"],
        "text_color": [LIGHT["text"], DARK["text"]],
        "text_color_disabled": ["#94A3B8", "#64748B"],
    },
    "CTkOptionMenu": {
        "corner_radius": 8,
        "fg_color": [LIGHT["card"], DARK["card"]],
        "button_color": [LIGHT["card"], DARK["card"]],
        "button_hover_color": ["#EEF2F7", "#334155"],
        "text_color": [LIGHT["text"], DARK["text"]],
        "text_color_disabled": ["#94A3B8", "#64748B"],
    },
    "CTkComboBox": {
        "corner_radius": 8,
        "border_width": 1,
        "fg_color": [LIGHT["card"], DARK["card"]],
        "border_color": [LIGHT["border"], DARK["border"]],
        "button_color": [LIGHT["accent"], DARK["accent"]],
        "button_hover_color": [LIGHT["accent_hover"], DARK["accent_hover"]],
        "text_color": [LIGHT["text"], DARK["text"]],
        "text_color_disabled": ["#94A3B8", "#64748B"],
    },
    "CTkTextbox": {
        "corner_radius": 12,
        "border_width": 1,
        "fg_color": [LIGHT["card"], DARK["card"]],
        "border_color": [LIGHT["border"], DARK["border"]],
        "text_color": [LIGHT["text"], DARK["text"]],
        "scrollbar_button_color": ["#CBD5E1", "#475569"],
        "scrollbar_button_hover_color": ["#94A3B8", "#64748B"],
    },
    "CTkProgressBar": {
        "corner_radius": 1000,
        "border_width": 0,
        "fg_color": ["#E2E8F0", "#334155"],
        "progress_color": [LIGHT["accent"], DARK["accent"]],
        "border_color": [LIGHT["border"], DARK["border"]],
    },
    "CTkScrollbar": {
        "corner_radius": 1000,
        "border_spacing": 4,
        "fg_color": "transparent",
        "button_color": ["#CBD5E1", "#475569"],
        "button_hover_color": ["#94A3B8", "#64748B"],
    },
    "CTkSegmentedButton": {
        "corner_radius": 8,
        "border_width": 1,
        "fg_color": [LIGHT["card"], DARK["card"]],
        "selected_color": [LIGHT["accent"], DARK["accent"]],
        "selected_hover_color": [LIGHT["accent_hover"], DARK["accent_hover"]],
        "unselected_color": [LIGHT["card"], DARK["card"]],
        "unselected_hover_color": ["#EEF2F7", "#334155"],
        "text_color": [LIGHT["text"], DARK["text"]],
        "text_color_disabled": ["#94A3B8", "#64748B"],
    },
    "DropdownMenu": {
        "fg_color": [LIGHT["card"], DARK["card"]],
        "hover_color": ["#EFF6FF", "#334155"],
        "text_color": [LIGHT["text"], DARK["text"]],
    },
}


_FONT_BLACKLIST = {"SimSun", "宋体", "FangSong", "仿宋", "KaiTi", "楷体", "Times New Roman"}
_FONT_PREFERENCE = [
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "PingFang SC",
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "Segoe UI",
    "Inter",
    "Roboto",
    "Arial",
]


def ensure_modern_theme_file() -> str:
    path = Path(tempfile.gettempdir()) / "translator_pro_modern_theme.json"
    path.write_text(json.dumps(THEME, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def install_modern_theme() -> None:
    ctk.set_default_color_theme(ensure_modern_theme_file())


def detect_font_family(root=None) -> str:
    # Prefer installed system fonts and explicitly avoid serif/CJK legacy fonts.
    try:
        families = set(tkfont.families(root=root))
    except Exception:
        families = set()
    for name in _FONT_PREFERENCE:
        if name in families and name not in _FONT_BLACKLIST:
            return name
    system = platform.system().lower()
    if "windows" in system:
        if Path(r"C:\Windows\Fonts\msyh.ttc").exists():
            return "Microsoft YaHei UI"
        return "Segoe UI"
    if "darwin" in system:
        return "PingFang SC"
    return "Source Han Sans SC"


def font(root=None, size: int = 13, weight: Optional[str] = None) -> ctk.CTkFont:
    # CTkFont 在 weight=None 时会回退读取 ThemeManager.theme["CTkFont"]["weight"]。
    # 为避免自定义主题缺省键或旧配置缓存导致启动失败，这里始终传入合法字重。
    safe_weight = weight if weight in ("normal", "bold") else "normal"
    return ctk.CTkFont(family=detect_font_family(root), size=size, weight=safe_weight)


def apply_textbox_typography(textbox, size: int = 14) -> None:
    textbox.configure(font=font(textbox, size=size))
    inner = getattr(textbox, "_textbox", None)
    if inner is not None:
        try:
            inner.configure(spacing1=3, spacing2=2, spacing3=8, insertwidth=2)
        except Exception:
            pass


def bind_focus_glow(widget, normal: Tuple[str, str] | None = None, focus: Tuple[str, str] | None = None) -> None:
    normal = normal or pair("border")
    focus = focus or pair("accent")
    try:
        widget.configure(border_color=normal)
    except Exception:
        return
    widget.bind("<FocusIn>", lambda _e: widget.configure(border_color=focus, border_width=2), add="+")
    widget.bind("<FocusOut>", lambda _e: widget.configure(border_color=normal, border_width=1), add="+")
    inner = getattr(widget, "_textbox", None)
    if inner is not None:
        inner.bind("<FocusIn>", lambda _e: widget.configure(border_color=focus, border_width=2), add="+")
        inner.bind("<FocusOut>", lambda _e: widget.configure(border_color=normal, border_width=1), add="+")


def install_textbox_placeholder(textbox, placeholder: str) -> None:
    textbox._tp_placeholder = placeholder
    textbox._tp_placeholder_active = False

    def set_placeholder() -> None:
        textbox._tp_placeholder_active = True
        textbox.configure(text_color=pair("placeholder"))
        textbox.delete("1.0", "end")
        textbox.insert("1.0", placeholder)

    def clear_placeholder() -> None:
        if getattr(textbox, "_tp_placeholder_active", False):
            textbox._tp_placeholder_active = False
            textbox.configure(text_color=pair("text"))
            textbox.delete("1.0", "end")

    def on_focus_out(_e=None) -> None:
        if not textbox.get("1.0", "end").strip():
            set_placeholder()

    textbox.bind("<FocusIn>", lambda _e: clear_placeholder(), add="+")
    textbox.bind("<FocusOut>", on_focus_out, add="+")
    inner = getattr(textbox, "_textbox", None)
    if inner is not None:
        inner.bind("<FocusIn>", lambda _e: clear_placeholder(), add="+")
        inner.bind("<FocusOut>", on_focus_out, add="+")
    set_placeholder()


def textbox_get_clean(textbox) -> str:
    if getattr(textbox, "_tp_placeholder_active", False):
        return ""
    return textbox.get("1.0", "end").strip()


def textbox_clear(textbox, placeholder: bool = False) -> None:
    active = getattr(textbox, "_tp_placeholder_active", False)
    if active:
        textbox.configure(text_color=pair("text"))
        textbox._tp_placeholder_active = False
    textbox.delete("1.0", "end")
    if placeholder and hasattr(textbox, "_tp_placeholder"):
        # Force focus-out style placeholder without requiring focus changes.
        textbox._tp_placeholder_active = True
        textbox.configure(text_color=pair("placeholder"))
        textbox.insert("1.0", textbox._tp_placeholder)


def textbox_insert_user_text(textbox, text: str, index: str = "end") -> None:
    if getattr(textbox, "_tp_placeholder_active", False):
        textbox._tp_placeholder_active = False
        textbox.configure(text_color=pair("text"))
        textbox.delete("1.0", "end")
    textbox.insert(index, text)


def button_colors(kind: str = "primary") -> dict:
    if kind == "primary":
        return {
            "fg_color": pair("accent"),
            "hover_color": pair("accent_hover"),
            "text_color": ("#FFFFFF", "#0F172A"),
            "border_width": 0,
        }
    if kind == "danger":
        return {
            "fg_color": (LIGHT["danger"], DARK["danger"]),
            "hover_color": ("#B91C1C", "#FCA5A5"),
            "text_color": ("#FFFFFF", "#0F172A"),
            "border_width": 0,
        }
    return {
        "fg_color": "transparent",
        "hover_color": ("#EEF2F7", "#334155"),
        "border_color": pair("border"),
        "border_width": 1,
        "text_color": pair("text"),
    }


def modern_button(parent, text: str, command=None, kind: str = "secondary", **kwargs):
    opts = button_colors(kind)
    opts.update(kwargs)
    if "font" not in opts:
        opts["font"] = font(parent, 13, "bold" if kind == "primary" else "normal")
    btn = ctk.CTkButton(parent, text=text, command=command, corner_radius=8, **opts)
    btn.bind("<Enter>", lambda _e: btn.configure(cursor="hand2"), add="+")
    return btn


def modern_option_menu(parent, values, command=None, width: int | None = None, **kwargs):
    """统一下拉框样式。

    CTkOptionMenu 不接受 width=None，因此这里始终提供安全宽度。
    右侧箭头按钮区域使用与输入框一致的底色，避免出现突兀的蓝色块。
    """
    opts = {
        "values": values,
        "command": command,
        "width": 230 if width is None else width,
        "height": 34,
        "corner_radius": 8,
        "fg_color": pair("card"),
        "button_color": pair("card"),
        "button_hover_color": ("#EEF2F7", "#334155"),
        "text_color": pair("text"),
        "dropdown_fg_color": pair("card"),
        "dropdown_hover_color": ("#EFF6FF", "#334155"),
        "dropdown_text_color": pair("text"),
        "font": font(parent, 13),
        "dropdown_font": font(parent, 13),
        "dynamic_resizing": False,
    }
    opts.update(kwargs)
    return ctk.CTkOptionMenu(parent, **opts)


def label(
    parent,
    text: str,
    kind: str = "body",
    size: int | None = None,
    weight: Optional[str] = None,
    color=None,
    secondary: bool = False,
    **kwargs,
):
    """统一标签样式。

    kind 和 secondary 是本项目自定义样式参数，不能继续传给 CTkLabel。
    secondary=True 兼容旧写法，等价于 kind="muted"。
    """
    if secondary:
        kind = "muted"

    if kind == "title":
        final_size = size or 18
        final_weight = weight or "bold"
        final_color = color or pair("text")
    elif kind == "caption":
        final_size = size or 13
        final_weight = weight or "bold"
        final_color = color or pair("text")
    elif kind == "muted":
        final_size = size or 12
        final_weight = weight or "normal"
        final_color = color or pair("text_secondary")
    elif kind == "status":
        final_size = size or 12
        final_weight = weight or "normal"
        final_color = color or pair("text_secondary")
    else:
        final_size = size or 13
        final_weight = weight or "normal"
        final_color = color or pair("text")

    return ctk.CTkLabel(
        parent,
        text=text,
        font=font(parent, final_size, final_weight),
        text_color=final_color,
        **kwargs,
    )


def card(parent, **kwargs):
    opts = {
        "corner_radius": 12,
        "fg_color": pair("card"),
        "border_color": pair("border"),
        "border_width": 1,
    }
    opts.update(kwargs)
    return ctk.CTkFrame(parent, **opts)


def soft_frame(parent, **kwargs):
    opts = {"corner_radius": 12, "fg_color": pair("card_soft"), "border_color": pair("border"), "border_width": 1}
    opts.update(kwargs)
    return ctk.CTkFrame(parent, **opts)


def shadow_card(parent, row: int, column: int, padx=0, pady=0, sticky="nsew", **kwargs):
    shadow = ctk.CTkFrame(parent, corner_radius=14, fg_color=pair("shadow"), border_width=0)
    shadow.grid(row=row, column=column, padx=padx, pady=pady, sticky=sticky)
    shadow.grid_propagate(False)
    frame = card(parent, **kwargs)
    frame.grid(row=row, column=column, padx=padx, pady=pady, sticky=sticky)
    return frame


def setup_ttk_style(root=None) -> None:
    family = detect_font_family(root)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(
        "Treeview",
        font=(family, 10),
        rowheight=30,
        background=LIGHT["card"],
        foreground=LIGHT["text"],
        fieldbackground=LIGHT["card"],
        bordercolor=LIGHT["border"],
        lightcolor=LIGHT["border"],
        darkcolor=LIGHT["border"],
    )
    style.configure(
        "Treeview.Heading",
        font=(family, 10, "bold"),
        background="#EEF2F7",
        foreground=LIGHT["text"],
        relief="flat",
    )
    style.map("Treeview", background=[("selected", LIGHT["accent_soft"])] , foreground=[("selected", LIGHT["text"])])


def apply_recursive_fonts(widget, root=None) -> None:
    family = detect_font_family(root or widget)
    for child in widget.winfo_children():
        try:
            cls = child.__class__.__name__
            if cls in {"CTkLabel", "CTkButton", "CTkEntry", "CTkOptionMenu", "CTkCheckBox", "CTkSwitch"}:
                current_size = 13
                if cls == "CTkLabel":
                    current_size = 13
                child.configure(font=ctk.CTkFont(family=family, size=current_size))
            elif cls == "CTkTextbox":
                child.configure(font=ctk.CTkFont(family=family, size=14))
        except Exception:
            pass
        apply_recursive_fonts(child, root)
