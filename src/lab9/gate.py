"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def _rules(spec: dict) -> dict:
    rules = {m["id"]: {**m.get("threshold", {}), "blocking": m.get("blocking", False)}
             for m in spec.get("metrics", [])}
    for s in spec.get("slices", []):
        rules[f"slice:{s['name']}/{s['metric']}"] = s
    return rules


def _relaxed_rules(spec: dict, base_spec: dict) -> list[str]:
    problems = []
    current = _rules(spec)
    for name, old in _rules(base_spec).items():
        if name not in current:
            problems.append(f"removed {name}")
            continue
        new = current[name]
        for key in ("blocking", "no_significant_drop"):
            if old.get(key) and not new.get(key):
                problems.append(f"{name} disabled {key}")
        for key in ("min", "max", "max_increase"):
            if key not in old:
                continue
            value = new.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{name} missing or invalid {key}")
            elif (key == "min" and value < old[key]) or (key != "min" and value > old[key]):
                problems.append(f"{name} relaxed {key}")
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    rows = pr["rows"]
    manifest = pr["manifest"]
    seeds = manifest["seeds"]
    if pr.get("evaluator_failures"):
        problems.append("evaluator reported failures")
    metrics = pr.get("metrics", {})
    for name in set(metrics) | {m["id"] for m in spec["metrics"]}:
        value = metrics.get(name)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            problems.append(f"missing or non-finite metric {name}")

    reference = {(r["item_id"], r["seed"]): set(r.get("slices", [])) for r in base["rows"]}
    actual = {(r["item_id"], r["seed"]) for r in rows}
    if len(rows) != manifest["items"] * len(seeds) or len(actual) != len(rows):
        problems.append("incorrect row count or duplicate item/seed")
    if (actual != reference.keys() or set(seeds) != set(base["manifest"]["seeds"])
            or len(set(seeds)) != len(seeds) or manifest["items"] != base["manifest"]["items"]):
        problems.append("item/seed coverage differs from baseline")
    graded = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]
    for row in rows:
        key = row["item_id"], row["seed"]
        if key in reference and set(row.get("slices", [])) != reference[key]:
            problems.append(f"slice tags differ at {key}")
        for name in graded:
            if not isinstance(row.get(name), bool):
                problems.append(f"missing or invalid {name} at {key}")
    if base_spec is not None and base_spec.get("eval_set_version") == spec.get("eval_set_version"):
        problems.extend(_relaxed_rules(spec, base_spec))
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    # TODO M5
    blocked = []
    lines = []
    bootstrap = spec.get("bootstrap", {})

    for rule in spec.get("slices", []):
        name = rule["name"]
        metric = rule["metric"]
        label = f"slice:{name}/{metric}"

        current = per_item(pr, metric, slice_name=name)
        baseline = per_item(base, metric, slice_name=name)
        reasons = []

        if not current or current.keys() != baseline.keys():
            reasons.append("missing or mismatched items")
            detail = f"PR items={len(current)}, baseline items={len(baseline)}"
        else:
            item_ids = sorted(current)
            a = [current[item] for item in item_ids]
            b = [baseline[item] for item in item_ids]
            value = sum(a) / len(a)
            detail = f"mean={value:.3f}, items={len(a)}"

            if "min" in rule and value < rule["min"]:
                reasons.append(f"below floor {rule['min']:.3f}")

            if rule.get("no_significant_drop"):
                if len(a) == 1:
                    # Một item chỉ tạo được một chênh lệch khi lấy mẫu lại.
                    delta = lo = hi = a[0] - b[0]
                else:
                    delta, lo, hi = stats.paired_bootstrap(
                        a, b,
                        n_resamples=bootstrap.get("n_resamples", 1000),
                        rng=bootstrap.get("rng", 2027),
                        confidence=bootstrap.get("confidence", 0.95),
                    )
                detail += f", delta={delta:+.3f}, CI=[{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    reasons.append("significant drop")

        verdict = "ok"
        if reasons:
            verdict = "warn"
            if rule.get("blocking"):
                blocked.append(label)
                verdict = "BLOCK"
            detail += ", " + ", ".join(reasons)

        lines.append(f"  {label} {detail} {verdict}")

    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
