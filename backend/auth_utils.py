from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(password: str):
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(password[:72])

def verify_password(password: str, hashed: str):
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.verify(password[:72], hashed)

