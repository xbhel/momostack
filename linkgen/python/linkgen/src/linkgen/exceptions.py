class RetryableException(Exception):
    def __init__(self, description: str) -> None:
        super().__init__(f"{self.__class__.__name__}: {description}")
