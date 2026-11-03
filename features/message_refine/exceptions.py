class MessageRefineException(Exception):
    error: str = "internal_error"
    message: str = "채팅 다듬기에 실패했습니다."

    def __init__(self, stage: str = "unknown", detail: str | None = None):
        self.stage = stage
        self.detail = detail
        super().__init__(detail or self.message)


class RefineServerConnectionError(MessageRefineException):
    error = "refine_server_unavailable"
    message = "채팅 다듬기 서버에 연결하지 못했어요. 잠시 후 다시 시도해주세요."


class RefineServerTimeoutError(MessageRefineException):
    error = "refine_server_timeout"
    message = "응답이 지연되고 있어요. 잠시 후 다시 시도해주세요."


class RefineServerAuthError(MessageRefineException):
    error = "refine_server_auth_error"
    message = "채팅 다듬기 서버 인증에 실패했어요. 잠시 후 다시 시도해주세요."


class RefineServerOverloadedError(MessageRefineException):
    error = "refine_server_overloaded"
    message = "요청이 많아 잠시 후 다시 시도해주세요."


class RefineServerApiError(MessageRefineException):
    error = "refine_server_api_error"
    message = "채팅 다듬기에 실패했어요. 잠시 후 다시 시도해주세요."


class InvalidRefineResponseError(MessageRefineException):
    error = "invalid_refine_response"
    message = "응답을 처리하지 못했어요. 다시 시도해주세요."
