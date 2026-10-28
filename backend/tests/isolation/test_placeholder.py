"""Chỗ giữ cho test cô lập dữ liệu 2 người dùng (Pilot Gate G-03).

Test thật: T-504 — kiểm thử cô lập tự động (AC-002.1 – AC-002.3).
"""

import pytest


@pytest.mark.isolation
@pytest.mark.skip(reason="Chưa có test cô lập thật — xem T-504")
def test_placeholder() -> None:
    pass
