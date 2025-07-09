from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class Precondition(BaseModel):
    """Represents a precondition for step execution"""

    condition: str
    expected: str
    description: Optional[str] = None


class RetryPolicy(BaseModel):
    """Retry configuration for steps"""

    limit: int = 3
    interval_sec: int = 30
    exit_codes: Optional[List[int]] = None


class RepeatPolicy(BaseModel):
    """Repeat configuration for steps"""

    repeat: bool = True
    interval_sec: int = 60
    limit: Optional[int] = None
    exit_code: Optional[List[int]] = None
    condition: Optional[str] = None
    expected: Optional[str] = None


class ContinueOn(BaseModel):
    """Configuration for continuing workflow on various conditions"""

    failure: bool = False
    skipped: bool = False
    exit_code: Optional[List[int]] = None
    output: Optional[List[str]] = None
    mark_success: bool = False


class ParallelConfig(BaseModel):
    """Configuration for parallel step execution"""

    items: List[str]
    max_concurrent: int = Field(default=1, alias="maxConcurrent")

    model_config = ConfigDict(populate_by_name=True)
