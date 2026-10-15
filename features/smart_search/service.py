# service.py
import json
import re

from core.config import settings
from features.smart_search.exceptions import SmartSearchProcessingException
from features.smart_search.prompts import RANK_CANDIDATES_PROMPT
from features.smart_search.schemas import Candidate
from shared.llm.claude_provider import ClaudeTransientError, generate

MAX_CANDIDATES = 50
MAX_PREFERENCE_LENGTH = 200
MAX_TITLE_LENGTH = 100


def _clean_text(text: str, max_length: int) -> str:
    text = text.replace("<", "").replace(">", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length]


def _prepare_candidates(
    candidates: list[Candidate],
) -> tuple[list[tuple[int, str]], list[int], list[int]]:
    seen: set[int] = set()
    rankable: list[tuple[int, str]] = []
    overflow: list[int] = []
    empty_title: list[int] = []

    for candidate in candidates:
        if candidate.itemId in seen:
            continue
        seen.add(candidate.itemId)

        title = _clean_text(candidate.title, MAX_TITLE_LENGTH)
        if not title:
            empty_title.append(candidate.itemId)
        elif len(rankable) >= MAX_CANDIDATES:
            overflow.append(candidate.itemId)
        else:
            rankable.append((candidate.itemId, title))

    return rankable, overflow, empty_title


def _build_prompt(titles: list[str], preference_text: str) -> str:
    numbered_candidates = "\n".join(
        f"{number}. {title}" for number, title in enumerate(titles, start=1)
    )
    return RANK_CANDIDATES_PROMPT.replace("{preference_text}", preference_text).replace(
        "{numbered_candidates}", numbered_candidates
    )


def _extract_json(raw_text: str) -> dict:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("응답에 JSON이 없습니다.")
    return json.loads(raw_text[start : end + 1])


def _parse_ranked(raw_text: str, count: int) -> list[int]:
    data = _extract_json(raw_text)
    ranked = data.get("ranked")
    if not isinstance(ranked, list):
        raise TypeError("'ranked'가 리스트가 아닙니다.")

    order: list[int] = []
    seen: set[int] = set()
    for number in ranked:
        if isinstance(number, bool) or not isinstance(number, int):
            continue
        if number < 1 or number > count or number in seen:
            continue
        seen.add(number)
        order.append(number - 1)

    if not order:
        raise ValueError("'ranked'에 유효한 번호가 없습니다.")

    ranked_set = set(order)
    order.extend(index for index in range(count) if index not in ranked_set)
    return order


async def _call_llm_rank(titles: list[str], preference_text: str) -> list[int]:
    prompt = _build_prompt(titles, preference_text)
    last_error: Exception | None = None

    for _ in range(2):
        try:
            raw_text = await generate(
                prompt=prompt,
                model=settings.claude_model_haiku,
            )
            return _parse_ranked(raw_text, len(titles))
        except ClaudeTransientError as error:
            raise SmartSearchProcessingException() from error
        except Exception as error:  # noqa: BLE001
            last_error = error

    raise SmartSearchProcessingException() from last_error


async def rank_candidates_by_preference(
    candidates: list[Candidate],
    preference_text: str | None,
) -> list[int]:
    rankable, overflow, empty_title = _prepare_candidates(candidates)
    tail = overflow + empty_title

    preference_text = _clean_text(preference_text or "", MAX_PREFERENCE_LENGTH)

    if len(rankable) <= 1 or not preference_text:
        return [item_id for item_id, _ in rankable] + tail

    titles = [title for _, title in rankable]
    order = await _call_llm_rank(titles, preference_text)

    ranked_ids = [rankable[index][0] for index in order]
    return ranked_ids + tail
