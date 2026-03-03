from fastapi import FastAPI, Request
from backend.database import supabase
from backend.auth_utils import hash_password, verify_password
from backend.models import RegisterUser, LoginUser, OTPVerify
from backend.confidence_engine import *
from backend.otp_service import generate_otp, verify_otp
from backend.bayesian_engine import adaptive_posterior
from backend.learning_engine import learn_likelihoods
from backend.mouse_engine import extract_mouse_speed, mouse_score
import uuid
from datetime import datetime, UTC, timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
import traceback
import os

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error("UNHANDLED EXCEPTION")
    logging.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # FIX: can't use * with credentials=True
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# REGISTER
# =====================================================
@app.post("/register")
def register(user: RegisterUser):

    existing = supabase.table("users") \
        .select("user_id") \
        .eq("email", user.email) \
        .execute()

    if existing.data:
        return {"message": "EMAIL_ALREADY_EXISTS"}

    user_id = str(uuid.uuid4())

    supabase.table("users").insert({
        "user_id": user_id,
        "email": user.email,
        "username": user.username,
        "password_hash": hash_password(user.password),
        "trust_score": 0.5,
        "created_at": datetime.now(UTC).isoformat()
    }).execute()

    return {"message": "User Registered Successfully"}


# =====================================================
# LOGIN
# =====================================================
@app.post("/login")
def login(user: LoginUser, request: Request):

    db = supabase.table("users") \
        .select("*") \
        .eq("email", user.email) \
        .execute()

    if not db.data:
        return {"decision": "USER_NOT_FOUND"}

    db_user = db.data[0]

    ip = request.headers.get(
        "x-forwarded-for",
        request.client.host
    )

    login_time = datetime.now(UTC)

    # ---------- PASSWORD ----------
    password_ok = verify_password(
        user.password,
        db_user["password_hash"]
    )

    # ---------- HISTORY ----------
    history = supabase.table("login_history") \
        .select("*") \
        .eq("user_id", db_user["user_id"]) \
        .execute().data

    # ---------- MOUSE BEHAVIOUR ----------
    mouse_speed = extract_mouse_speed(user.mouse)
    m = mouse_score(mouse_speed, history)

    # ---------- LOG WRONG PASSWORD ----------
    if not password_ok:
        supabase.table("login_history").insert({
            "login_id": str(uuid.uuid4()),
            "user_id": db_user["user_id"],
            "login_time": login_time.isoformat(),
            "ip_address": ip,
            "latitude": user.latitude,
            "longitude": user.longitude,
            "password_correct": False,
            "otp_verified": False,
            "mouse_speed": mouse_speed,  # FIX: was inconsistent with column name
            "confidence_score": 0.1,
            "login_result": "BLOCK"
        }).execute()

        return {"decision": "WRONG_PASSWORD"}

    # ---------- SCORES ----------
    p = password_score(password_ok)
    i = ip_score(ip, history)
    t = time_score(login_time.isoformat(), history)
    l = location_score(
        user.latitude,
        user.longitude,
        history
    )

    partial_confidence = final_confidence(p, i, t, l, 0)

    # ---------- CREATE OTP SESSION ----------
    session_id = str(uuid.uuid4())
    expires_at = login_time + timedelta(minutes=5)

    supabase.table("otp_sessions").insert({
        "id": session_id,
        "email": user.email,
        "user_id": db_user["user_id"],
        "ip": ip,
        "latitude": user.latitude,
        "longitude": user.longitude,
        "mouse_speed": mouse_speed,
        "password_ok": password_ok,
        "p": p,
        "i": i,
        "t": t,
        "l": l,
        "m": m,
        "login_time": login_time.isoformat(),
        "expires_at": expires_at.isoformat()
    }).execute()

    # ---------- SEND OTP ----------
    generate_otp(user.email)

    return {
        "decision": "ENTER_OTP",
        "partial_confidence": partial_confidence,
        "session_id": session_id
    }

