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
from datetime import datetime, UTC
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_LOGIN = {}

# =====================================================
# REGISTER
# =====================================================
@app.post("/register")
def register(user: RegisterUser):

    user_id = str(uuid.uuid4())

    supabase.table("users").insert({
        "user_id": user_id,
        "email": user.email,
        "username": user.username,
        "password_hash": hash_password(user.password),
        "trust_score": 0.5
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

    login_time = datetime.now(UTC).isoformat()

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
            "login_time": login_time,
            "ip_address": ip,
            "latitude": user.latitude,
            "longitude": user.longitude,
            "password_correct": False,
            "otp_verified": False,
            "mouse_speed": mouse_speed,
            "confidence_score": 0.1,
            "login_result": "BLOCK"
        }).execute()

    # ---------- SCORES ----------
    p = password_score(password_ok)
    i = ip_score(ip, history)
    t = time_score(login_time, history)
    l = location_score(
        user.latitude,
        user.longitude,
        history
    )

    partial_confidence = final_confidence(p, i, t, l, 0)

    # ---------- OTP ----------
    generate_otp(user.email)

    TEMP_LOGIN[user.email] = {
        "scores": (p, i, t, l, m),
        "mouse_speed": mouse_speed,
        "user_id": db_user["user_id"],
        "ip": ip,
        "lat": user.latitude,
        "lon": user.longitude,
        "time": login_time,
        "password_ok": password_ok
    }

    return {
        "decision": "ENTER_OTP",
        "partial_confidence": partial_confidence
    }


# =====================================================
# OTP VERIFY
# =====================================================
@app.post("/verify-otp")
def verify_otp_login(data: OTPVerify):

    session = TEMP_LOGIN.get(data.email)

    if not verify_otp(data.email, data.otp):

        if session:
            supabase.table("login_history").insert({
                "login_id": str(uuid.uuid4()),
                "user_id": session["user_id"],
                "login_time": session["time"],
                "ip_address": session["ip"],
                "latitude": session["lat"],
                "longitude": session["lon"],
                "password_correct": session["password_ok"],
                "otp_verified": False,
                "mouse_speed": session["mouse_speed"],
                "confidence_score": 0.2,
                "login_result": "BLOCK"
            }).execute()

        return {"status": "OTP_FAILED"}

    if not session:
        return {"status": "SESSION_EXPIRED"}

    p, i, t, l, m = session["scores"]

    # ---------- PRIOR ----------
    user_data = supabase.table("users") \
        .select("trust_score") \
        .eq("user_id", session["user_id"]) \
        .execute()

    prior = user_data.data[0]["trust_score"] or 0.5

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

    # ---------- CLAMP ----------
    safe_confidence = min(max(confidence, 0.05), 0.95)

    supabase.table("users").update({
        "trust_score": safe_confidence
    }).eq(
        "user_id",
        session["user_id"]
    ).execute()

    # ---------- DECISION ----------
    if confidence >= 0.85:
        decision = "ALLOW"
    elif confidence >= 0.60:
        decision = "MONITOR"
    else:
        decision = "BLOCK"

    # ---------- STORE LOGIN ----------
    supabase.table("login_history").insert({
        "login_id": str(uuid.uuid4()),
        "user_id": session["user_id"],
        "login_time": session["time"],
        "ip_address": session["ip"],
        "latitude": session["lat"],
        "longitude": session["lon"],
        "password_correct": session["password_ok"],
        "otp_verified": True,
        "mouse_speed": session["mouse_speed"],
        "confidence_score": confidence,
        "login_result": decision
    }).execute()

    del TEMP_LOGIN[data.email]

    return {
        "message": decision,
        "confidence": confidence

    }
