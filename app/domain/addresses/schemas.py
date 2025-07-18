from pydantic import BaseModel, Field, ConfigDict

class AddressCreateDTO(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    street: str = Field(min_length=2, max_length=200)
    postal_code: str = Field(min_length=4, max_length=12)
    building_number: str = Field(min_length=1, max_length=10)
    apartment_number: str | None = Field(min_length=1, max_length=10, default=None)
    country_code: str = Field(min_length=2, max_length=2, pattern="^[A-Z]{2}$")


class AddressReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str
    street: str
    postal_code: str
    building_number: str
    apartment_number: str | None
    country_code: str


class AddressPutDTO(AddressCreateDTO):
    pass
