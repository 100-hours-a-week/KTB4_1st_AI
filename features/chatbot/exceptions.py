class ChatbotException(Exception):
    error: str = "internal_error"
    message: str = "챗봇 응답에 실패했습니다."

    def __init__(self, stage: str = "unknown", detail: str | None = None):
        self.stage = stage
        self.detail = detail
        super().__init__(detail or self.message)


class ClaudeRateLimitedError(ChatbotException):
    error = "claude_rate_limited"
    message = "요청이 많아 잠시 후 다시 시도해주세요."


class ClaudeTimeoutError(ChatbotException):
    error = "claude_timeout"
    message = "응답이 지연되고 있어요. 잠시 후 다시 시도해주세요."


class ClaudeApiError(ChatbotException):
    error = "claude_api_error"
    message = "답변을 생성하지 못했어요. 잠시 후 다시 시도해주세요."


class InvalidModelResponseError(ChatbotException):
    error = "invalid_model_response"
    message = "답변을 처리하지 못했어요. 다시 시도해주세요."


class EmbeddingModelError(ChatbotException):
    error = "embedding_model_error"
    message = "검색 준비에 실패했어요. 잠시 후 다시 시도해주세요."


class RetrievalError(ChatbotException):
    error = "retrieval_error"
    message = "관련 정책을 찾는 중 문제가 생겼어요. 다시 시도해주세요."
