# exceptions.py
class ModerationException(Exception):
    def __init__(self, error: str, message: str):
        self.error = error
        self.message = message
        super().__init__(message)


class ModerationMissingTitleException(ModerationException):
    def __init__(self):
        super().__init__(
            error="missing_title",
            message="제목을 입력해주세요.",
        )


class ModerationMissingContentException(ModerationException):
    def __init__(self):
        super().__init__(
            error="missing_content",
            message="상세 내용을 입력해주세요.",
        )


class ModerationProcessingException(ModerationException):
    def __init__(self):
        super().__init__(
            error="internal_error",
            message="텍스트 검증에 실패했어요. 잠시 후 다시 시도해주세요.",
        )
