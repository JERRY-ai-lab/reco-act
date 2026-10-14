"""STT 프로바이더 인터페이스 (01-plan 3.2).

엔진마다 결과의 모양이 다르다.
- 화자까지 나눠 주는 엔진(clova): segments와 speaker_names를 채운다. 화자분리 단계를 건너뛴다.
- 단어 타임스탬프만 주는 엔진(faster_whisper, qwen3_asr, mock): words만 채운다.
  화자분리와 병합(01-plan 3.3)이 segments를 만든다.
"""
from dataclasses import dataclass, field
from typing import Protocol

from models.meeting import TranscriptSegment


@dataclass(frozen=True)
class Word:
    start_ms: int
    end_ms: int
    text: str
    prob: float | None = None


@dataclass
class SttHints:
    """엔진 힌트. 회의 도메인의 키워드 목록(domain_keywords)이다. 엔진별 변환은 어댑터가 맡는다."""
    keywords: list[str] = field(default_factory=list)


@dataclass
class SttResult:
    engine: str
    engine_version: str = ""
    words: list[Word] = field(default_factory=list)  # 화자 없는 단어 타임스탬프
    segments: list[TranscriptSegment] | None = None  # 엔진이 화자까지 준 경우
    speaker_names: list[str] | None = None  # segments의 speaker_index로 인덱싱한다
    raw: dict = field(default_factory=dict)  # 원문 보존용(stt_results, 01-plan 3.4)


class SttProvider(Protocol):
    name: str

    def transcribe(self, wav_path: str, *, language: str, hints: SttHints) -> SttResult:
        """language는 현행 Clova 형식(ko-KR)으로 받는다. 엔진별 언어 코드 변환은 어댑터가 맡는다."""
        ...

    def unload(self) -> None:
        """모델이 잡은 메모리(GPU 포함)를 돌려준다(exclusive 모드, 01-plan 3.6). 모델이 없으면 아무것도 하지 않는다."""
        ...
