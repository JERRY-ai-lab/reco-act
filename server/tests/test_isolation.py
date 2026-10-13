"""테스트가 실제 .env와 운영 접속 정보를 쓰지 않는지 확인한다."""
import os

from conftest import FAKE_ENV, SECRET_ENV_KEYS


def test_dotenv_is_blocked():
    import main  # noqa: F401  앱 전체 import (모든 모듈의 load_dotenv 호출 포함)

    # 실패해도 값이 출력되지 않도록 키 이름만 비교한다.
    leaked = [key for key in SECRET_ENV_KEYS if key in os.environ]
    assert leaked == []


def test_fake_connection_env():
    import database
    from utils import redis_client

    # 실패 메시지에 비밀번호가 찍히지 않도록 host와 database만 본다.
    assert (database.engine.url.host, database.engine.url.database) == ("127.0.0.1", "test")
    assert redis_client._REDIS_HOST == FAKE_ENV["REDIS_HOST"]
