"""Naver Clova Speech 어댑터 (public). clova_stt.py는 고치지 않고 convert()를 그대로 감싼다."""
import clova_stt
from stt.base import SttHints, SttResult


class ClovaSttProvider:
    name = "clova"

    def transcribe(self, wav_path: str, *, language: str, hints: SttHints) -> SttResult:
        # Clova는 화자분리까지 해서 돌려준다. 키워드는 clova_stt가 boostings로 넘긴다.
        segments, speaker_names = clova_stt.convert(
            file_path=wav_path,
            language=language,
            domain_keywords=hints.keywords or None,
        )
        # convert()는 원 응답을 돌려주지 않아 raw는 비워 둔다. public은 stt_results에 저장하지 않는다.
        return SttResult(engine=self.name, segments=segments, speaker_names=speaker_names)

    def unload(self) -> None:
        pass
