import os, sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

import logging

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
inf = 9223372036854775807

load_dotenv()

# ==================== 프로파일 ====================
APP_PROFILES = ("public", "airgap")


def parse_app_profile(value: Optional[str]) -> str:
    """APP_PROFILE 값을 검증한다. 미설정이면 public(현재 운영 동작).

    그 외 값(빈 문자열, 대소문자·공백이 다른 값 포함)은 예외를 내서 기동을 멈춘다.
    오타나 빈 값 때문에 airgap 서버가 조용히 public(외부 API 호출)으로 뜨는 것을 막는다.
    """
    if value is None:
        return "public"
    if value not in APP_PROFILES:
        raise ValueError(f"Invalid APP_PROFILE={value!r}. Use one of: {', '.join(APP_PROFILES)}")
    return value


APP_PROFILE = parse_app_profile(os.getenv("APP_PROFILE"))


def parse_bool_env(name: str, value: Optional[str], default: bool) -> bool:
    """true/false 형식 env를 읽는다. 미설정이면 default, 알 수 없는 값이면 예외로 기동을 멈춘다."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in ("true", "1"):
        return True
    if normalized in ("false", "0"):
        return False
    raise ValueError(f"Invalid {name}={value!r}. Use true or false")


ENVIRONMENT = os.getenv("ENVIRONMENT")  # 'local' or 'prod'

if ENVIRONMENT == "prod":
    # Docker 환경에서는 absolute path
    RECORDS_DIR = Path("/app/records")
else:
    # 로컬 환경에서는 프로젝트 상대경로
    RECORDS_DIR = Path(__file__).parent.parent / "records"

RECORDS_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"[CONFIG] App profile: {APP_PROFILE}")
logger.info(f"[CONFIG] Environment: {ENVIRONMENT}")
logger.info(f"[CONFIG] Records directory: {RECORDS_DIR}")

# ==================== 메일(SMTP) ====================
# 회원가입 인증코드, 비밀번호 재설정, 회의록 메일이 모두 이 설정을 쓴다(00-decisions 2.7).
# public 기본값은 현행 Gmail(465, SSL)과 같다. airgap은 설치할 때 그 망의 사내 메일 서버를 지정한다.
SMTP_SECURITY_MODES = ("ssl", "starttls", "none")
SMTP_DEFAULT_PORTS = {"ssl": 465, "starttls": 587, "none": 25}


def parse_smtp_security(value: Optional[str]) -> str:
    """SMTP_SECURITY 값을 검증한다. 미설정이면 ssl(현행 Gmail 방식)."""
    if value is None:
        return "ssl"
    if value not in SMTP_SECURITY_MODES:
        raise ValueError(f"Invalid SMTP_SECURITY={value!r}. Use one of: {', '.join(SMTP_SECURITY_MODES)}")
    return value


# airgap에서 미설정이면 None으로 두고 발송을 실패시킨다(외부 Gmail로 나가지 않게).
SMTP_HOST = os.getenv("SMTP_HOST") or ("smtp.gmail.com" if APP_PROFILE == "public" else None)
SMTP_SECURITY = parse_smtp_security(os.getenv("SMTP_SECURITY"))
SMTP_PORT = int(os.getenv("SMTP_PORT") or SMTP_DEFAULT_PORTS[SMTP_SECURITY])
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")  # 비어 있으면 로그인을 건너뛴다(인증 없는 사내 릴레이)

# 가입 이메일 검증 때 DNS로 도메인의 메일 수신 가능 여부를 조회할지. airgap은 외부 DNS 조회를 끈다(01-plan R2).
EMAIL_DELIVERABILITY_CHECK = parse_bool_env(
    "EMAIL_DELIVERABILITY_CHECK", os.getenv("EMAIL_DELIVERABILITY_CHECK"), default=APP_PROFILE == "public"
)

# ==================== Azure OpenAI 설정 ====================
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZURE_OPENAI_EMBEDDING = os.getenv("AZURE_OPENAI_EMBEDDING")


def get_llm(temperature: float = 0.3):
    """Azure OpenAI LLM 인스턴스를 반환합니다."""
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=temperature,
        # streaming=True
    )


def get_embeddings():
    return AzureOpenAIEmbeddings(
        model=AZURE_OPENAI_EMBEDDING,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )