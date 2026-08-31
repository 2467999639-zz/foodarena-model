"""Validate inputs, enforce constraints, then rank eligible meals."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURES = ["affordability", "rating", "speed", "cuisine_match", "spice_match"]
LABELS = ["预算余量", "菜品评分", "等待时间", "菜系偏好", "辣度偏好"]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def number(value, field, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(field + " must be a number")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(field + " is out of range")
    return value


def strings(value, field):
    if not isinstance(value, list) or len(value) > 100:
        raise ValueError(field + " must be a list of at most 100 strings")
    if any(not isinstance(v, str) or not v.strip() or len(v) > 100 for v in value):
        raise ValueError(field + " contains an invalid string")
    return [v.strip().casefold() for v in value]


def profile(raw):
    if not isinstance(raw, dict):
        raise ValueError("profile must be an object")
    allowed = {"budget", "max_spice", "preferred_spice", "vegetarian", "allergens", "disliked_ingredients", "preferred_cuisines"}
    if set(raw) - allowed:
        raise ValueError("unknown profile fields: " + ", ".join(sorted(set(raw) - allowed)))
    budget = number(raw.get("budget"), "budget", 0.01, 10000)
    maximum = number(raw.get("max_spice", 3), "max_spice", 0, 3)
    preferred = number(raw.get("preferred_spice", maximum), "preferred_spice", 0, maximum)
    vegetarian = raw.get("vegetarian", False)
    if not isinstance(vegetarian, bool):
        raise ValueError("vegetarian must be a boolean")
    return dict(budget=budget, max_spice=maximum, preferred_spice=preferred,
                vegetarian=vegetarian,
                allergens=strings(raw.get("allergens", []), "allergens"),
                disliked_ingredients=strings(raw.get("disliked_ingredients", []), "disliked_ingredients"),
                preferred_cuisines=strings(raw.get("preferred_cuisines", []), "preferred_cuisines"))


def dishes(raw):
    if not isinstance(raw, list) or len(raw) > 500:
        raise ValueError("dishes must be a list with at most 500 items")
    result, ids = [], set()
    for dish in raw:
        if not isinstance(dish, dict):
            raise ValueError("each dish must be an object")
        item = dict(dish)
        for key in ("id", "name", "cuisine"):
            if not isinstance(item.get(key), str) or not item[key].strip() or len(item[key]) > 100:
                raise ValueError("dish " + key + " must be a nonempty string")
        if item["id"] in ids:
            raise ValueError("duplicate dish id")
        ids.add(item["id"])
        for key, lo, hi in [("price", 0, 10000), ("rating", 0, 5), ("wait_minutes", 0, 240), ("spice", 0, 3)]:
            number(item.get(key), key, lo, hi)
        for key in ("vegetarian", "available", "allergens_verified"):
            if not isinstance(item.get(key), bool):
                raise ValueError("dish " + key + " must be a boolean")
        for key in ("allergens", "ingredients"):
            item[key] = strings(item.get(key), key)
        if not item["ingredients"]:
            raise ValueError("dish ingredients must not be empty")
        item["cuisine"] = item["cuisine"].strip().casefold()
        result.append(item)
    return result


def exclusions(user, dish):
    reasons = []
    if not dish["available"]:
        reasons.append("已售罄")
    if dish["price"] > user["budget"]:
        reasons.append("超出预算")
    if dish["spice"] > user["max_spice"]:
        reasons.append("超过辣度上限")
    if user["vegetarian"] and not dish["vegetarian"]:
        reasons.append("不符合素食要求")
    if user["allergens"]:
        if not dish["allergens_verified"]:
            reasons.append("过敏原信息未核实")
        if set(user["allergens"]) & set(dish["allergens"] + dish["ingredients"]):
            reasons.append("包含需避开的过敏原")
    if set(user["disliked_ingredients"]) & set(dish["ingredients"]):
        reasons.append("包含忌口食材")
    return reasons


def features(user, dish):
    cuisines = user["preferred_cuisines"]
    return [max(-1, 1 - dish["price"] / user["budget"]),
            dish["rating"] / 5,
            1 - min(dish["wait_minutes"], 60) / 60,
            float(dish["cuisine"] in cuisines) if cuisines else 0,
            1 - abs(dish["spice"] - user["preferred_spice"]) / 3]


def load_model(path=None):
    model = read_json(path or ROOT / "models" / "baseline.json")
    if model.get("features") != FEATURES or model.get("model_type") != "pairwise-logistic-linear":
        raise ValueError("incompatible model artifact")
    weights = model.get("weights")
    if not isinstance(weights, list) or len(weights) != len(FEATURES):
        raise ValueError("invalid model weights")
    for weight in weights:
        number(weight, "model weight", -1000, 1000)
    return model


def recommend(request, model=None):
    if not isinstance(request, dict) or set(request) - {"profile", "dishes", "top_k"}:
        raise ValueError("request must contain only profile, dishes and top_k")
    user = profile(request.get("profile"))
    menu = dishes(request.get("dishes", read_json(ROOT / "data" / "menu.sample.json")))
    top_k = request.get("top_k", 3)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 20:
        raise ValueError("top_k must be an integer from 1 to 20")
    model = model or load_model()
    ranked, excluded = [], []
    for dish in menu:
        blocked = exclusions(user, dish)
        if blocked:
            excluded.append({"id": dish["id"], "name": dish["name"], "reasons": blocked})
            continue
        values = features(user, dish)
        contributions = [v * w for v, w in zip(values, model["weights"])]
        ranked.append({"id": dish["id"], "name": dish["name"], "price": dish["price"],
                       "score": round(sum(contributions), 6),
                       "explanation": [{"feature": key, "label": label, "value": round(value, 4),
                                        "contribution": round(contribution, 4)}
                                       for key, label, value, contribution in zip(FEATURES, LABELS, values, contributions)]})
    ranked.sort(key=lambda item: (-item["score"], item["price"], item["id"]))
    return {"status": "ok" if ranked else "no_match", "model_version": model["version"],
            "recommendations": ranked[:top_k], "excluded": excluded,
            "notice": "合成数据演示基线；分数不是满意概率。食材信息和交叉接触风险需向商家核实。"}
