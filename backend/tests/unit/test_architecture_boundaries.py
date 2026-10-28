"""Kiểm thử ranh giới module (SADD §2.2.1, T-001 §7).

Gọi CLI `lint-imports` qua subprocess (giống hệt `make lint-arch` và
CI) thay vì API nội bộ của import-linter — API nội bộ (`use_cases.*`)
cần trạng thái mà chỉ CLI mới khởi tạo nên không ổn định để gọi trực
tiếp. Mục đích: chứng minh contract thật sự CHẶN vi phạm, không chỉ
chạy xanh vì không có gì để kiểm tra.
"""

import pathlib
import subprocess
import sys

_BACKEND_ROOT = pathlib.Path(__file__).parents[2]


def _run_lint_imports() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from importlinter.cli import lint_imports_command; lint_imports_command()",
            "--no-logo",
        ],
        cwd=_BACKEND_ROOT,
        capture_output=True,
        text=True,
    )


def test_all_contracts_pass_on_current_codebase() -> None:
    result = _run_lint_imports()
    assert result.returncode == 0, result.stdout + result.stderr


def test_forbidden_contract_catches_a_real_violation() -> None:
    """`app.modules.*` không được import `app.adapters`/`app.api`. Tạo
    một vi phạm tạm thời, xác nhận import-linter báo lỗi (exit != 0),
    rồi dọn sạch — kể cả khi assertion thất bại.
    """
    violation = _BACKEND_ROOT / "app" / "modules" / "documents" / "_tmp_violation.py"
    violation.write_text("import app.adapters\n", encoding="utf-8")
    try:
        result = _run_lint_imports()
        assert result.returncode != 0
        assert "app.modules.documents is not allowed to import app.adapters" in result.stdout
    finally:
        violation.unlink(missing_ok=True)
