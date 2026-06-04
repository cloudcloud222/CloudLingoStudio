from __future__ import annotations

from typing import Dict, Iterable, List


def glossary_to_prompt(glossary: List[Dict[str, str]], max_items: int = 80) -> str:
    terms = []
    for item in glossary[:max_items]:
        src = (item.get("source") or "").strip()
        tgt = (item.get("target") or "").strip()
        note = (item.get("note") or "").strip()
        if src and tgt:
            if note:
                terms.append(f"- {src} => {tgt}（{note}）")
            else:
                terms.append(f"- {src} => {tgt}")
    if not terms:
        return ""
    return "\n\n翻译时必须优先遵循以下术语库，保持译名一致：\n" + "\n".join(terms)
