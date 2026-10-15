from enum import Enum

from pydantic import BaseModel


class Screen(str, Enum):
    MY_PAGE = "MY_PAGE"
    ITEM_LIST = "ITEM_LIST"
    ITEM_ADD = "ITEM_ADD"
    CHAT_LIST = "CHAT_LIST"
    GROUP_MANAGE = "GROUP_MANAGE"
    INTEREST_LIST = "INTEREST_LIST"
    INQUIRY = "INQUIRY"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatbotRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatbotAction(BaseModel):
    label: str
    screen: Screen


class ChatbotResponse(BaseModel):
    answer: str
    action: ChatbotAction | None = None
