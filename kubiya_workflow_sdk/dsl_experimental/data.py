from typing import Any, Optional
from pydantic import BaseModel


class FileDefinition(BaseModel):
    """Represents a file to be created during execution"""
    destination: str
    content: str


class ArgDefinition(BaseModel):
    """Represents an argument definition for tools"""
    name: str
    type: str
    required: bool = False
    default: Optional[Any] = None


class Parameter(BaseModel):
    """Represents a workflow parameter"""
    name: str
    value: Any
    description: Optional[str] = None


class EnvironmentVariable(BaseModel):
    """Represents an environment variable"""
    name: str
    value: str
