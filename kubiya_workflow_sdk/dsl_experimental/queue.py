from pydantic import BaseModel, Field, ConfigDict


# Queue configuration
class QueueConfig(BaseModel):
    """Queue configuration"""
    name: str
    max_active_runs: int = Field(1, alias="maxActiveRuns")
    
    model_config = ConfigDict(populate_by_name=True)
