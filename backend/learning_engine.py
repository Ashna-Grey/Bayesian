def safe_prob(num, den):
    if den == 0:
        return 0.5
    return (num + 1) / (den + 2)   # Laplace smoothing


def learn_likelihoods(history):

    legit = [
        h for h in history
        if h.get("login_result") == "ALLOW"
    ]

    attack = [
        h for h in history
        if h.get("login_result") == "BLOCK"
    ]

    L = len(legit)
    A = len(attack)

    model = {}

    # ---------------- PASSWORD ----------------
    model["password_legit"] = safe_prob(
        sum(1 for h in legit if h.get("password_correct")),
        L
    )

    model["password_attack"] = safe_prob(
        sum(1 for h in attack if h.get("password_correct")),
        A
    )

    # ---------------- OTP ----------------
    model["otp_legit"] = safe_prob(
        sum(1 for h in legit if h.get("otp_verified")),
        L
    )

    model["otp_attack"] = safe_prob(
        sum(1 for h in attack if h.get("otp_verified")),
        A
    )

    return model