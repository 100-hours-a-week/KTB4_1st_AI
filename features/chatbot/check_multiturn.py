import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from core.config import settings
from features.chatbot.exceptions import ChatbotException
from features.chatbot.prompts import (
    NOT_FOUND_ANSWER,
    OUT_OF_SCOPE_ANSWER,
    SCREEN_LABELS,
)
from features.chatbot.schemas import ChatbotRequest, ChatbotResponse, ChatMessage
from features.chatbot.service import ask_chatbot


class Turn(NamedTuple):
    message: str
    kind: str  # policy / navigation / out_of_scope / not_found
    screen: str | None = None  # None이면 화면은 검사하지 않음
    answer_has: tuple[str, ...] = ()  # 답변에 모두 들어 있어야 하는 말
    query_has: tuple[str, ...] = ()  # 검색용 질문에 모두 들어 있어야 하는 말


# (시나리오 이름, 턴 목록) - 앞 턴의 실제 답변이 뒤 턴의 이전 대화로 들어감
SCENARIOS = [
    (
        "그룹 질문 뒤 '설명은요?'",
        [
            Turn("그룹 이름은 몇 글자까지 쓸 수 있어요?", "policy", answer_has=("30",)),
            Turn("그럼 설명은요?", "policy", answer_has=("300",), query_has=("설명",)),
        ],
    ),
    (
        "탈퇴 질문 뒤 '그건 어디서 해요?'",
        [
            Turn("탈퇴하면 데이터는 언제 삭제돼요?", "policy", answer_has=("7일",)),
            Turn(
                "그건 어디서 해요?",
                "policy",
                answer_has=("마이페이지",),
                query_has=("탈퇴",),
            ),
        ],
    ),
    (
        "문의 질문 뒤 '거기로 가줘'",
        [
            Turn("1:1 문의 답변은 얼마나 걸려요?", "policy", answer_has=("48시간",)),
            Turn("거기로 가줘", "navigation", screen="INQUIRY"),
        ],
    ),
    (
        "화면 이동 뒤 정책 질문",
        [
            Turn("물건 등록하러 갈래", "navigation", screen="ITEM_ADD"),
            Turn("사진은 몇 장까지 올릴 수 있어요?", "policy", answer_has=("3장",)),
            Turn("그럼 제목은요?", "policy", answer_has=("100",), query_has=("제목",)),
        ],
    ),
    (
        "잡담이 끼어든 뒤 정책 질문",
        [
            Turn("안녕", "out_of_scope"),
            Turn(
                "교환을 요청하면 채팅방은 어떻게 돼요?",
                "policy",
                answer_has=("채팅방",),
            ),
            Turn("오늘 날씨 어때?", "out_of_scope"),
            Turn(
                "그럼 교환 요청을 수정할 수도 있어요?",
                "policy",
                answer_has=("수정",),
                query_has=("교환",),
            ),
        ],
    ),
    (
        "v3 전용 기능 후속 질문 (답변은 직접 확인)",
        [
            Turn("신고하면 어떤 제재를 받아요?", "policy"),
            Turn("그럼 지금 신고할 수 있어요?", "policy"),
        ],
    ),
]


class QueryCapture(logging.Handler):
    """service.py의 'chatbot intent=... search_query=...' 로그에서 search_query를 꺼냄"""

    def __init__(self) -> None:
        super().__init__()
        self.search_query: str | None = None

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno == logging.INFO and isinstance(record.args, tuple):
            self.search_query = str(record.args[-1])


capture = QueryCapture()
warning_handler = logging.StreamHandler()
warning_handler.setLevel(logging.WARNING)
service_logger = logging.getLogger("features.chatbot.service")
service_logger.setLevel(logging.INFO)
service_logger.addHandler(capture)
service_logger.addHandler(warning_handler)


# 응답 모양으로 챗봇이 어떤 경로를 탔는지 알아냄
def kind_of(response: ChatbotResponse) -> str:
    if response.answer == OUT_OF_SCOPE_ANSWER:
        return "out_of_scope"
    if response.answer == NOT_FOUND_ANSWER:
        return "not_found"
    if response.action is not None:
        label = SCREEN_LABELS[response.action.screen.value]
        if response.answer == f"{label} 화면으로 이동할 수 있어요.":
            return "navigation"
    return "policy"


