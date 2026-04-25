from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass
class MemoryState:
    repeated_problems: list[str]
    repeated_missing_inputs: list[str]
    prior_next_steps: list[str]
    commercial_direction: str


def build_deal_memory(call_summaries: list[dict]) -> MemoryState:
    problem_counter: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()
    next_steps: list[str] = []

    for item in call_summaries:
        for problem in item.get("problems", []):
            if problem:
                problem_counter[problem] += 1
        for missing in item.get("missing_inputs", []):
            if missing:
                missing_counter[missing] += 1
        if item.get("next_step"):
            next_steps.append(item["next_step"])

    repeated_problems = [k for k, _ in problem_counter.most_common(3)]
    repeated_missing = [k for k, _ in missing_counter.most_common(5)]

    commercial_direction = "Hold on clear proposal until missing inputs are resolved."
    if repeated_problems:
        commercial_direction = "Use the repeated problems to frame the next recommended scope."

    return MemoryState(
        repeated_problems=repeated_problems,
        repeated_missing_inputs=repeated_missing,
        prior_next_steps=next_steps[-5:],
        commercial_direction=commercial_direction,
    )
