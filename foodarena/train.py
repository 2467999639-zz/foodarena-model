"""Reproducible pairwise learning from synthetic or consented preferences."""

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

from .ranker import ROOT, FEATURES, dishes, exclusions, features, profile, read_json


def sigmoid(x):
    return 1 / (1 + math.exp(-max(-40, min(40, x))))


def synthetic_pairs(seed=42, count=1200):
    rng = random.Random(seed)
    menu = dishes(read_json(ROOT / "data" / "menu.sample.json"))
    teacher = [1.5, 2.2, 1.0, 2.0, 1.2]
    result = []
    while len(result) < count:
        maximum = rng.randint(0, 3)
        user = profile({"budget": rng.choice([15, 18, 22, 30]), "max_spice": maximum,
                        "preferred_spice": rng.randint(0, maximum),
                        "preferred_cuisines": rng.choice([[], ["中式"], ["面食"], ["轻食"]])})
        candidates = [dish for dish in menu if not exclusions(user, dish)]
        if len(candidates) < 2:
            continue
        left, right = rng.sample(candidates, 2)
        delta = [a - b for a, b in zip(features(user, left), features(user, right))]
        probability = sigmoid(3 * sum(w * x for w, x in zip(teacher, delta)))
        label = int(rng.random() < probability)
        result.append({"profile": user, "left": left, "right": right, "preferred": "left" if label else "right"})
    return result


def examples(rows):
    if not isinstance(rows, list) or len(rows) < 20:
        raise ValueError("training requires at least 20 preference pairs")
    result = []
    for row in rows:
        user = profile(row["profile"])
        left, right = dishes([row["left"], row["right"]])
        if exclusions(user, left) or exclusions(user, right):
            raise ValueError("training pairs must both pass hard constraints")
        if row.get("preferred") not in ("left", "right"):
            raise ValueError("preferred must be left or right")
        delta = [a - b for a, b in zip(features(user, left), features(user, right))]
        result.append((delta, int(row["preferred"] == "left")))
    return result


def train(rows, seed=42, epochs=180):
    data = examples(rows)
    random.Random(seed).shuffle(data)
    split = max(1, int(len(data) * 0.8))
    training, validation = data[:split], data[split:]
    weights = [0.0] * len(FEATURES)
    for _ in range(epochs):
        gradient = [0.0] * len(weights)
        for vector, label in training:
            error = sigmoid(sum(w * x for w, x in zip(weights, vector))) - label
            for j, value in enumerate(vector):
                gradient[j] += error * value
        weights = [w - 0.8 * (g / len(training) + 0.001 * w) for w, g in zip(weights, gradient)]
    probabilities = [sigmoid(sum(w * x for w, x in zip(weights, vector))) for vector, _ in validation]
    accuracy = sum(int(p >= 0.5) == label for p, (_, label) in zip(probabilities, validation)) / len(validation)
    loss = -sum(label * math.log(max(p, 1e-12)) + (1 - label) * math.log(max(1 - p, 1e-12))
                for p, (_, label) in zip(probabilities, validation)) / len(validation)
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    model = {"version": "0.1.0", "model_type": "pairwise-logistic-linear", "features": FEATURES,
             "weights": weights, "seed": seed, "epochs": epochs, "data_sha256": digest}
    metrics = {"train_pairs": len(training), "validation_pairs": len(validation),
               "pairwise_accuracy": round(accuracy, 4), "log_loss": round(loss, 4),
               "split": "seeded random pair split; use user/time split for real data", "seed": seed}
    return model, metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, help="JSON array of preference pairs; omit for synthetic demo")
    parser.add_argument("--output", type=Path, default=ROOT / "models" / "baseline.json")
    parser.add_argument("--metrics", type=Path, default=ROOT / "reports" / "metrics.json")
    args = parser.parse_args()
    rows = read_json(args.data) if args.data else synthetic_pairs()
    model, metrics = train(rows)
    source = "user-provided; not independently verified" if args.data else "synthetic-demo"
    model["data_source"] = metrics["data_source"] = source
    for path, payload in [(args.output, model), (args.metrics, metrics)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
