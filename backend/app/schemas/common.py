from typing import Generic, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 20


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Response(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None
