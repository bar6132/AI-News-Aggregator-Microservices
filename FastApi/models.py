from pydantic import BaseModel, EmailStr, validator
from typing import List

ALLOWED_PREFERENCES = {
    "business", "crime", "domestic", "education", "entertainment",
    "environment", "food", "health", "lifestyle", "other", "politics",
    "science", "sports", "technology", "top", "tourism", "world"
}


def validate_preferences(preferences: List[str]):
    for preference in preferences:
        if preference not in ALLOWED_PREFERENCES:
            raise ValueError(f"Invalid preference: {preference}")
    if len(preferences) > 5:
        raise ValueError("You can select up to 5 preferences only.")
    return preferences


class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr
    preferences: List[str] = []

    @validator('preferences')
    def validate_preferences_list(cls, value):
        validate_preferences(value)  # Validate the whole preferences list
        return value


class UserLogin(BaseModel):
    username: str
    password: str
