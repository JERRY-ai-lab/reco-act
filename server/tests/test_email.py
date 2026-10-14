"""메일 서버 설정과 이메일 검증 옵션 (01-plan 3.9, R2).

실제 SMTP 서버나 DNS에는 접속하지 않는다. smtplib과 email-validator의 DNS 조회 함수를 대역으로 바꾼다.
"""

import pytest

from services import auth_service
from utils import config
from utils import email as mail
from utils.config import parse_bool_env, parse_smtp_security


# ==================== 설정 ====================

def test_public_defaults_match_current_gmail():
    assert (config.SMTP_HOST, config.SMTP_PORT, config.SMTP_SECURITY) == ("smtp.gmail.com", 465, "ssl")
    assert (mail.SMTP_HOST, mail.SMTP_PORT, mail.SMTP_SECURITY) == ("smtp.gmail.com", 465, "ssl")
    assert config.EMAIL_DELIVERABILITY_CHECK is True


def test_airgap_defaults(reload_config):
    cfg = reload_config(APP_PROFILE="airgap")
    assert cfg.SMTP_HOST is None  # 설치할 때 사내 메일 서버를 지정해야 한다
    assert cfg.EMAIL_DELIVERABILITY_CHECK is False


def test_airgap_internal_mail_server(reload_config):
    cfg = reload_config(APP_PROFILE="airgap", SMTP_HOST="mail.corp.internal", SMTP_SECURITY="starttls")
    assert (cfg.SMTP_HOST, cfg.SMTP_PORT, cfg.SMTP_SECURITY) == ("mail.corp.internal", 587, "starttls")


@pytest.mark.parametrize("security, port", [("ssl", 465), ("starttls", 587), ("none", 25)])
def test_port_follows_security_when_unset(reload_config, security, port):
    assert reload_config(SMTP_SECURITY=security).SMTP_PORT == port


def test_port_override(reload_config):
    assert reload_config(SMTP_SECURITY="none", SMTP_PORT="2525").SMTP_PORT == 2525


def test_deliverability_override(reload_config):
    assert reload_config(EMAIL_DELIVERABILITY_CHECK="false").EMAIL_DELIVERABILITY_CHECK is False


@pytest.mark.parametrize("value", ["", "SSL", "tls", "starttls "])
def test_invalid_smtp_security_is_rejected(value):
    with pytest.raises(ValueError, match="Invalid SMTP_SECURITY"):
        parse_smtp_security(value)


@pytest.mark.parametrize("value, expected", [("true", True), ("TRUE", True), ("1", True),
                                             ("false", False), ("False", False), ("0", False)])
def test_parse_bool_env(value, expected):
    assert parse_bool_env("X", value, default=not expected) is expected


@pytest.mark.parametrize("value", ["", "yes", "off", "2"])
def test_invalid_bool_env_is_rejected(value):
    with pytest.raises(ValueError, match="Invalid X"):
        parse_bool_env("X", value, default=True)


def test_invalid_bool_env_stops_import(reload_config):
    with pytest.raises(ValueError, match="Invalid EMAIL_DELIVERABILITY_CHECK"):
        reload_config(EMAIL_DELIVERABILITY_CHECK="yes")


# ==================== 발송 ====================

class FakeSMTP:
    """smtplib.SMTP / SMTP_SSL 대역. 접속 인자와 호출 순서만 기록한다."""

    def __init__(self, kind, host, port):
        self.kind, self.host, self.port = kind, host, port
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.calls.append("quit")
        return False

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def sendmail(self, sender, recipient, message):
        self.calls.append(("sendmail", sender, recipient))


