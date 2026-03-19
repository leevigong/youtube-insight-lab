from pydantic import BaseModel


class Category(BaseModel):
    id: str
    title: str
    assignable: bool


class CategoriesResponse(BaseModel):
    categories: list[Category]
