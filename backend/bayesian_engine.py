import math
def prob_to_logodds(p):
    p = min(max(p, 0.05), 0.95)
    return math.log(p / (1 - p))
def logodds_to_prob(l):
    return 1 / (1 + math.exp(-l))
# ==================================================
# FINAL ADAPTIVE BAYESIAN POSTERIOR
# ==================================================
def adaptive_posterior(
        prior,
        p,
        i,
        t,
        l,
        m,      # mouse
        o,      # otp
        learned
):
    log_belief = prob_to_logodds(prior)
    evidence = {
        "password": p,
        "otp": o
    }
    for key in evidence:
        legit = learned[f"{key}_legit"]
        attack = learned[f"{key}_attack"]
        likelihood_ratio = legit / max(attack, 1e-6)
        EVIDENCE_WEIGHT = 0.25
        log_belief += EVIDENCE_WEIGHT * math.log(likelihood_ratio)
    # ------------------------------
    # ADD CONTINUOUS FEATURES
    # ------------------------------
    continuous = [i, t, l, m]
    for val in continuous:
        val = min(max(val, 0.01), 0.99)
        log_belief += 0.15 * math.log(
            (0.8 * val + 0.1) /
            (0.8 * (1 - val) + 0.1)
        )
    posterior = logodds_to_prob(log_belief)

    return round(posterior, 4)
