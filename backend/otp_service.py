import random
import smtplib
from email.mime.text import MIMEText

OTP_STORE = {}

# ==============================
# CHANGE THESE
# ==============================

EMAIL_ADDRESS = "putuislam4@gmail.com"
APP_PASSWORD = "clzm nqnh drsd goor"


# ==============================
# SEND EMAIL
# ==============================

def send_email(receiver, otp):

    msg = MIMEText(f"""
Your Login OTP is:

{otp}

Do not share this code.
""")

    msg["Subject"] = "Authentication OTP"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, APP_PASSWORD)
        server.send_message(msg)


# ==============================
# GENERATE OTP
# ==============================

def generate_otp(email):

    otp = str(random.randint(100000, 999999))

    OTP_STORE[email] = otp

    send_email(email, otp)

    print("OTP SENT TO:", email)

    return otp


# ==============================
# VERIFY OTP
# ==============================

def verify_otp(email, otp):

    stored = OTP_STORE.get(email)

    if stored == otp:
        del OTP_STORE[email]
        return True

    return False