from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found exception"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationException(AppException):
    """Validation error exception"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class UnauthorizedException(AppException):
    """Unauthorized access exception"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )
