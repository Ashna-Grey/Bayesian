from datetime import datetime
import math
def password_score(correct):
    return 1 if correct else 0
def ip_score(ip, history):
    ips = [h["ip_address"] for h in history]
    count = ips.count(ip)
    if count >= 5:
        return 1
    elif count >= 2:
        return 0.8
    elif count == 1:
        return 0.6
    return 0.3
def time_score(current_time, history):
    if not history:
        return 1
    hours = [
        datetime.fromisoformat(
            h["login_time"]
        ).hour
        for h in history
    ]
    avg = sum(hours)/len(hours)
    curr = datetime.fromisoformat(current_time).hour
    diff = abs(curr-avg)
    if diff <= 1: return 1
    if diff <= 3: return 0.8
    if diff <= 6: return 0.5
    return 0.2
def location_score(lat, lon, history):
    coords = [
        (h["latitude"], h["longitude"])
        for h in history
        if h["latitude"]
    ]
    if not coords:
        return 1
    avg_lat = sum(c[0] for c in coords)/len(coords)
    avg_lon = sum(c[1] for c in coords)/len(coords)
    dist = math.sqrt(
        (lat-avg_lat)**2 +
        (lon-avg_lon)**2
    )
    if dist < 0.01: return 1
    if dist < 0.1: return 0.7
    return 0.3
def otp_score(verified):
    return 1 if verified else 0
def final_confidence(p,i,t,l,o):
    return (
        0.25*p +
        0.20*i +
        0.20*t +
        0.15*l +
        0.20*o
    )