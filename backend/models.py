from typing import List, Dict
from pydantic import BaseModel
class RegisterUser(BaseModel):
    email: str
    username: str
    password: str
class LoginUser(BaseModel):
    email: str
    password: str
    latitude: float
    longitude: float
    mouse: List[Dict]
class OTPVerify(BaseModel):
    email: str
    otp: str
    session_id: str
