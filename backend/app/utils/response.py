from app.schemas.common import Response


def success(data=None, message: str = "success") -> dict:
    return Response(code=200, message=message, data=data).model_dump()


def error(code: int = 400, message: str = "error", data=None) -> dict:
    return Response(code=code, message=message, data=data).model_dump()
