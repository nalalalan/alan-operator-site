from __future__ import annotations

import json
from pathlib import Path

from app.schemas.revenue_ops import BuyerRequestIn, CallContext
from app.services.buyer_fit import score_buyer_fit
from app.services.premium_operator import build_premium_packet
from app.workers.buyer_engine import draft_buyer_engine_row

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "scripts" / "premium_fixtures.json"
OUT = ROOT / "scripts" / "premium_dry_run_output.json"


def run_dry_run() -> dict:
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    out = {"buyers": [], "packets": []}

    for buyer in data.get("buyers", []):
        buyer_in = BuyerRequestIn(**buyer)
        out["buyers"].append(draft_buyer_engine_row(buyer_in))

    for packet_case in data.get("packets", []):
        ctx = CallContext(**packet_case)
        out["packets"].append(build_premium_packet(ctx))

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    result = run_dry_run()
    print(json.dumps(result, indent=2, ensure_ascii=False))
