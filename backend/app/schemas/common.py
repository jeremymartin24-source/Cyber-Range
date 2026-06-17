from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