@pytest.fixture
def smtp(monkeypatch):
    """생성된 FakeSMTP 목록. 발송 계정은 가짜 값으로 둔다."""
    servers = []

    def factory(kind):
        def create(host, port):
            servers.append(FakeSMTP(kind, host, port))
            return servers[-1]
        return create

    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", factory("SMTP_SSL"))
    monkeypatch.setattr(mail.smtplib, "SMTP", factory("SMTP"))
    monkeypatch.setattr(mail, "SENDER_EMAIL", "noreply@example.com")
    monkeypatch.setattr(mail, "SENDER_PASSWORD", "app-password")
    return servers


def send_both():
    assert mail.send_verification_email("user@example.com", "123456") is True
    assert mail.send_summary_email("user@example.com", "주간 회의", b"docx", "notes.docx") is True


def test_public_default_sends_like_before(smtp):
    """기존 코드와 같이 SMTP_SSL(smtp.gmail.com, 465) → login → sendmail."""
    send_both()
    assert [(s.kind, s.host, s.port) for s in smtp] == [("SMTP_SSL", "smtp.gmail.com", 465)] * 2
    for server in smtp:
        assert server.calls == [
            ("login", "noreply@example.com", "app-password"),
            ("sendmail", "noreply@example.com", "user@example.com"),
            "quit",
        ]


def test_starttls(smtp, monkeypatch):
    monkeypatch.setattr(mail, "SMTP_HOST", "mail.corp.internal")
    monkeypatch.setattr(mail, "SMTP_PORT", 587)
    monkeypatch.setattr(mail, "SMTP_SECURITY", "starttls")
    send_both()
    assert [(s.kind, s.host, s.port) for s in smtp] == [("SMTP", "mail.corp.internal", 587)] * 2
    for server in smtp:
        assert server.calls[:2] == ["starttls", ("login", "noreply@example.com", "app-password")]


@pytest.mark.parametrize("password", ["", None])
def test_relay_without_password_skips_login(smtp, monkeypatch, password):
    monkeypatch.setattr(mail, "SMTP_HOST", "relay.corp.internal")
    monkeypatch.setattr(mail, "SMTP_PORT", 25)
    monkeypatch.setattr(mail, "SMTP_SECURITY", "none")
    monkeypatch.setattr(mail, "SENDER_PASSWORD", password)
    send_both()
    for server in smtp:
        assert (server.kind, server.calls) == (
            "SMTP", [("sendmail", "noreply@example.com", "user@example.com"), "quit"]
        )


def test_missing_host_fails_without_connecting(smtp, monkeypatch):
    """airgap에서 SMTP_HOST를 지정하지 않았으면 Gmail로 나가지 않고 실패한다."""
    monkeypatch.setattr(mail, "SMTP_HOST", None)
    assert mail.send_verification_email("user@example.com", "123456") is False
    assert mail.send_summary_email("user@example.com", "주간 회의", b"docx", "notes.docx") is False
    assert smtp == []


# ==================== 이메일 검증 ====================

@pytest.fixture
def dns_lookups(monkeypatch):
    """email-validator의 DNS 조회 함수 대역. 호출된 도메인을 기록한다."""
    import email_validator.deliverability

    domains = []

    def fake_lookup(domain, domain_i18n, timeout=None, dns_resolver=None):
        domains.append(domain)
        return {}

    monkeypatch.setattr(email_validator.deliverability, "validate_email_deliverability", fake_lookup)
    return domains


def test_public_checks_deliverability(dns_lookups):
    auth_service._validate_email_or_raise("user@example.com")
    assert dns_lookups == ["example.com"]


def test_deliverability_check_off_skips_dns(dns_lookups, monkeypatch):
    monkeypatch.setattr(auth_service, "EMAIL_DELIVERABILITY_CHECK", False)
    auth_service._validate_email_or_raise("user@corp.example.com")
    assert dns_lookups == []


def test_syntax_is_still_checked_without_dns(dns_lookups, monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(auth_service, "EMAIL_DELIVERABILITY_CHECK", False)
    with pytest.raises(HTTPException) as exc:
        auth_service._validate_email_or_raise("not-an-email")
    assert exc.value.status_code == 400
