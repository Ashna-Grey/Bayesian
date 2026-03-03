import math

def prob_to_logodds(p):
    p = min(max(p, 0.05), 0.95)
    return math.log(p / (1 - p))

def logodds_to_prob(l):
    return 1 / (1 + math.exp(-l))

def adaptive_posterior(prior, p, i, t, l, m, o, learned):

    log_belief = prob_to_logodds(prior)

    evidence = {
        "password": p,
        "otp": o
    }

    for key in evidence:
        legit = learned.get(f"{key}_legit", 0.5)
        attack = learned.get(f"{key}_attack", 0.5)

        if attack == 0:
            attack = 0.01

        likelihood_ratio = legit / attack
        log_belief += 0.25 * math.log(likelihood_ratio)

    continuous = [i, t, l, m]

    for val in continuous:
        val = min(max(val, 0.01), 0.99)
        log_belief += 0.15 * math.log(
            (0.8 * val + 0.1) /
            (0.8 * (1 - val) + 0.1)
        )

    return round(logodds_to_prob(log_belief), 4)
