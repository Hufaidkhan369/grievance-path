"""Pydantic request/response schemas."""
from pydantic import BaseModel, EmailStr, Field


class ComplaintIn(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=15, max_length=5000)
    category: str = ""
    location: str = ""
    city: str = ""
    pincode: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    # Optional MANUAL routing override: the citizen picks the department
    # themselves and skips the automatic analysis.
    manual_department_code: str | None = None
    manual_reason: str = ""


class FeedbackIn(BaseModel):
    rating: int = Field(5, ge=1, le=5)
    comment: str = Field("", max_length=2000)


class UserIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str = ""
    phone: str = ""
    city: str = ""
    password: str = Field("", max_length=100)


class UserLogin(BaseModel):
    identifier: str = ""
    password: str = ""


class ComplaintUpdate(BaseModel):
    status: str = ""           # IN_PROGRESS | RESOLVED | REJECTED | CLOSED
    priority: str = ""         # LOW | MEDIUM | HIGH | URGENT
    note: str = ""
    reassign_code: str = ""    # admin reassignment


class TrackResponse(BaseModel):
    ok: bool
    tracking_id: str | None = None
    status: str | None = None
    department: dict | None = None
    history: list[dict] | None = None
    message: str = ""


class RoutingResult(BaseModel):
    department_id: int | None = None
    department_code: str | None = None
    department_name: str | None = None
    confidence: float = 0.0
    method: str = "classifier"
    matched_keywords: list[str] = []
    explanation: str = ""
