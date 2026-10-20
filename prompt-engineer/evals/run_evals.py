#!/usr/bin/env python3
"""Run the eval cases in evals/<case>/ through the API and grade them.

The cases are written for `claude plugin eval`, and that is the better runner
when you have Claude Code: it loads the skill the way a session does, so it can
see whether the skill triggered, and it runs a baseline arm without the skill,
so the number you get is the difference the skill makes. This script is for
everyone else, and for quick checks that should not start an agent. Both read
the same case files, so there is one eval set, not two that drift apart.

What it can and cannot do, stated up front because the distinction matters:

CAN grade what the skill produces once applied. `regex` graders run here, in
code. `llm` graders go to a second model, one verdict per criterion.

CANNOT see triggering. Whether a skill activates is decided by the harness that
loads it, and no API call reproduces that, so `tool_used` graders are skipped
and listed rather than faked. The system prompt is the whole skill flattened
into one block, as if every reference had been read; `--core` sends SKILL.md
alone, which is the other end of what a real session sees.

Usage:
    export ANTHROPIC_API_KEY=...
    python evals/run_evals.py                      # every case, one run each
    python evals/run_evals.py --case 02 --runs 3   # one case, three samples
    python evals/run_evals.py --dry-run            # list cases and graders, call nothing
    python evals/run_evals.py --manual             # triggering checklist for a human
    python evals/run_evals.py --self-test          # parsing and grading logic, offline
"""
import argparse
import fnmatch
import importlib.util
import json
import os
import pathlib
import re
import signal
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SKILL_ROOT = ROOT.parent
RESULTS = ROOT / "results" / "api"
API = "https://api.anthropic.com/v1/messages"

# On models where thinking always runs, max_tokens covers thinking plus the
# answer. A budget sized for the answer alone truncates it, and the truncated
# text then fails a grader for a reason that has nothing to do with the skill.
GEN_MAX_TOKENS = 32000
GRADE_MAX_TOKENS = 8000
EFFORTS = ["low", "medium", "high", "xhigh", "max"]


# ---------------------------------------------------------------- case files

def parse_frontmatter(text):
    """Return (dict, body) for a Markdown file with a simple YAML header.

    Handles exactly what the case files use: scalars, quoted strings, ints and
    one-line lists. Standard library only, so the script runs anywhere.
    """
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            header, body = text[3:end], text[end + 4:]
            for raw in header.splitlines():
                if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
                    continue
                key, value = raw.split(":", 1)
                meta[key.strip()] = _scalar(value.strip())
    return meta, body.strip()


def _scalar(value):
    if value.startswith("[") and value.endswith("]"):
        return [_scalar(v.strip()) for v in value[1:-1].split(",") if v.strip()]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if value in ("true", "false"):
        return value == "true"
    return value


def load_cases(root=ROOT):
    cases = []
    for d in sorted(p for p in root.iterdir() if (p / "prompt.md").is_file()):
        meta, prompt = parse_frontmatter((d / "prompt.md").read_text())
        graders = []
        for g in sorted((d / "graders").glob("*.md")):
            fm, body = parse_frontmatter(g.read_text())
            graders.append(dict(fm, name=g.stem, body=body))
        cases.append({"id": d.name, "meta": meta, "prompt": prompt, "graders": graders})
    return cases


def select(cases, pattern):
    if not pattern:
        return cases
    glob = pattern if any(c in pattern for c in "*?[") else pattern + "*"
    return [c for c in cases if fnmatch.fnmatch(c["id"], glob)]


def is_negative(case):
    return any(g.get("type") == "tool_used" and g.get("max") == 0 for g in case["graders"])


# ------------------------------------------------------------------- grading

JS_FLAGS = {"i": re.I, "m": re.M, "s": re.S}


def grade_regex(g, output):
    """Mirror `claude plugin eval` regex semantics on the final message."""
    if g.get("target", "last_message") != "last_message":
        return None, "target other than last_message needs claude plugin eval"
    flags = 0
    for f in str(g.get("flags", "")):
        flags |= JS_FLAGS.get(f, 0)
    hits = len(re.findall(g["body"], output, flags))
    match = str(g.get("match", "contains"))
    if match == "contains":
        return hits > 0, f"{hits} match(es)"
    if match == "not_contains":
        return hits == 0, f"{hits} match(es)"
    if match.startswith("count:"):
        want = int(match.split(":", 1)[1])
        return hits == want, f"{hits} match(es), wanted {want}"
    return None, f"unknown match mode {match}"


GRADER_SYSTEM = """You grade one response against numbered criteria. You did not write
the response and you are not being asked to improve it.

For each criterion, write PASS or FAIL, then one sentence of evidence pointing at
the part of the response that decided it. Judge what the response does, not the
words it uses: a response that hands schema enforcement to a tool definition has
met a criterion about API-level enforcement even if it never uses that phrase.

Output one line per criterion, in order, formatted exactly:
<n>. PASS|FAIL - <evidence>
Nothing else."""

VERDICT_RE = re.compile(r"^\s*(\d+)\.\s*[*_`]*\s*(PASS|FAIL)\b", re.M | re.I)


