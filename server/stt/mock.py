"""고정 단어열을 돌려주는 STT (테스트·개발용, 01-plan 3.2). 입력 음성은 읽지 않는다."""
from stt.base import SttHints, SttResult, Word

# 합성 문장. 화자는 주지 않는다(화자분리·병합 단계가 붙인다). 중간에 화자 전환용 침묵을 둔다.
MOCK_WORDS = (
    Word(0, 600, "안녕하세요."),
    Word(700, 1300, "오늘은"),
    Word(1350, 1900, "검색"),
    Word(1950, 2600, "개편을"),
    Word(2650, 3400, "논의합니다."),
    Word(4200, 4700, "네,"),
    Word(4750, 5400, "일정부터"),
    Word(5450, 6100, "정하죠."),
)


class MockSttProvider:
    name = "mock"

    def transcribe(self, wav_path: str, *, language: str, hints: SttHints) -> SttResult:
        return SttResult(engine=self.name, words=list(MOCK_WORDS))

    def unload(self) -> None:
        pass
