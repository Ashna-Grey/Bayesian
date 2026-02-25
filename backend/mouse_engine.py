import math
def extract_mouse_speed(mouse):
    if not mouse or len(mouse) < 5:
        return 0.5
    speeds = []
    for i in range(1, len(mouse)):
        dx = mouse[i]["x"] - mouse[i-1]["x"]
        dy = mouse[i]["y"] - mouse[i-1]["y"]
        dt = mouse[i]["t"] - mouse[i-1]["t"]
        if dt > 0:
            speed = math.sqrt(dx*dx + dy*dy) / dt
            speeds.append(speed)
    if not speeds:
        return 0.5
    return sum(speeds)/len(speeds)
def mouse_score(current_speed, history):
    past = [
        h.get("mouse_speed")
        for h in history
        if h.get("mouse_speed") is not None
    ]
    if not past:
        return 0.7   # learning phase
    baseline = sum(past)/len(past)
    diff = abs(current_speed - baseline)
    if diff < 0.02:
        return 1
    elif diff < 0.05:
        return 0.7
    else:
        return 0.3