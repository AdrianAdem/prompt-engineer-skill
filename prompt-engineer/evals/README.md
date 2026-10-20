# Evals

One directory per case: `prompt.md` holds the request, `graders/` holds one file
per check. This is the format `claude plugin eval` reads, and
`run_evals.py` reads the same files, so there is a single eval set.

## Two runners, two questions

`claude plugin eval` answers *does the skill help, and does it fire when it
should*. It loads the skill the way a session does, runs every case with the
skill and again without it, and reports the difference. The `tool_used`
graders check triggering: cases 07 and 08 must not load the skill, the rest
must. Run it from the repository root, after piloting:

    claude plugin eval prompt-engineer --runs 1 --no-publish --model sonnet --judge-model opus
    claude plugin eval prompt-engineer --no-publish --model sonnet --judge-model opus

The first command is the pilot. Read `costUsd` in the newest
`results/*/aggregate-result.json` in this directory before running the full
suite, which costs about three times that. The judge is a different model from the one under
test, for the reason in `references/evaluation.md`: a model grading its own
output is measuring itself.

`run_evals.py` answers *does the guidance produce the right answer once
applied*, through the API, for anyone without Claude Code. It cannot see
triggering, so it skips `tool_used` graders and says so. `--self-test` checks the
parsing and the suite's floor rules offline and runs in CI.

## Rules for the graders

A `regex` grader holds only what a regex is the right instrument for. Anything
that needs judgment is an `llm` grader with one checkable claim. Keyword
matching on a judgment question measures agreement with the author's
vocabulary, not quality: in the benchmark, a response the judges praised for
delegating the schema to a tool failed a keyword check looking for the words
"tool schema". Never tune these patterns against a fixed set of sample
answers; that tunes the test to the sample.

The floor, which `--self-test` enforces: at least one case where the skill must
not fire, at least one outcome grader per case besides the trigger check, and
three runs per case.

Results go to `evals/results/`, which is not committed.
