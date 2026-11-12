import argparse
import asyncio
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from core.config import settings
from features.message_refine import service
from features.message_refine.exceptions import MessageRefineException
from features.message_refine.prompts import FIXED_RULES, build_system_prompt

OUTPUT_PATH = "style_compare.json"
STYLE_KEYS = ("CONVERSATION_STYLE", "DESCRIPTION_STYLE", "OPINION_STYLE")

# 서로 많이 다른 취향 조합 (대화 방식, 설명 방식, 의견 표현 방식)
COMBOS = {
    "직설·짧게": ("CONCISE", "BRIEF", "CLEAR"),
    "다정·길게·완곡": ("WARM", "DETAILED", "INDIRECT"),
    "편안·보통·자연": ("COMFORTABLE", "MODERATE", "NATURAL"),
    "간결·자세히·완곡": ("CONCISE", "DETAILED", "INDIRECT"),
    "다정·짧게·분명": ("WARM", "BRIEF", "CLEAR"),
    "취향 없음": None,
}

MESSAGES = [
    "말 같지도 않은 소리하지마",
    "그게 말이 되냐",
    "장난하냐 진짜",
    "그것도 모르냐",
    "아 열받네 빨리 좀 와라",
    "야 3시에 와",
    "내일 5시에 정문으로 나와",
    "오늘 3시쯤 거래, 장소는 4층 엘리베이터 앞",
    "그건 좀 어려울 것 같아",
    "이거 얼마야?",
    "ㅇㅋ",
    "ㅋㅋ",
    "ㅂㅈㄷㄱ",
    "qwerty",
]


def to_answers(combo):
    if combo is None:
        return []
    return [{"question": q, "answer": a} for q, a in zip(STYLE_KEYS, combo)]


# 백엔드가 프론트에 돌려주는 응답 형식
def backend_success(refined):
    return {"data": {"refined_message": refined}, "error": None}


def backend_error():
    return {
        "data": None,
        "error": {
            "code": "AI_MESSAGE_REFINE_FAILED",
            "message": "AI 메시지 다듬기에 실패했습니다.",
            "details": [],
        },
    }


async def refine_once(target, answers, message):
    styles = {item["question"]: item["answer"] for item in answers}
    system_prompt = build_system_prompt(styles)
    try:
        if target == "runpod":
            text = await service._call_refine_server(system_prompt, message)
        else:
            text = await service._call_claude(system_prompt, message)
        refined = service._parse_response(text).refined
        return backend_success(refined), None
    except MessageRefineException as error:
        return backend_error(), error.error


# style_compare.json -> style_compare_1.json, style_compare_2.json ... 처럼 다음 번호 경로를 구함
def next_output_path(base):
    path = Path(base)
    pattern = re.compile(rf"^{re.escape(path.stem)}_(\d+){re.escape(path.suffix)}$")
    numbers = [
        int(match.group(1))
        for file in path.parent.glob(f"{path.stem}_*{path.suffix}")
        if (match := pattern.match(file.name))
    ]
    return path.with_name(f"{path.stem}_{max(numbers, default=0) + 1}{path.suffix}")


# 실행할 때마다 새 파일로 저장 (이미 있는 파일은 덮어쓰지 않음)
def save_run(base, run):
    path = next_output_path(base)
    with path.open("x", encoding="utf-8") as file:
        json.dump(run, file, ensure_ascii=False, indent=2)
    return path


async def main(target, repeat, output):
    sem = asyncio.Semaphore(4)

    async def run(answers, message):
        async with sem:
            return await refine_once(target, answers, message)

    rows = []
    for message in MESSAGES:
        print(f"\n### 입력: {message}")
        print("| 취향 조합 | 결과 |")
        print("| --- | --- |")
        for name, combo in COMBOS.items():
            answers = to_answers(combo)
            outcomes = await asyncio.gather(
                *(run(answers, message) for _ in range(repeat))
            )
            texts = []
            for attempt, (response, ai_error) in enumerate(outcomes, start=1):
                rows.append(
                    {
                        "message": message,
                        "combo": name,
                        "answers": answers,
                        "attempt": attempt,
                        "response": response,
                        "ai_error": ai_error,
                    }
                )
                texts.append(
                    f"(에러: {ai_error})"
                    if ai_error
                    else response["data"]["refined_message"]
                )
            print(f"| {name} | {' / '.join(texts)} |")

    model = (
        settings.refine_server_model
        if target == "runpod"
        else settings.claude_model_haiku
    )
    run_result = {
        "meta": {
            "run_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "target": target,
            "model": model,
            "repeat": repeat,
            "prompt_hash": hashlib.sha1(FIXED_RULES.encode()).hexdigest()[:8],
        },
        "rows": rows,
    }
    path = save_run(output, run_result)
    print(f"\n결과를 {path} 에 저장했습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["runpod", "claude"], default="runpod")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", default=OUTPUT_PATH)
    args = parser.parse_args()
    asyncio.run(main(args.target, args.repeat, args.output))
