"""Chỗ giữ cho test tích hợp (CSDL, Redis qua Testcontainers).

Test thật đầu tiên: T-104 (RLS cô lập owner_id) và T-108 (POST /documents).
"""

import pytest


@pytest.mark.skip(reason="Chưa có test tích hợp thật — xem T-104, T-108")
def test_placeholder() -> None:
    pass
