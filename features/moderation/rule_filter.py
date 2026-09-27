# rule_filter.py
import re

from korcen import korcen as korcen_engine


class RuleViolation(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


KORCEN_GAP_WORDS = ["씨발", "존나"]


def _check_offensive_language(text: str) -> None:
    for word in KORCEN_GAP_WORDS:
        if word in text:
            raise RuleViolation("부적절한 표현이 포함되어 있어요. 다시 작성해주세요.")
    if korcen_engine.check(text):
        raise RuleViolation("부적절한 표현이 포함되어 있어요. 다시 작성해주세요.")


PROHIBITED_ITEMS = [
    "마약",
    "필로폰",
    "대마초",
    "대마",
    "히로뽕",
    "총기",
    "실탄",
    "흉기",
    "도난품",
    "장물",
    "위조지폐",
    "위조여권",
]


def _check_prohibited_item(text: str) -> None:
    for word in PROHIBITED_ITEMS:
        if word in text:
            raise RuleViolation(
                "거래할 수 없는 품목이 포함되어 있어요. 내용을 확인해주세요."
            )


PHONE_PATTERN = re.compile(r"01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}")
CONTACT_TRIGGER_WORDS = ["카톡", "카카오톡", "인스타", "라인아이디", "텔레그램"]


def _check_personal_contact(text: str) -> None:
    if PHONE_PATTERN.search(text):
        raise RuleViolation("게시글에서 연락처나 SNS 계정 정보를 제거해주세요.")
    for word in CONTACT_TRIGGER_WORDS:
        if word in text:
            raise RuleViolation("게시글에서 연락처나 SNS 계정 정보를 제거해주세요.")


URL_PATTERN = re.compile(r"(https?://|www\.)\S+")
SPAM_WORDS = ["최저가", "재구매", "링크 클릭", "무료체험"]


def _check_spam(text: str) -> None:
    if URL_PATTERN.search(text):
        raise RuleViolation("광고성 문구가 포함되어 있어요. 내용을 확인해주세요.")
    for word in SPAM_WORDS:
        if word in text:
            raise RuleViolation("광고성 문구가 포함되어 있어요. 내용을 확인해주세요.")


def run_rule_filter(title: str, content: str) -> None:
    combined = f"{title}\n{content}"
    _check_offensive_language(combined)
    _check_prohibited_item(combined)
    _check_personal_contact(combined)
    _check_spam(combined)
