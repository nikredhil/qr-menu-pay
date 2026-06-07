"""Auth payloads: phone OTP for customers, password for staff."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

# Indian mobile numbers: 10 digits starting 6-9, optionally +91 / 91 prefixed.
_PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits


class OtpRequest(BaseModel):
    phone: str
    name: str | None = Field(default=None, max_length=80)

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, v: str) -> str:
        norm = normalize_phone(v)
        if not _PHONE_RE.match(norm):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return norm


class OtpRequestResult(BaseModel):
    phone: str
    expires_in: int
    # Present only in demo mode so the flow is testable without an SMS provider.
    debug_otp: str | None = None


class OtpVerify(BaseModel):
    phone: str
    code: str = Field(min_length=4, max_length=8)

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, v: str) -> str:
        return normalize_phone(v)


class CustomerToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    phone: str
    name: str | None = None


class AdminLogin(BaseModel):
    password: str


class AdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "admin"
