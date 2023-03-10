from ape.exceptions import ApeException
from ape.logging import logger


class SilverBackException(ApeException):
    pass


class Halt(SilverBackException):
    def __init__(self):
        super().__init__("App halted, must restart manually")


class CircuitBreaker(SilverBackException):
    """Custom exception (created by user) that should trigger a shutdown."""

    def __init__(self, message: str):
        logger.error(message)
        super().__init__(message)
