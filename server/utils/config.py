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