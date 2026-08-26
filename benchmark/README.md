# Benchmark

Three rounds comparing this skill against three other public prompt-engineering
skills, on the same two tasks, with an LLM judge and a fixed rubric.

The results are here in full, including the two rounds where this skill did not
win and the finding that undermines the ranking method itself. A benchmark that
only reports its author's wins is an advertisement.

## Method

Four skills, two tasks. Each skill produced **one response covering both
tasks**, which is how the judge saw it, so `answers/` holds five files and not
ten. Each round relabelled the answers and reshuffled their order. Nothing was
removed from them: they were checked for traces of their origin by grepping for
skill and author names, with no hits.

**The rubric was not identical across all three rounds, and that matters for
what this benchmark can claim.** Rounds 1 and 2 used the same rubric word for
word. Round 3 extended item 5 to ask the judge to look for constraints inside a
prompt that contradict each other, naming the null-field case as the example.

That extension is exactly the defect this skill's pre-fix answer contained, so
the change is not neutral and should not be read as one. What keeps round 3
usable: the round 2 judge had already reported the same contradiction
unprompted, under the unextended rubric. The extension made the judge look for
something it had found on its own, it did not create the finding. Round 3
comparisons against rounds 1 and 2 are weaker for it; comparisons **inside**
round 3, which is where the before-and-after result lives, are unaffected,
because both versions faced the same extended rubric.

| Round | Judge model | Labels reshuffled | Field |
|---|---|---|---|
| 1 | Opus | yes | 4 skills |
| 2 | Opus | yes, different mapping | same 4 answers, unchanged |
| 3 | Sonnet | yes, different mapping | 5 answers: this skill before and after a fix |

Round 2 changed only the judge instance and the labels. Round 3 changed the
judge's model and added the pre-fix version of this skill's answer as a fifth
entry, so the effect of a change could be read inside a single run.

**Task 1.** An extraction and classification prompt for support tickets, running
at volume, unattended.
**Task 2.** Enforce a rule on every commit, in a way an agent cannot route
around.

## Results

Per task, because the aggregate turned out not to mean anything (see below).

**Task 1**

| Round | 1st | 2nd | 3rd | 4th | 5th |
|---|---|---|---|---|---|
| 1, Opus | Jeffallan | daymade | this skill | ECC | |
| 2, Opus | Jeffallan | daymade | ECC | this skill | |
| 3, Sonnet | Jeffallan | this skill, fixed | daymade | ECC | this skill, before fix |

**Task 2**

| Round | 1st | 2nd | 3rd | 4th | 5th |
|---|---|---|---|---|---|
| 1, Opus | this skill | daymade | Jeffallan | ECC | |
| 2, Opus | this skill | daymade | Jeffallan | ECC | |
| 3, Sonnet | daymade | Jeffallan | this skill, before fix | this skill, fixed | ECC |

## What the data supports

**Task 2 is this skill's win, and the judge said why.** It was the only response
that closed the bypass: the agent hook and the git hook call the same script,
`--no-verify` is blocked explicitly, and the test case requires the terminal
bypass to fail. That is the artifact-routing doctrine in `SKILL.md` showing up
in the output.

**Task 1 is this skill's loss, three times, against two judge models.** Jeffallan
wins it in every round. The gap narrowed after the evaluation guidance here was
rewritten, from last place to second in round 3, and the judge named the reason:
seed set, held-out portion, confusion matrix, per-class precision and recall.
The gap did not close.

**One fix is cleanly attributable.** Round 3 held both versions of this skill's
Task 1 answer, judged together, same judge, same rubric, in the same run. Before
the rewrite of `references/evaluation.md`: last. After: second. That is the only
clean before-and-after measurement in the whole exercise, and it is the reason
the file grew from 445 to 956 words. Being inside one round, it is also the one
result the rubric change does not touch.

**A second fix removed a real defect.** The pre-fix answer contained a
contradiction: it told the model to return `null` for an undetermined field and,
two lines later, that a null field breaks the downstream insert. The judge found
it independently and reported no comparable contradiction in any other answer.
The `sentinel-conflict` check in `scripts/lint_prompt.py` exists because of this
finding.

## What the data does not support

**The aggregate ranking is noise.** Rounds 1 and 2 used the same four answers,
the same rubric, and differed only in judge instance and labels. Three of four
positions moved. Any overall "this skill placed Nth" claim from this benchmark
is weaker than it sounds.

**The judge's model dominates.** The same unchanged Task 2 answer placed first
under two Opus judges and third under a Sonnet judge. The judge's model moved
the result more than the content did.

**Only within-run comparisons are load-bearing.** The evaluation-rewrite result
holds because both versions were judged in the same run by the same judge, under
the same rubric. Every cross-round comparison here should be read as indicative
at best, and the round 3 comparisons against rounds 1 and 2 carry the additional
caveat of the rubric extension described in the method.

**Both sides are Claude models.** Candidates and judges come from one model
family. A judge from a different vendor would be a stronger test and has not
been run.

## Reproducing it

`tasks.md` holds both task prompts and both rubric versions verbatim, with the
round 3 extension marked. `answers/` holds all five responses exactly as the
judge saw them, each covering both tasks. Nothing was edited after judging, and
nothing was removed from the answers before it.

The honest way to rerun this is to change one variable at a time and to compare
within a run rather than across runs. If you rerun it and this skill does worse,
open an issue with the round and the judge model; that is more useful than a
star.
