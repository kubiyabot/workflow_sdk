from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from .data import FileDefinition, ArgDefinition


# Enums for type safety
class ExecutorType(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    SSH = "ssh"
    HTTP = "http"
    MAIL = "mail"
    JQ = "jq"
    DAG = "dag"
    TOOL = "tool"
    KUBIYA = "kubiya"
    AGENT = "agent"


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class SignalType(str, Enum):
    SIGTERM = "SIGTERM"
    SIGKILL = "SIGKILL"
    SIGINT = "SIGINT"


# Executor configurations
class DockerExecutorConfig(BaseModel):
    image: str
    volumes: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    network: Optional[str] = None
    platform: Optional[str] = None
    auto_remove: bool = True


class SSHExecutorConfig(BaseModel):
    host: str
    user: str
    port: int = 22
    key_file: Optional[str] = None
    password: Optional[str] = None
    strict_host_key_checking: bool = True


class HTTPExecutorConfig(BaseModel):
    url: str
    method: HTTPMethod = HTTPMethod.GET
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    timeout_sec: int = 30
    silent: bool = False


class MailExecutorConfig(BaseModel):
    to: str
    from_address: str = Field(alias="from")
    subject: str
    message: str
    attachments: Optional[List[str]] = None

    model_config = ConfigDict(populate_by_name=True)


class JQExecutorConfig(BaseModel):
    query: str
    raw: bool = False


class DAGExecutorConfig(BaseModel):
    params: Optional[str] = None


class KubiyaExecutorConfig(BaseModel):
    url: str
    method: HTTPMethod = HTTPMethod.GET
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None


class AgentExecutorConfig(BaseModel):
    agent_name: str
    message: str
    context: Optional[Dict[str, Any]] = None


# Tool definition
class ToolDef(BaseModel):
    name: str
    description: str = ""
    type: str
    image: str
    content: str
    with_files: Optional[List[FileDefinition]] = None
    args: Optional[List[ArgDefinition]] = None
    secrets: Optional[List[str]] = None


class ToolExecutorConfig(BaseModel):
    tool_def: ToolDef
    args: Optional[Dict[str, Any]] = None
    secrets: Optional[Dict[str, Any]] = None


# Executor base model
class Executor(BaseModel):
    type: ExecutorType
    config: Optional[
        Union[
            DockerExecutorConfig,
            SSHExecutorConfig,
            HTTPExecutorConfig,
            MailExecutorConfig,
            JQExecutorConfig,
            DAGExecutorConfig,
            ToolExecutorConfig,
            KubiyaExecutorConfig,
            AgentExecutorConfig,
            Dict[str, Any],  # Fallback for custom executors
        ]
    ] = None
