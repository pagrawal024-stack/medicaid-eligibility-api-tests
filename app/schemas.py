"""Request validation models."""
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from app.notices import SUPPORTED_LANGUAGES

Language = Literal[SUPPORTED_LANGUAGES]


class ApplicantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    date_of_birth: date
    state_resident: StrictBool
    citizen_or_qualified: StrictBool
    pregnant: StrictBool = False
    disabled: StrictBool = False
    caregiver_child_under_14: StrictBool = False
    preferred_language: Language
    email: Optional[str] = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: Optional[str] = Field(default=None, pattern=r"^\+?[0-9]{10,15}$")

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return v

    @model_validator(mode="after")
    def needs_contact(self):
        if not self.email and not self.phone:
            raise ValueError("at least one of email or phone is required")
        return self


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applicant_id: int = Field(gt=0)
    household_size: int = Field(ge=1, le=20)
    monthly_income: Decimal = Field(ge=0, le=1_000_000, decimal_places=2)
    work_hours_monthly: int = Field(ge=0, le=744)  # 744 = 31 days x 24 h
    application_date: date = Field(default_factory=date.today)

    @field_validator("monthly_income", mode="before")
    @classmethod
    def money_from_text(cls, v):
        # Convert floats through str so 1799.76 stays 1799.76, not 1799.7599999...
        if isinstance(v, float):
            return Decimal(str(v))
        return v
