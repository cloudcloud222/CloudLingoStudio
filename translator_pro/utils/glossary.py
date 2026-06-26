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



def _contains(text: str, term: str) -> bool:
    """Small helper for case-insensitive substring matching.

    It intentionally stays simple: this tool is meant to be a quick manual check,
    not a strict NLP evaluator.
    """
    if not text or not term:
        return False
    return term.casefold() in text.casefold()


def analyze_glossary_hits(source_text: str, result_text: str, glossary: List[Dict[str, str]]) -> Dict[str, object]:
    """Check whether terms that appear in the source text also appear as expected in the result.

    Matching rule:
    - If the source text contains `source`, the expected translation is `target`.
    - If the source text contains `target`, the expected translation is `source`.
    - Terms not appearing in the source text are ignored in the hit-rate denominator.

    This is a lightweight check for human review. It does not try to solve synonyms,
    inflections, spacing differences, or model paraphrases.
    """
    rows: List[Dict[str, object]] = []
    valid_terms = 0
    relevant_terms = 0
    hit_terms = 0

    for item in glossary:
        src = (item.get("source") or "").strip()
        tgt = (item.get("target") or "").strip()
        note = (item.get("note") or "").strip()
        if not src or not tgt:
            continue
        valid_terms += 1

        source_has_src = _contains(source_text, src)
        source_has_tgt = _contains(source_text, tgt)
        if not source_has_src and not source_has_tgt:
            rows.append({
                "source": src,
                "target": tgt,
                "note": note,
                "direction": "未出现",
                "expected": "",
                "hit": None,
                "status": "跳过",
            })
            continue

        relevant_terms += 1
        if source_has_src:
            expected = tgt
            direction = "原术语 → 目标译名"
        else:
            expected = src
            direction = "目标译名 → 原术语"

        hit = _contains(result_text, expected)
        if hit:
            hit_terms += 1
        rows.append({
            "source": src,
            "target": tgt,
            "note": note,
            "direction": direction,
            "expected": expected,
            "hit": hit,
            "status": "命中" if hit else "未命中",
        })

    missing_terms = max(0, relevant_terms - hit_terms)
    hit_rate = (hit_terms / relevant_terms) if relevant_terms else 0.0
    return {
        "valid_terms": valid_terms,
        "relevant_terms": relevant_terms,
        "hit_terms": hit_terms,
        "missing_terms": missing_terms,
        "hit_rate": hit_rate,
        "rows": rows,
    }
