"""
app.models.fingerprint
========================
Schémas Pydantic : validation stricte des entrées/sorties de l'API.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

ALLOWED_FINGER_TYPES = {
    "right_thumb", "right_index", "right_middle", "right_ring", "right_pinky",
    "left_thumb", "left_index", "left_middle", "left_ring", "left_pinky",
}


class EnrollRequest(BaseModel):
    employeeId: str = Field(..., min_length=1, max_length=64)
    fingerType: str
    image: str = Field(..., description="Image base64 (avec ou sans préfixe data:image/...)")

    @field_validator("employeeId")
    @classmethod
    def employee_id_safe(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("employeeId ne doit contenir que lettres, chiffres, - et _")
        return v

    @field_validator("fingerType")
    @classmethod
    def finger_type_whitelist(cls, v: str) -> str:
        if v not in ALLOWED_FINGER_TYPES:
            raise ValueError(f"fingerType doit être l'un de : {sorted(ALLOWED_FINGER_TYPES)}")
        return v


class EnrollResponse(BaseModel):
    success: bool
    employeeId: str
    fingerType: str
    message: str


class IdentifyRequest(BaseModel):
    image: str


class IdentifyResponse(BaseModel):
    success: bool
    employeeId: str | None = None
    score: int = 0
    message: str


class VerifyRequest(BaseModel):
    employeeId: str = Field(..., min_length=1, max_length=64)
    image: str


class VerifyResponse(BaseModel):
    success: bool
    match: bool
    employeeId: str
    score: int = 0
    message: str


class HealthResponse(BaseModel):
    status: str
    enrolled_employees: int
    service: str


class DeleteRequest(BaseModel):
    employeeId: str = Field(..., min_length=1, max_length=64)

    @field_validator("employeeId")
    @classmethod
    def employee_id_safe(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("employeeId ne doit contenir que lettres, chiffres, - et _")
        return v


class DeleteResponse(BaseModel):
    success: bool
    employeeId: str
    message: str
