"""
biometric_client.models
=========================
Structures de données typées retournées par BiometricClient. Utilise des
dataclasses standard (pas de dépendance à pydantic) pour que ce SDK reste
installable dans n'importe quel projet Python sans imposer de version de
pydantic qui pourrait entrer en conflit avec celle du projet hôte.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EnrollResult:
    success: bool
    employee_id: str
    finger_type: str
    message: str

    @classmethod
    def from_dict(cls, data: dict) -> "EnrollResult":
        return cls(
            success=data.get("success", False),
            employee_id=data.get("employeeId", ""),
            finger_type=data.get("fingerType", ""),
            message=data.get("message", ""),
        )


@dataclass(frozen=True)
class IdentifyResult:
    success: bool
    employee_id: Optional[str]
    score: Optional[int]
    message: str

    @classmethod
    def from_dict(cls, data: dict) -> "IdentifyResult":
        return cls(
            success=data.get("success", False),
            employee_id=data.get("employeeId"),
            score=data.get("score"),
            message=data.get("message", ""),
        )


@dataclass(frozen=True)
class VerifyResult:
    success: bool
    match: bool
    employee_id: str
    score: Optional[int]
    message: str

    @classmethod
    def from_dict(cls, data: dict) -> "VerifyResult":
        return cls(
            success=data.get("success", False),
            match=data.get("match", False),
            employee_id=data.get("employeeId", ""),
            score=data.get("score"),
            message=data.get("message", ""),
        )


@dataclass(frozen=True)
class DeleteResult:
    success: bool
    employee_id: str
    message: str

    @classmethod
    def from_dict(cls, data: dict) -> "DeleteResult":
        return cls(
            success=data.get("success", False),
            employee_id=data.get("employeeId", ""),
            message=data.get("message", ""),
        )


@dataclass(frozen=True)
class HealthResult:
    status: str
    enrolled_employees: int
    service: str

    @classmethod
    def from_dict(cls, data: dict) -> "HealthResult":
        return cls(
            status=data.get("status", ""),
            enrolled_employees=data.get("enrolled_employees", 0),
            service=data.get("service", ""),
        )
