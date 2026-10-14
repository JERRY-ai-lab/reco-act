"""합성 회의. 실제 회의 녹음·전사가 아니다.

외부 LLM(OpenRouter)에는 이 데이터만 보낸다(00-decisions 3장).
"""
from models.meeting import Meeting, TranscriptSegmentResponse

PARTICIPANTS = ["화자1", "화자2", "화자3"]

# (speaker_index, start ms, end ms, text)
_SEGMENTS = [
    (0, 0, 7000, "오늘은 사내 문서 검색 시스템 개편 일정과 역할을 정하려고 합니다."),
    (1, 7000, 15000, "현재 검색 서버는 키워드 일치만 지원해서 오타가 있으면 결과가 안 나옵니다."),
    (2, 15000, 23000, "형태소 분석기를 바꾸고 색인을 다시 만들면 2주 정도 걸릴 것 같습니다."),
    (0, 23000, 30000, "색인 재구축은 업무 시간 이후에 진행해야 서비스에 영향이 없겠네요."),
    (1, 30000, 38000, "네, 야간 배치로 돌리고 진행 상황은 매일 아침 공유하겠습니다."),
    (2, 38000, 47000, "검색 화면에는 필터 기능을 추가해 달라는 요청이 많았습니다. 부서와 작성일 기준입니다."),
    (0, 47000, 55000, "필터는 2차 범위로 미루고, 이번에는 검색 정확도 개선에 집중하겠습니다."),
    (1, 55000, 62000, "테스트용 문서 100건은 제가 다음 주 월요일까지 준비하겠습니다."),
    (2, 62000, 70000, "저는 형태소 분석기 후보 두 가지를 비교해서 수요일에 결과를 공유하겠습니다."),
    (0, 70000, 76000, "좋습니다. 다음 회의는 다음 주 목요일 오후 2시에 하겠습니다."),
]


def make_synthetic_meeting(meeting_id: str = "m_synthetic") -> Meeting:
    return Meeting(
        id=meeting_id,
        title="문서 검색 개편 회의(합성)",
        created_at="2026-10-14 10:00:00",
        participants=PARTICIPANTS,
        transcript=[
            TranscriptSegmentResponse(
                speaker_index=speaker, speaker_name=PARTICIPANTS[speaker], text=text, start=start, end=end
            )
            for speaker, start, end, text in _SEGMENTS
        ],
        transcription_status="done",
    )