@app.get("/check-env")
def check_env():
    return {
        "EMAIL_USER": os.environ.get("EMAIL_USER", "NOT SET"),
        "EMAIL_PASS": "SET" if os.environ.get("EMAIL_PASS") else "NOT SET"
    }
# =====================================================
# OTP VERIFY
# =====================================================
@app.post("/verify-otp")
def verify_otp_login(data: OTPVerify):

    session_query = supabase.table("otp_sessions") \
        .select("*") \
        .eq("id", data.session_id) \
        .execute()

    if not session_query.data:
        return {"status": "SESSION_EXPIRED"}

    session = session_query.data[0]

    # ---------- CHECK EXPIRY ----------
    if datetime.fromisoformat(session["expires_at"]) < datetime.now(UTC):
        supabase.table("otp_sessions") \
            .delete() \
            .eq("id", data.session_id) \
            .execute()
        return {"status": "SESSION_EXPIRED"}

    # ---------- VERIFY OTP ----------
    if not verify_otp(data.email, data.otp):

        supabase.table("login_history").insert({
            "login_id": str(uuid.uuid4()),
            "user_id": session["user_id"],
            "login_time": session["login_time"],
            "ip_address": session["ip"],
            "latitude": session["latitude"],
            "longitude": session["longitude"],
            "password_correct": session["password_ok"],
            "otp_verified": False,
            "mouse_speed": session["mouse_speed"],
            "confidence_score": 0.2,
            "login_result": "BLOCK"
        }).execute()

        return {"status": "OTP_FAILED"}

    # ---------- LOAD SCORES ----------
    p = session["p"]
    i = session["i"]
    t = session["t"]
    l = session["l"]
    m = session["m"]

    # ---------- PRIOR ----------
    user_data = supabase.table("users") \
        .select("trust_score") \
        .eq("user_id", session["user_id"]) \
        .execute()

    if not user_data.data:
        return {"status": "USER_NOT_FOUND"}

    prior = user_data.data[0].get("trust_score", 0.5) or 0.5

    # ---------- LEARNING ----------
    history = supabase.table("login_history") \
        .select("*") \
        .eq("user_id", session["user_id"]) \
        .execute().data

    likelihood_model = learn_likelihoods(history)

    # ---------- BAYESIAN UPDATE ----------
    confidence = adaptive_posterior(
        prior,
        p,
        i,
        t,
        l,
        m,
        1,
        likelihood_model
    )

    safe_confidence = min(max(confidence, 0.05), 0.95)

    # ---------- UPDATE TRUST SCORE ----------
    supabase.table("users").update({
        "trust_score": safe_confidence
    }).eq(
        "user_id", session["user_id"]
    ).execute()

    # ---------- DECISION ----------
    if safe_confidence >= 0.85:
        decision = "ALLOW"
    elif safe_confidence >= 0.60:
        decision = "MONITOR"
    else:
        decision = "BLOCK"

    # ---------- ISSUE SESSION TOKEN IF ALLOWED ----------
    session_token = None
    if decision in ("ALLOW", "MONITOR"):
        session_token = str(uuid.uuid4())
        supabase.table("sessions").insert({
            "session_token": session_token,
            "user_id": session["user_id"],
            "email": data.email,
            "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat()
        }).execute()

    # ---------- STORE LOGIN ----------
    supabase.table("login_history").insert({
        "login_id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "login_time": session["login_time"],
        "ip_address": session["ip"],
        "latitude": session["latitude"],
        "longitude": session["longitude"],
        "password_correct": session["password_ok"],
        "otp_verified": True,
        "mouse_speed": session["mouse_speed"],
        "confidence_score": safe_confidence,
        "login_result": decision
    }).execute()

    # ---------- DELETE OTP SESSION ----------
    supabase.table("otp_sessions") \
        .delete() \
        .eq("id", data.session_id) \
        .execute()

    return {
        "message": decision,
        "confidence": safe_confidence,
        "session_token": session_token  # None if BLOCK
    }


