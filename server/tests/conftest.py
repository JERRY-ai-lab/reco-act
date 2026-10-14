"""테스트 공통 설정.

앱 모듈은 import 시점에 load_dotenv()로 server/.env(운영 비밀 포함)를 읽고,
DATABASE_URL·REDIS_PORT·SECRET_KEY가 없으면 import 자체가 실패한다.
그래서 앱 모듈을 import하기 전에 이 파일 최상단에서
1) load_dotenv를 막고 2) 가짜 env를 넣고 3) 결과를 바꿀 수 있는 env를 지운다.
"""
import importlib
import os

import dotenv
import pytest

# 앱 코드는 `from dotenv import load_dotenv`로 이 속성을 가져가므로 여기서 바꾸면 막힌다.
dotenv.load_dotenv = lambda *args, **kwargs: False

# 셸에 실제 값이 있어도 덮어쓴다. create_engine/redis 클라이언트는 연결을 미루므로 접속하지 않는다.
FAKE_ENV = {
    "DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/test",
    "REDIS_HOST": "127.0.0.1",
    "REDIS_PORT": "6379",
    "SECRET_KEY": "test-secret-key",
}

# 테스트 결과를 바꾸거나 실제 외부 서비스를 가리킬 수 있는 env
SECRET_ENV_KEYS = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_EMBEDDING",
    "CLOVA_INVOKE_URL",
    "CLOVA_SECRET_KEY",
    "SENDER_EMAIL",
    "SENDER_PASSWORD",
    "REDIS_PASSWORD",
    "LLM_API_KEY",
]
CLEARED_ENV_KEYS = SECRET_ENV_KEYS + [
    "APP_PROFILE",
    "ENVIRONMENT",  # prod면 RECORDS_DIR이 /app/records가 된다
    "AZURE_OPENAI_API_VERSION",
    "WEB_ORIGIN",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_SECURITY",
    "EMAIL_DELIVERABILITY_CHECK",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_SERVING",
]

os.environ.update(FAKE_ENV)
for _key in CLEARED_ENV_KEYS:
    os.environ.pop(_key, None)

# -m external 테스트용 OpenRouter 키. 앱 코드가 보지 못하게 env에서 빼 둔다.
EXTERNAL_OPENROUTER_API_KEY = os.environ.pop("OPENROUTER_API_KEY", None)


def pytest_addoption(parser):
    parser.addoption(
        "--update-openapi-snapshot",
        action="store_true",
        default=False,
        help="tests/snapshots/openapi_public.json을 현재 앱 스키마로 다시 쓴다(의도한 API 변경일 때만)",
    )


@pytest.fixture
def reload_config(monkeypatch):
    """env를 바꿔 config를 다시 읽는다. 끝나면 env를 되돌리고 원래 상태로 다시 읽는다."""
    from utils import config

    def _reload(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(config)

    yield _reload
    monkeypatch.undo()
    importlib.reload(config)
