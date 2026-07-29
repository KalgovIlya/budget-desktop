from __future__ import annotations

from src.domain.errors import ValidationError
from src.i18n import t


def canonical_key(raw: str) -> str:
    folded = raw.strip().casefold().replace("ё", "е")
    key = "".join(ch for ch in folded if ch.isalnum())
    if not key:
        raise ValidationError(t("merchant.err.empty_normalized"))
    return key


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def suggest_keys(
    query_key: str,
    candidates: list[tuple[str, str]],
    *,
    max_distance: int = 2,
    limit: int = 8,
) -> list[tuple[str, str]]:
    """candidates: list of (canonical_key, display_name). Returns matches for suggest."""
    if not query_key:
        return []
    prefix: list[tuple[str, str]] = []
    fuzzy: list[tuple[int, str, str]] = []
    for key, display in candidates:
        if query_key in key or query_key in display.casefold():
            prefix.append((key, display))
            continue
        if len(query_key) <= 2:
            continue
        dist = levenshtein(query_key, key)
        threshold = 1 if len(query_key) <= 4 else max_distance
        if dist <= threshold:
            fuzzy.append((dist, key, display))
    fuzzy.sort(key=lambda x: (x[0], x[1]))
    seen = {k for k, _ in prefix}
    out = list(prefix)
    for _, key, display in fuzzy:
        if key not in seen:
            out.append((key, display))
            seen.add(key)
        if len(out) >= limit:
            break
    return out[:limit]