def parse_verdicts(text, n):
    """Map criterion number to True/False. Missing numbers count as FAIL."""
    found = {int(num): word.upper() == "PASS" for num, word in VERDICT_RE.findall(text)}
    return [found.get(i, False) for i in range(1, n + 1)]


# ----------------------------------------------------------------------- API

class StopError(Exception):
    """The model stopped for a reason other than finishing its answer."""


def call(model, system, prompt, effort, max_tokens):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "output_config": {"effort": effort},
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "content-type": "application/json",
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.load(r)
    stop = data.get("stop_reason")
    # Thinking blocks can come first and carry empty text; read by block type.
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    # A refusal arrives as HTTP 200 with little or no text. Grading it would
    # report a bad answer and send you tuning a prompt that was never the problem.
    if stop == "refusal":
        category = (data.get("stop_details") or {}).get("category", "unspecified")
        raise StopError(f"refusal ({category})")
    if stop == "max_tokens":
        raise StopError(f"truncated at max_tokens={max_tokens}; raise the budget")
    # Some models occasionally put the whole answer in the thinking and return
    # no visible text. Grading an empty string would blame the skill for it.
    if not text.strip():
        raise StopError(f"empty reply (stop_reason {stop}); the answer may be in the thinking")
    return text


def load_skill(core):
    spec = importlib.util.spec_from_file_location(
        "build_system_prompt", SKILL_ROOT / "scripts" / "build_system_prompt.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build(core=core)


def run_case(case, args, system):
    """One sample of one case. Returns (passed, weighted_score, lines)."""
    out = call(args.model, system, case["prompt"], args.effort, GEN_MAX_TOKENS)
    lines, total, earned, all_pass = [], 0.0, 0.0, True

    llm = [g for g in case["graders"] if g.get("type") == "llm"]
    verdicts = []
    if llm:
        items = "\n".join(f"{i}. {g['body']}" for i, g in enumerate(llm, 1))
        prompt = (f"CRITERIA:\n{items}\n\nREQUEST THE RESPONSE WAS ANSWERING:\n"
                  f"{case['prompt']}\n\nRESPONSE:\n{out}")
        try:
            raw = call(args.grader, GRADER_SYSTEM, prompt, args.grader_effort, GRADE_MAX_TOKENS)
        except (StopError, urllib.error.URLError, OSError):
            save(case, out, ["grading failed; response saved for a rerun"])
            raise
        verdicts = parse_verdicts(raw, len(llm))
        evidence = {int(m.group(1)): m.group(0).strip()
                    for m in re.finditer(r"^\s*(\d+)\..*$", raw, re.M)}

    for g in case["graders"]:
        kind, weight = g.get("type"), float(g.get("weight", 1))
        if kind == "regex":
            ok, note = grade_regex(g, out)
        elif kind == "llm":
            i = llm.index(g) + 1
            ok, note = verdicts[i - 1], evidence.get(i, "no verdict line")
        else:
            lines.append(f"      skip  {g['name']} ({kind}: needs claude plugin eval)")
            continue
        if ok is None:
            lines.append(f"      skip  {g['name']} ({note})")
            continue
        total += weight
        earned += weight if ok else 0
        all_pass = all_pass and ok
        lines.append(f"      {'pass' if ok else 'FAIL'}  {g['name']}: {note[:140]}")

    if not all_pass:
        save(case, out, lines)
    return all_pass, (earned / total if total else 1.0), lines


def save(case, output, lines):
    RESULTS.mkdir(parents=True, exist_ok=True)
    n = len(list(RESULTS.glob(f"{case['id']}-*.txt"))) + 1
    path = RESULTS / f"{case['id']}-{n}.txt"
    path.write_text(output + "\n\n---- graders ----\n" + "\n".join(lines) + "\n")
    shown = path.relative_to(SKILL_ROOT) if path.is_relative_to(SKILL_ROOT) else path
    lines.append(f"      response written to {shown}")


# ------------------------------------------------------------------ self-test

def self_test():
    """Exercise parsing and grading offline, and check the suite's floor rules."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        status = "ok" if got == want else "FAIL"
        ok = ok and got == want
        print(f"  {label:<44} {status}")

    meta, body = parse_frontmatter(
        "---\nmax_turns: 15\nallowed_tools: [Skill, Read]\nflags: \"i\"\n---\n\nHello there.\n")
    check("frontmatter: int", meta.get("max_turns"), 15)
    check("frontmatter: list", meta.get("allowed_tools"), ["Skill", "Read"])
    check("frontmatter: quoted string", meta.get("flags"), "i")
    check("frontmatter: body", body, "Hello there.")

    g = {"body": r"\{\{[A-Za-z_]+\}\}", "match": "contains", "flags": "i"}
    check("regex contains: hit", grade_regex(g, "uses {{ticket_text}}")[0], True)
    check("regex contains: miss", grade_regex(g, "no placeholders")[0], False)
    g = {"body": "respond only in valid json", "match": "not_contains", "flags": "i"}
    check("regex not_contains: hit fails", grade_regex(g, "Respond only in valid JSON.")[0], False)
    g = {"body": "x", "match": "count:2", "flags": ""}
    check("regex count:2", grade_regex(g, "x and x")[0], True)

    check("verdicts: plain", parse_verdicts("1. PASS - a\n2. FAIL - b", 2), [True, False])
    check("verdicts: bold and lowercase", parse_verdicts("1. **pass** - a\n2. **FAIL** - b", 2), [True, False])
    check("verdicts: missing line counts as fail", parse_verdicts("1. PASS - a", 2), [True, False])

    # Floor rules for the suite itself, the same ones `claude plugin eval`
    # authoring enforces: a negative case exists, every case has an outcome
    # grader beyond the trigger check, and every case asks for three runs.
    cases = load_cases()
    check("suite: has cases", len(cases) > 0, True)
    check("suite: at least one should-not-fire case", any(is_negative(c) for c in cases), True)
    for c in cases:
        outcome = [g for g in c["graders"] if g.get("type") in ("regex", "llm", "file_exists")]
        check(f"{c['id'][:30]}: outcome grader", len(outcome) > 0, True)
        check(f"{c['id'][:30]}: runs >= 3", c["meta"].get("runs", 0) >= 3, True)
        check(f"{c['id'][:30]}: prompt not empty", bool(c["prompt"]), True)
        for g in c["graders"]:
            if g.get("type") == "regex":
                try:
                    re.compile(g["body"])
                    good = True
                except re.error:
                    good = False
                check(f"{c['id'][:22]}/{g['name'][:18]}: regex compiles", good, True)

    print("self-test passed" if ok else "self-test FAILED")
    return 0 if ok else 1


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5-5",
                    help="model that produces the responses")
    ap.add_argument("--grader", default="claude-opus-5-5",
                    help="model that grades them; keep it different from --model, "
                         "because a model grading its own output is measuring itself")
    ap.add_argument("--effort", choices=EFFORTS, default="high",
                    help="pinned for the run, because an unpinned effort setting is an "
                         "unknown class and defaults differ between models")
    ap.add_argument("--grader-effort", choices=EFFORTS, default="medium")
    ap.add_argument("--runs", type=int, default=1,
                    help="samples per case; one is a smoke test, three is the floor for a claim")
    ap.add_argument("--case", help="case id, prefix, or glob, e.g. 02 or '0[1-3]*'")
    ap.add_argument("--core", action="store_true",
                    help="send SKILL.md alone instead of the skill with every reference")
    ap.add_argument("--manual", action="store_true", help="print the triggering checklist only")
    ap.add_argument("--dry-run", action="store_true", help="list cases and graders, make no calls")
    ap.add_argument("--self-test", action="store_true",
                    help="check parsing, grading logic and the suite's floor rules offline")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    cases = select(load_cases(), args.case)
    if not cases:
        print(f"no case matches {args.case!r}", file=sys.stderr)
        return 2

    if args.manual:
        print("Triggering checklist. `claude plugin eval` checks this automatically; by hand,")
        print("open a fresh session with the skill installed, paste each prompt, and note")
        print("whether the skill loaded before anything else happened.\n")
        for c in cases:
            print(f"[{c['id']}] {'must NOT load' if is_negative(c) else 'must load'}")
            print(f"     {c['prompt']}\n")
        return 0

    if args.dry_run:
        for c in cases:
            kinds = ", ".join(f"{g['name']} ({g.get('type')})" for g in c["graders"])
            print(f"--- {c['id']} ---\n{c['prompt']}\n  graders: {kinds}\n")
        return 0

    if "ANTHROPIC_API_KEY" not in os.environ:
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2

    system = load_skill(args.core)
    print(f"model {args.model} at {args.effort}, grader {args.grader} at {args.grader_effort}, "
          f"{'SKILL.md only' if args.core else 'full skill'}, {args.runs} run(s) per case\n")
    failed = 0
    for c in cases:
        passes, scores = 0, []
        for n in range(1, args.runs + 1):
            try:
                ok, score, lines = run_case(c, args, system)
            except StopError as e:
                print(f"[{c['id']}] run {n}: STOPPED: {e}")
                continue
            except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
                detail = e.read()[:200].decode(errors="replace") if hasattr(e, "read") else str(e)
                print(f"[{c['id']}] run {n}: ERROR: {detail}")
                continue
            passes += ok
            scores.append(score)
            print(f"[{c['id']}] run {n}: {'PASS' if ok else 'FAIL'}  score {score:.2f}")
            for line in lines:
                print(line)
        if passes < args.runs:
            failed += 1
        mean = sum(scores) / len(scores) if scores else 0.0
        print(f"[{c['id']}] {passes}/{args.runs} runs passed, mean score {mean:.2f}\n")

    print(f"{len(cases) - failed}/{len(cases)} cases passed on every run.")
    if any(g.get("type") == "tool_used" for c in cases for g in c["graders"]):
        print("Trigger checks were skipped: run `claude plugin eval` for those, or --manual.")
    return 1 if failed else 0


if __name__ == "__main__":
    # Piping into head sends SIGPIPE; die quietly rather than with a traceback.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
