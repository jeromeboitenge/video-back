from datetime import datetime

from pydantic import BaseModel


class MediaAssetResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size: int
    created_at: datetime

    model_config = {"from_attributes": True}
