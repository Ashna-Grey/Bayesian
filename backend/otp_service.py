import random
import smtplib
from email.mime.text import MIMEText
import os

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

OTP_STORE = {}

def send_email(receiver, otp):
    msg = MIMEText(f"""
Your Login OTP is:

{otp}

Do not share this code.
""")

    msg["Subject"] = "Authentication OTP"
    msg["From"] = EMAIL_USER
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def generate_otp(email):
    if not EMAIL_USER or not EMAIL_PASS:
        raise Exception("Email credentials not configured")

    otp = str(random.randint(100000, 999999))
    OTP_STORE[email] = otp

    send_email(email, otp)

    return otp

def verify_otp(email, otp):
    stored = OTP_STORE.get(email)

    if stored == otp:
        del OTP_STORE[email]
        return True

    return False
