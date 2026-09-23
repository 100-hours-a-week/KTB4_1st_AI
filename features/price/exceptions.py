class PriceEstimationException(Exception):
    def __init__(
        self, error: str = "internal_error", message: str = "가격 추정에 실패했습니다."
    ):
        self.error = error
        self.message = message
        super().__init__(message)
