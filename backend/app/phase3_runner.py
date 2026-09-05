"""
Phase 3 pipeline runner: builds the self-contained dashboard.html.

Run from backend/ directory:

    python -m app.phase3_runner --phase1-json ../data/phase1_results.json \\
        --phase2-json ../data/phase2_results.json \\
        --out ../frontend/dashboard.html
"""

import argparse
import json

from app.services.dashboard_builder import build_dashboard_html


def main():
    parser = argparse.ArgumentParser(description="Build the Phase 3 dashboard.html")
    parser.add_argument("--phase1-json", type=str, required=True)
    parser.add_argument("--phase2-json", type=str, required=True)
    parser.add_argument("--out", type=str, default="../frontend/dashboard.html")
    args = parser.parse_args()

    with open(args.phase1_json) as f:
        phase1_payload = json.load(f)
    with open(args.phase2_json) as f:
        phase2_payload = json.load(f)

    html = build_dashboard_html(phase1_payload, phase2_payload)
    with open(args.out, "w") as f:
        f.write(html)

    print(f"Dashboard written to {args.out} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
