# exceptions.py
class VisionException(Exception):
    def __init__(self, error: str, message: str):
        self.error = error
        self.message = message
        super().__init__(message)


class VisionInvalidInputException(VisionException):
    def __init__(self):
        super().__init__(
            error="invalid_input",
            message="이미지 파일이 없거나 지원하지 않는 형식이에요. jpeg/png/webp 파일을 1~3장 올려주세요.",
        )


class VisionFileTooLargeException(VisionException):
    def __init__(self):
        super().__init__(
            error="file_too_large",
            message="이미지 파일 하나당 5MB를 초과했어요. 용량을 줄여 다시 업로드해주세요.",
        )


class VisionProcessingException(VisionException):
    def __init__(self):
        super().__init__(
            error="internal_error",
            message="이미지 분석에 실패했어요. 잠시 후 다시 시도해주세요.",
        )
