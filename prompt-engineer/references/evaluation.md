# Evaluation

Every deliverable ships with a way to check it. Scale the apparatus to the
stakes: a chat one-off needs three test inputs, a template running thousands of
times a day needs a real eval set.

## Success criteria

Specific, measurable, achievable, relevant. Push back on "accurate" and "high
quality" by asking what number, on what set, compared to what. Even soft
dimensions quantify. Instead of "safe outputs", write "fewer than 0.1 percent of
10,000 outputs flagged by the content filter".

Most real use cases need several criteria at once, because task fidelity,
consistency, tone, latency, and cost trade against each other. Naming the
trade-off is part of the deliverable.

## Canonical edge cases

Derive test cases from this list before inventing your own. These are the four
that break prompts in production:

- irrelevant or nonexistent input data
- input far longer than expected
- hostile, harmful, or off-topic input, for anything conversational
- cases genuinely ambiguous enough that two careful humans would disagree

## Eval design

Mirror the real input distribution, including its edges. Automate grading
wherever the question can be structured to allow it. Prefer many test cases with
imperfect automated grading over a handful of hand-graded ones, and generate the
bulk of them from a small hand-written seed set.

## Grading ladder

Use the fastest reliable method.

1. **Code-based**: exact match, string match, schema validation, banned-word
   lists, structural checks. Fast, free, and deterministic. Most format and
   constraint requirements reduce to this if you design them to.
2. **LLM-based**: where judgment is required. Write an explicit rubric with a
   hard failure condition, force a categorical or 1-to-5 verdict rather than
   prose, let the grader reason before scoring and discard that reasoning, and
   grade with a different model than the one that generated the output.
3. **Human**: only where nothing else works.

A useful pattern for volume: run the code-based checks first and send only the
survivors to an LLM grader. It cuts cost sharply and makes the LLM grader's job
narrower, which makes it more reliable.

## Iteration discipline

Establish a baseline before touching the prompt. Change one thing per
measurement. Re-run after each change.

Tuning a prompt against impressions instead of a baseline is how prompts
accumulate lines nobody can justify later, and it is the single most common
reason a long-lived prompt becomes unmaintainable.

## Failure signature

Alongside the test cases, name in one line what a bad output will look like. This
is what lets someone recognise a regression months later without rereading the
prompt and reconstructing its intent. Good failure signatures are concrete:
"bullets that restate the headline at three levels of abstraction", not "output
quality drops".
