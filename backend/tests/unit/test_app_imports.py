"""Kiểm thử khói (smoke test) — xác nhận package `app` import được.

Giữ CI xanh ở T-001 trước khi có test nghiệp vụ thật (từ T-101 trở đi).
"""

import app


def test_app_package_importable() -> None:
    assert app is not None
