"""APP_PROFILE 파싱·검증 (01-plan 3.1)."""
import importlib

import pytest

from utils import config
from utils.config import parse_app_profile


def test_unset_is_public():
    assert parse_app_profile(None) == "public"


@pytest.mark.parametrize("value", ["public", "airgap"])
def test_valid_profiles(value):
    assert parse_app_profile(value) == value


@pytest.mark.parametrize("value", ["", "Airgap", "PUBLIC", " airgap", "airgap ", "prod", "local"])
def test_invalid_profiles_are_rejected(value):
    with pytest.raises(ValueError, match="Invalid APP_PROFILE"):
        parse_app_profile(value)


def test_default_profile_in_test_env():
    # conftest가 APP_PROFILE을 지우므로 기본값(public)이어야 한다.
    assert config.APP_PROFILE == "public"


def test_invalid_profile_stops_import(monkeypatch):
    """잘못된 값이면 config import가 실패한다 = uvicorn이 main을 import하지 못해 기동이 멈춘다."""
    monkeypatch.setenv("APP_PROFILE", "staging")
    try:
        with pytest.raises(ValueError, match="Invalid APP_PROFILE"):
            importlib.reload(config)
    finally:
        monkeypatch.delenv("APP_PROFILE")
        importlib.reload(config)  # 다른 테스트를 위해 원래 상태로 되돌린다
    assert config.APP_PROFILE == "public"
