from pydantic import BaseModel
from typing import Optional

class TestProjects(BaseModel):
    id: Optional[int] = None
    name: str
