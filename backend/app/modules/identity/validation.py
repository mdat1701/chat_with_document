"""Validate `return_to` chống open-redirect (T-101 §5 bước 3).

Chỉ chấp nhận đường dẫn nội bộ bắt đầu bằng một dấu `/` duy nhất —
chặn URL tuyệt đối (`https://evil.com`) và protocol-relative
(`//evil.com`, trình duyệt hiểu là `https://evil.com`).
"""

import re

_INTERNAL_PATH_RE = re.compile(r"^/(?!/)[^\s]*$")


def is_safe_return_to(return_to: str) -> bool:
    return bool(_INTERNAL_PATH_RE.match(return_to))
