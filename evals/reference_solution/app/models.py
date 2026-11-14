from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Priority = Literal["low", "medium", "high"]


def _clean_title(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    value = value.strip()
    if not value:
        raise ValueError("title must not be blank")
    if len(value) > 200:
        raise ValueError("title must be at most 200 characters")
    return value


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: Priority = "medium"
    tags: List[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def check_title(cls, value):
        return _clean_title(value)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, value):
        seen = []
        for tag in value:
            tag = tag.strip().lower()
            if tag and tag not in seen:
                seen.append(tag)
        return seen


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def check_title(cls, value):
        return _clean_title(value)


class Task(BaseModel):
    id: int
    title: str
    description: str = ""
    done: bool = False
    priority: Priority = "medium"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None
