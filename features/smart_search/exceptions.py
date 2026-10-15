# exceptions.py


class SmartSearchException(Exception):
    def __init__(self, error: str, message: str):
        self.error = error
        self.message = message
        super().__init__(message)


class SmartSearchProcessingException(SmartSearchException):
    def __init__(self):
        super().__init__(
            error="internal_error",
            message="스마트 검색에 실패했어요. 잠시 후 다시 시도해주세요.",
        )
