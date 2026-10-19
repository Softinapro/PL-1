from pydantic import BaseModel, ConfigDict

from app.models.rejection_reason import RejectionScope


class RejectionReasonPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: RejectionScope
    text: str
