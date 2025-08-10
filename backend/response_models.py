from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Any

class ProjectCreate(BaseModel):
    name: str

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    created_at: datetime

class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    project_id: int
    filename: str
    filepath: str
    size: int
    mime_type: Optional[str] = None
    content: Optional[str] = None
    parse_status: str = "not_parsed"
    parse_error: Optional[str] = None
    uploaded_at: datetime

class ConfigCreate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class ConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None

class ConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    key: str
    value: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class StatusResponse(BaseModel):
    message: str