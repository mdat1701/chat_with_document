"""Kiểm thử logic của smoke_infra.py bằng cách giả lập (mock) các kết
nối mạng — không cần Docker/hạ tầng thật đang chạy.

Mục đích: chứng minh script phân tích đúng phản hồi thật của từng
dịch vụ (PONG của Redis, FOUND của ClamAV, mảng 1024 chiều của TEI...),
tách biệt khỏi việc hạ tầng có đang chạy hay không.
"""

import json
from unittest.mock import MagicMock, patch

import smoke_infra


def test_eicar_string_matches_official_test_string() -> None:
    # Chuỗi thử chuẩn do eicar.org công bố — không phải mã độc thật.
    assert smoke_infra.EICAR.startswith(b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR")


def test_check_redis_ok_when_ping_returns_true() -> None:
    fake_client = MagicMock()
    fake_client.ping.return_value = True
    with patch("redis.from_url", return_value=fake_client):
        result = smoke_infra.check_redis()
    assert result.ok is True
    assert "PONG" in result.detail


def test_check_redis_fails_on_connection_error() -> None:
    with patch("redis.from_url", side_effect=ConnectionError("refused")):
        result = smoke_infra.check_redis()
    assert result.ok is False
    assert "refused" in result.detail


def test_check_clamav_detects_eicar_as_infected() -> None:
    fake_sock = MagicMock()
    # 2 lượt create_connection: (1) PING, (2) INSTREAM.
    fake_sock.recv.side_effect = [b"PONG\0", b"stream: Win.Test.EICAR_HDB-1 FOUND\0"]
    cm = MagicMock()
    cm.__enter__.return_value = fake_sock
    cm.__exit__.return_value = False
    with patch("socket.create_connection", return_value=cm):
        result = smoke_infra.check_clamav()
    assert result.ok is True
    assert "FOUND" in result.detail


def test_check_clamav_reports_failure_when_ping_wrong() -> None:
    fake_sock = MagicMock()
    fake_sock.recv.return_value = b"garbage"
    cm = MagicMock()
    cm.__enter__.return_value = fake_sock
    cm.__exit__.return_value = False
    with patch("socket.create_connection", return_value=cm):
        result = smoke_infra.check_clamav()
    assert result.ok is False


def test_check_tei_returns_true_for_1024_dim_vector() -> None:
    body = json.dumps([[0.1] * 1024]).encode("utf-8")
    fake_resp = MagicMock()
    fake_resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False
    with patch("urllib.request.urlopen", return_value=cm):
        result = smoke_infra.check_tei()
    assert result.ok is True
    assert "1024" in result.detail


def test_check_tei_fails_for_wrong_dimension() -> None:
    body = json.dumps([[0.1] * 768]).encode("utf-8")
    fake_resp = MagicMock()
    fake_resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = fake_resp
    cm.__exit__.return_value = False
    with patch("urllib.request.urlopen", return_value=cm):
        result = smoke_infra.check_tei()
    assert result.ok is False


def test_main_returns_nonzero_when_any_check_fails(capsys) -> None:
    ok = smoke_infra.CheckResult("A", True, "ok")
    bad = smoke_infra.CheckResult("B", False, "lỗi")
    with patch.object(smoke_infra, "CHECKS", [lambda: ok, lambda: bad]):
        code = smoke_infra.main()
    assert code == 1
    out = capsys.readouterr().out
    assert "1/2 dịch vụ sẵn sàng" in out


def test_main_returns_zero_when_all_checks_pass() -> None:
    ok1 = smoke_infra.CheckResult("A", True, "ok")
    ok2 = smoke_infra.CheckResult("B", True, "ok")
    with patch.object(smoke_infra, "CHECKS", [lambda: ok1, lambda: ok2]):
        code = smoke_infra.main()
    assert code == 0
