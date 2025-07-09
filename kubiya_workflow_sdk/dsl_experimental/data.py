from typing import Any, Optional
from pydantic import BaseModel, RootModel


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


class WorkflowParams(RootModel[list[Parameter]]):

    def model_dump(self, *args, **kwargs) -> dict:
        return {r.name: r.value for r in self.root}


class EnvironmentVariable(BaseModel):
    """Represents an environment variable"""

    name: str
    value: str


class EnvironmentVariables(RootModel[list[EnvironmentVariable]]):

    def model_dump(self, *args, **kwargs) -> dict:
        return {r.name: r.value for r in self.root}
