import math

CONDITION_TO_RANK = {
    "Very Poor": 0,
    "Poor": 1,
    "Fair": 2,
    "Good": 3,
    "Excellent": 4,
}
RANK_TO_CONDITION = {v: k for k, v in CONDITION_TO_RANK.items()}


def condition_rank(value: str) -> int | None:
    v = (value or "").strip()
    if not v or v in ("Not Applicable", "N/A"):
        return None
    return CONDITION_TO_RANK.get(v)


def worst_condition(values: list[str]) -> str:
    ranks = [r for v in values if (r := condition_rank(v)) is not None]
    if not ranks:
        return ""
    return RANK_TO_CONDITION[min(ranks)]


def average_condition(values: list[str]) -> str:
    ranks = [r for v in values if (r := condition_rank(v)) is not None]
    if not ranks:
        return ""
    mean = sum(ranks) / len(ranks)
    nearest = max(0, min(4, int(math.floor(mean + 0.5))))
    return RANK_TO_CONDITION[nearest]


def aggregate_doors(values: list[str], method: str = "average") -> str:
    if method == "worst":
        return worst_condition(values)
    return average_condition(values)
