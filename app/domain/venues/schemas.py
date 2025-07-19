from pydantic import BaseModel, Field, ConfigDict, field_validator

class VenueCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    address_id: int

    @field_validator("name", mode="before")
    def strip_name(cls, v: str) -> str:
        return v.strip()

class VenueReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address_id: int

class VenueUpdateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=100)

    @field_validator("name", mode="before")
    def strip_name(cls, v: str) -> str:
        return v.strip()
