from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

_COLOR = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(default="#64748B", pattern=_COLOR)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    color: Optional[str] = Field(default=None, pattern=_COLOR)


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    color: str
    created_at: Optional[datetime] = None
    # 引用该标签的未删除任务数（列表接口带出，省掉前端 N 次请求）
    task_count: int = 0
