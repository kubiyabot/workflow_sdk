from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from .executors import Executor


# Handler definitions
class Handler(BaseModel):
    """Handler for workflow events"""

    command: Optional[str] = None
    script: Optional[str] = None
    executor: Optional[Executor] = None


class HandlerOn(BaseModel):
    """Handlers for different workflow events"""

    success: Optional[Handler] = None
    failure: Optional[Handler] = None
    cancel: Optional[Handler] = None
    exit: Optional[Handler] = None


# SMTP and email configuration
class SMTPConfig(BaseModel):
    """SMTP configuration for email notifications"""

    host: str
    port: str = "587"
    username: str
    password: str


class MailConfig(BaseModel):
    """Email configuration"""

    from_address: str = Field(alias="from")
    to: str
    prefix: Optional[str] = None
    attach_logs: bool = Field(False, alias="attachLogs")

    model_config = ConfigDict(populate_by_name=True)


class MailOn(BaseModel):
    """Email notification triggers"""

    success: bool = False
    failure: bool = True