def find_problems(turn: Turn, response: ChatbotResponse, kind: str) -> list[str]:
    problems = []
    if kind != turn.kind:
        problems.append(f"의도가 {kind}")
    screen = response.action.screen.value if response.action else None
    if turn.screen is not None and screen != turn.screen:
        problems.append(f"화면이 {screen}")
    for word in turn.answer_has:
        if word not in response.answer:
            problems.append(f"답변에 '{word}' 없음")
    for word in turn.query_has:
        if word not in (capture.search_query or ""):
            problems.append(f"검색 질문에 '{word}' 없음")
    return problems


# 시나리오 하나를 실행하고 턴별 결과를 돌려줌
async def run_scenario(name: str, turns: list[Turn]) -> list[dict]:
    print(f"\n=== {name}")
    history: list[ChatMessage] = []
    rows = []
    for number, turn in enumerate(turns, start=1):
        capture.search_query = None
        row = {
            "scenario": name,
            "turn": number,
            "message": turn.message,
            "expected_kind": turn.kind,
            "expected_screen": turn.screen,
        }
        request = ChatbotRequest(message=turn.message, history=history)
        try:
            response = await ask_chatbot(request)
        except ChatbotException as error:
            print(
                f"X [{number}] {turn.message} | 호출 실패 {error.error} ({error.stage})"
            )
            row.update(ok=False, error=error.error, stage=error.stage)
            rows.append(row)
            break

        kind = kind_of(response)
        screen = response.action.screen.value if response.action else None
        problems = find_problems(turn, response, kind)
        search_query = capture.search_query if kind in ("policy", "not_found") else None
        mark = "O" if not problems else "X"
        print(
            f"{mark} [{number}] {turn.message} | "
            f"기대 {turn.kind} {turn.screen} | 결과 {kind} {screen}"
        )
        if search_query:
            print(f"    검색 질문: {search_query}")
        print(f"    응답: {response.answer}")
        if problems:
            print(f"    문제: {', '.join(problems)}")

        row.update(
            kind=kind,
            screen=screen,
            search_query=search_query,
            answer=response.answer,
            problems=problems,
            ok=not problems,
        )
        rows.append(row)
        history.append(ChatMessage(role="user", content=turn.message))
        history.append(ChatMessage(role="assistant", content=response.answer))
    return rows


async def run_all() -> list[dict]:
    rows = []
    for name, turns in SCENARIOS:
        rows += await run_scenario(name, turns)
    return rows


def summarize(rows: list[dict]) -> dict:
    passed_scenarios = 0
    for name, turns in SCENARIOS:
        scenario_rows = [row for row in rows if row["scenario"] == name]
        # 중간에 호출이 실패해 턴이 모자라면 통과로 치지 않음
        if len(scenario_rows) == len(turns) and all(r["ok"] for r in scenario_rows):
            passed_scenarios += 1
    return {
        "scenarios_passed": passed_scenarios,
        "scenarios_total": len(SCENARIOS),
        "turns_passed": sum(row["ok"] for row in rows),
        "turns_total": sum(len(turns) for _, turns in SCENARIOS),
    }


def main() -> None:
    # python -m features.chatbot.check_multiturn run2 처럼 번호를 줄 수 있음
    label = sys.argv[1] if len(sys.argv) > 1 else "run1"
    rows = asyncio.run(run_all())
    summary = summarize(rows)
    print(
        f"\n시나리오 통과: {summary['scenarios_passed']}/{summary['scenarios_total']}"
    )
    print(f"턴 통과: {summary['turns_passed']}/{summary['turns_total']}")

    result = {
        "meta": {
            "label": label,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "model_sonnet": settings.claude_model_sonnet,
            "model_haiku": settings.claude_model_haiku,
            "top_k": settings.chatbot_top_k,
            "max_distance": settings.chatbot_max_distance,
        },
        "summary": summary,
        "rows": rows,
    }
    output = Path(f"eval_result_multiturn_{label}.json")
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"저장: {output}")


if __name__ == "__main__":
    main()
