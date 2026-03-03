import random
import resend
import os
from datetime import datetime, UTC, timedelta
from backend.database import supabase

resend.api_key = os.getenv("RESEND_API_KEY")

def generate_otp(email):
    if not resend.api_key:
        raise Exception("RESEND_API_KEY not configured")

    otp = str(random.randint(100000, 999999))
    expires_at = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()

    # Delete any existing OTP for this email
    supabase.table("otp_store").delete().eq("email", email).execute()

    # Store in Supabase
    supabase.table("otp_store").insert({
        "email": email,
        "otp": otp,
        "expires_at": expires_at
    }).execute()

    # Send via Resend
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": email,
        "subject": "Authentication OTP",
        "text": f"Your Login OTP is:\n\n{otp}\n\nDo not share this code."
    })

    return otp

def verify_otp(email, otp):
    result = supabase.table("otp_store") \
        .select("*") \
        .eq("email", email) \
        .execute()

    if not result.data:
        return False

    row = result.data[0]

    supabase.table("otp_store").delete().eq("email", email).execute()

    if datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
        return False

    return row["otp"] == otp
