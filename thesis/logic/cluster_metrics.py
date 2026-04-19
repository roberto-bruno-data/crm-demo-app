import numpy as np

def compute_cluster_score(cluster_pairs, cluster_size):

    if cluster_pairs.empty or cluster_size <= 1:
        return {
            "score": 0.0,
            "harmonic": 0.0,
            "mean": 0.0,
            "min": 0.0,
            "coverage": 0.0,
        }

    probs = cluster_pairs["prob"].values

    mean_prob = probs.mean()
    min_prob = probs.min()

    # harmonic mean (konservativ)
    if np.any(probs == 0):
        harmonic = 0.0
    else:
        harmonic = len(probs) / np.sum(1.0 / probs)

    # coverage
    max_pairs = cluster_size * (cluster_size - 1) / 2
    coverage = len(probs) / max_pairs if max_pairs > 0 else 0

    # 👉 kombinierter Score (leicht konservativ)
    score = harmonic * (0.5 + 0.5 * coverage)

    return {
        "score": score,
        "harmonic": harmonic,
        "mean": mean_prob,
        "min": min_prob,
        "coverage": coverage,
    }