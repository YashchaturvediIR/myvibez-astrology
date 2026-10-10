from pydantic import BaseModel, Field
from typing import Literal

class BirthDetails(BaseModel):
    date: str
    time: str
    place: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str

class Settings(BaseModel):
    zodiac: Literal["sidereal"] = "sidereal"
    ayanamsha: Literal["Lahiri"] = "Lahiri"
    node_type: Literal["mean", "true"] = "mean"
    house_system: Literal["whole_sign"] = "whole_sign"

class KundliRequest(BaseModel):
    birth_details: BirthDetails
    settings: Settings = Settings()
