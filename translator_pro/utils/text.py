from __future__ import annotations

import re
from typing import Iterable, List


def count_chars(text: str) -> int:
    return len(text or "")


def estimate_tokens(text: str) -> int:
    # Practical approximation for mixed Chinese/English documents.
    if not text:
        return 0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    non_cjk = len(text) - cjk
    return int(cjk * 1.2 + non_cjk / 4)


def split_text_into_chunks(text: str, max_chars: int = 1800) -> List[str]:
    text = text.replace("\r\n", "\n")
    parts = re.split(r"(\n\s*\n)", text)
    chunks: List[str] = []
    buf = ""
    for part in parts:
        if len(buf) + len(part) <= max_chars:
            buf += part
            continue
        if buf.strip():
            chunks.append(buf.strip())
            buf = ""
        if len(part) <= max_chars:
            buf = part
        else:
            # Fallback split by sentence/length.
            sentences = re.split(r"(?<=[。！？.!?])", part)
            for sent in sentences:
                if len(buf) + len(sent) <= max_chars:
                    buf += sent
                else:
                    if buf.strip():
                        chunks.append(buf.strip())
                    buf = sent
            if len(buf) > max_chars:
                for i in range(0, len(buf), max_chars):
                    chunks.append(buf[i:i + max_chars].strip())
                buf = ""
    if buf.strip():
        chunks.append(buf.strip())
    return [x for x in chunks if x]


def safe_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    return name.strip() or "translated"
