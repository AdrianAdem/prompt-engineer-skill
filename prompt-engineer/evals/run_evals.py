#!/usr/bin/env python3
"""Run the eval cases in evals.json and check the outputs against expectations.

What this can and cannot do, stated up front because the distinction matters:

CAN check whether the skill, once applied, produces the right *kind* of answer.
Each case carries machine-checkable assertions (must_contain, must_not_contain,
must_produce_files) derived from its expected_output.

CANNOT check triggering. Whether a skill activates on a given phrasing is a
property of the harness that loads it, not of the model. There is no API call
that reproduces it. Cases marked "triggering": true are printed as a manual
checklist instead of being run, and they are the more important half.

Usage:
    export ANTHROPIC_API_KEY=...
    python evals/run_evals.py                       # run automatable cases
    python evals/run_evals.py --manual              # print the manual checklist
    python evals/run_evals.py --model claude-opus-5
    python evals/run_evals.py --case 2
    python evals/run_evals.py --dry-run             # show prompts, call nothing
"""
import argparse
import json
import os
import signal
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SKILL = ROOT.parent / "SKILL.md"
API = "https://api.anthropic.com/v1/messages"


def load_skill():
    text = SKILL.read_text()
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.strip()


def call(model, system, prompt, max_tokens=4000):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "content-type": "application/json",
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    return "".join(b.get("text", "") for b in data.get("content", []))


def check(case, output):
    """Return (passed, [failure descriptions])."""
    problems = []
    low = output.lower()
    for pattern in case.get("must_contain", []):
        if not re.search(pattern, low, re.I):
            problems.append(f"missing: {pattern}")
    for pattern in case.get("must_not_contain", []):
        if re.search(pattern, low, re.I):
            m = re.search(pattern, low, re.I)
            problems.append(f"present but should not be: {pattern} ({m.group(0)[:40]})")
    lo, hi = case.get("word_range", [0, 10**9])
    words = len(output.split())
    if not lo <= words <= hi:
        problems.append(f"length {words} words, expected {lo} to {hi}")
    return (not problems), problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-4-5")
    ap.add_argument("--case", type=int, help="run a single case by id")
    ap.add_argument("--manual", action="store_true", help="print the manual checklist only")
    ap.add_argument("--dry-run", action="store_true", help="print prompts, make no calls")
    args = ap.parse_args()

    spec = json.loads((ROOT / "evals.json").read_text())
    cases = spec["evals"]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]

    manual = [c for c in cases if c.get("triggering")]
    auto = [c for c in cases if not c.get("triggering")]

    if args.manual or not auto:
        print("Manual checklist: triggering cannot be tested through the API.")
        print("Open a fresh session with the skill installed, paste each prompt,")
        print("and record whether the skill loaded before anything else happened.\n")
        for c in manual:
            print(f"[{c['id']}] {c['prompt']}")
            print(f"     expect: {c['expected_output']}\n")
        if args.manual:
            return 0

    if args.dry_run:
        for c in auto:
            print(f"--- case {c['id']} ---\n{c['prompt']}\n")
        return 0

    if "ANTHROPIC_API_KEY" not in os.environ:
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2

    system = load_skill()
    failed = 0
    for c in auto:
        try:
            out = call(args.model, system, c["prompt"])
        except urllib.error.HTTPError as e:
            print(f"[{c['id']}] ERROR {e.code}: {e.read()[:200].decode(errors='replace')}")
            failed += 1
            continue
        ok, problems = check(c, out)
        print(f"[{c['id']}] {'PASS' if ok else 'FAIL'}  {c['prompt'][:60]}...")
        for p in problems:
            print(f"      {p}")
        if not ok:
            failed += 1
            (ROOT / f"out_{c['id']}.txt").write_text(out)
            print(f"      full output written to evals/out_{c['id']}.txt")

    print(f"\n{len(auto) - failed}/{len(auto)} automatable cases passed.")
    if manual:
        print(f"{len(manual)} triggering case(s) still need a manual run: --manual")
    return 1 if failed else 0


if __name__ == "__main__":
    # Piping into head sends SIGPIPE; die quietly rather than with a traceback.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
