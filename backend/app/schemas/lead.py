from pydantic import BaseModel, EmailStr


class LeadCreate(BaseModel):
    company: str
    contact_name: str
    email: EmailStr
    niche: str = "marketing agency"
    notes: str = ""
