import random
import smtplib
from email.mime.text import MIMEText
import os
from datetime import datetime, UTC, timedelta
from backend.database import supabase

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

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
    expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()

    # Delete any existing OTP for this email first
    supabase.table("otp_store").delete().eq("email", email).execute()

    # Store fresh OTP in Supabase
    supabase.table("otp_store").insert({
        "email": email,
        "otp": otp,
        "expires_at": expires_at
    }).execute()

    send_email(email, otp)
    return otp

def verify_otp(email, otp):
    result = supabase.table("otp_store") \
        .select("*") \
        .eq("email", email) \
        .execute()

    if not result.data:
        return False

    row = result.data[0]

    # Always delete after retrieval (one-time use)
    supabase.table("otp_store").delete().eq("email", email).execute()

    # Check expiry
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
        return False

    # Check OTP match
    return row["otp"] == otp
