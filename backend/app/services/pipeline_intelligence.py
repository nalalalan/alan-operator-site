from __future__ import annotations

from collections import Counter


def summarize_pipeline_patterns(records: list[dict]) -> dict:
    objections = Counter()
    missing_inputs = Counter()
    recommended_moves = Counter()

    for item in records:
        for obj in item.get("objections", []):
            if obj:
                objections[obj] += 1
        for missing in item.get("missing_inputs", []):
            if missing:
                missing_inputs[missing] += 1
        move = item.get("recommended_next_move")
        if move:
            recommended_moves[move] += 1

    return {
        "top_objections": objections.most_common(5),
        "top_missing_inputs": missing_inputs.most_common(5),
        "top_recommended_moves": recommended_moves.most_common(5),
    }
