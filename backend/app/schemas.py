from typing import Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class ProcessRequest(BaseModel):
    query: str = Field(..., min_length=1)
    history: list[Message] = Field(default_factory=list)


class ProcessResponse(BaseModel):
    tool: Literal["send_email", "draft_email", "schedule_meeting", "chat"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    args: dict
    missing_fields: list[str] = Field(default_factory=list)
    follow_up_question: Optional[str] = None


class SlotRequest(BaseModel):
    participants: list[str]
    duration_minutes: int = Field(..., gt=0)


class SlotResponse(BaseModel):
    selected_slot: Optional[str] = None
    available_slots: list[str] = Field(default_factory=list)
