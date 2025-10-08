from app.core.utils.serialization import normalize_ctx


class AppError(Exception):
    def __init__(self, message: str = "", *, ctx: dict | None = None) -> None:
        super().__init__(message or self.__class__.__name__)
        self.ctx = normalize_ctx(ctx or {})


class NotFound(AppError):
    pass
class Unauthorized(AppError):
    pass
class Forbidden(AppError):
    pass
class Conflict(AppError):
    pass
class InvalidInput(AppError):
    pass
class Unprocessable(AppError):
    pass
