from typing import List, Dict, Optional
from pydantic import BaseModel, EmailStr

class RegisterUser(BaseModel):
    email: EmailStr
    username: str
    password: str

class LoginUser(BaseModel):
    email: EmailStr
    password: str
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0
    mouse: Optional[List[Dict]] = []

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str
    session_id: str
