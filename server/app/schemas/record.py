from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import RecordType, TemplateType


class RecordCreate(BaseModel):
    type: RecordType = "diary"
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = None
    mood: Optional[str] = Field(default=None, max_length=20)
    tags: Optional[str] = Field(default=None, max_length=200)
    book_title: Optional[str] = Field(default=None, max_length=200)
    book_author: Optional[str] = Field(default=None, max_length=100)
    project: Optional[str] = Field(default=None, max_length=100)
    weather: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=100)
    record_date: Optional[date] = None
    record_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    template_id: Optional[int] = Field(default=None, ge=1)


class RecordUpdate(BaseModel):
    type: Optional[RecordType] = None
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = None
    mood: Optional[str] = Field(default=None, max_length=20)
    tags: Optional[str] = Field(default=None, max_length=200)
    book_title: Optional[str] = Field(default=None, max_length=200)
    book_author: Optional[str] = Field(default=None, max_length=100)
    project: Optional[str] = Field(default=None, max_length=100)
    weather: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=100)
    record_date: Optional[date] = None
    record_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: str
    title: str
    content: Optional[str]
    mood: Optional[str]
    tags: Optional[str]
    book_title: Optional[str]
    book_author: Optional[str]
    project: Optional[str]
    weather: Optional[str]
    location: Optional[str]
    record_date: date
    record_time: Optional[str]
    created_at: datetime
    updated_at: datetime


class CalendarDay(BaseModel):
    date: str
    total: int = 0
    diary: int = 0
    worklog: int = 0
    note: int = 0
    tasks: int = 0  # 当日到期任务数


class TemplateCreate(BaseModel):
    type: TemplateType = "diary"
    name: str = Field(min_length=1, max_length=100)
    icon: str = Field(default="📄", max_length=20)
    content: Optional[str] = None


class TemplateUpdate(BaseModel):
    type: Optional[TemplateType] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=20)
    content: Optional[str] = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    type: str
    name: str
    icon: str
    content: Optional[str]
    is_preset: bool
