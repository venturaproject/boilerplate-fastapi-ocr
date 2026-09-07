from fastapi import HTTPException


class AppException(HTTPException):
    pass


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "No autenticado"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Sin permiso suficiente"):
        super().__init__(status_code=403, detail=detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "No encontrado"):
        super().__init__(status_code=404, detail=detail)


class ConflictException(AppException):
    def __init__(self, detail: str = "Conflicto"):
        super().__init__(status_code=409, detail=detail)


class ValidationException(AppException):
    def __init__(self, detail: str = "Error de validación"):
        super().__init__(status_code=422, detail=detail)


class UnsupportedMediaException(AppException):
    def __init__(self, detail: str = "Tipo de archivo no soportado"):
        super().__init__(status_code=415, detail=detail)


class PayloadTooLargeException(AppException):
    def __init__(self, detail: str = "El archivo excede el tamaño máximo permitido"):
        super().__init__(status_code=413, detail=detail)


class OcrEngineException(AppException):
    def __init__(self, detail: str = "El motor de OCR no pudo procesar el documento"):
        super().__init__(status_code=502, detail=detail)
