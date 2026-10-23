from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class TaskWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: str | None = Field(default=None, max_length=10000)
    completed: bool = False


class TaskRead(TaskWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
