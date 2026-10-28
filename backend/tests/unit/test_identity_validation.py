"""Kiểm thử chặn open-redirect qua `return_to` (T-101 §7)."""

import pytest

from app.modules.identity.validation import is_safe_return_to


@pytest.mark.parametrize("value", ["/", "/documents", "/a/b?x=1", "/a#frag"])
def test_internal_paths_are_safe(value: str) -> None:
    assert is_safe_return_to(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "https://evil.com",
        "http://evil.com/x",
        "//evil.com",
        "//evil.com/path",
        "evil.com",
        "",
        " /documents",
    ],
)
def test_external_or_malformed_values_are_rejected(value: str) -> None:
    assert is_safe_return_to(value) is False
