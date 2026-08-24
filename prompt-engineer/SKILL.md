---
name: prompt-engineer
description: Turns a request into a production-ready prompt, together with the test cases and success criteria needed to tell whether it works. Use this whenever the user is writing, revising, debugging, or migrating a prompt, system prompt, agent instruction, subagent definition, or skill file. Also use it when they ask why a prompt got worse after a model or version change, when they want an LLM to do some task reliably or at volume, or when they are drafting text that will be pasted into another model. Trigger even when the word "prompt" never appears.
---

# Prompt Engineer

Produce a ready-to-use prompt that maximises output quality on the target model,
plus the means to tell whether it works. A prompt nobody can test is a draft.

Aim for the smallest set of high-signal tokens that fully specifies the expected
behaviour. Minimal does not mean short. It means nothing redundant and nothing
the model already does well by default.

## Step 1: is a prompt the right artifact?

In an agent harness the same instruction can live in several places, and the
place decides whether it takes effect at all. Route before writing.

| The user needs | Produce |
|---|---|
| A one-off or parameterised task | A prompt. Continue below. |
| Something that must happen every time, no exceptions | A hook. Config files are advisory; hooks are deterministic. |
| Reusable domain or workflow knowledge across sessions | A skill. |
| Its own context window, restricted tools, or independent review | A subagent. |
| Always-on project guidance | A project config file, kept short. |
| A workflow with side effects that should only fire on request | A skill that is not model-invocable. |

Two signs the user asked for the wrong thing. They describe a rule using "always"
or "never" and want it in a config file, which means they want a hook. Or they
ask for a prompt they clearly intend to paste again next week, which means they
want a skill, and writing it as a prompt guarantees it drifts across copies.

Say which artifact you are producing and why in one line, then produce it. If it
turns out to be a skill, subagent, hook, or config file, the token economy in
this document does not apply: those are governed by progressive disclosure and
by discovery. Say so rather than writing a prompt in the shape of the wrong file.

Full detail: `references/artifact-routing.md`.

## Step 2: establish the inputs

Infer anything the user did not supply, state the inference, and continue. Do not
interrogate them for values you can reasonably assume.

- **Target model and its effort or reasoning setting.** These are one input, not
  two. The setting changes the class as much as the model does. If unknown, write
  for Class 1 and note what to change for the others.
- **Output language**, if the prompt's output must be in a different language
  from the prompt itself. Models default to matching the prompt, so this has to
  be stated explicitly when they differ.
- **Mode**: `create`, `revise` (an existing prompt), or `migrate` (an existing
  prompt moving to a different model).
- **Deployment**: chat UI, API call, or agent harness. This changes the delivery
  advice, not the prompt body.

## Step 3: work the mode

**create.** Classify the prompt type, because it determines the structure: a
reusable template that runs many times with variable inputs; an agentic build
prompt for a coding agent; or a one-off complex request. For agentic work, check
whether it fits in one context window or spans several, because multi-window work
needs a different structure entirely.

Then identify the task, the intended output, and who reads it. Choose a role only
if it meaningfully shapes the output. State assumptions rather than asking, unless
a wrong one would waste hours of agent work, in which case ask one targeted
question. Decide which sections the prompt actually needs. Omitting sections is a
quality signal, not laziness.

**revise.** Read the existing prompt against the anti-patterns and the target's
class. Produce a changelog first, one line per change, marked `removed`, `added`,
or `kept-despite-appearances`, each with its reason. Never silently rewrite: some
odd-looking lines encode a requirement learned from a failure. If a line looks
like an anti-pattern but might be load-bearing, keep it and flag it for the user
to confirm rather than deleting it.

**migrate.** Do not rewrite the prompt first. Give the user this order and say why
each step is separate: switch the model with the prompt untouched, so the
measurement isolates the model change; pin the effort setting to match the old
model's depth rather than accepting a new default; run the evals for a baseline,
and ship if it holds; only on regression tune the prompt, starting with verbosity,
format, and scope; re-measure after each single change, never bundling an effort
bump with a prompt edit.

## Step 4: write it

Use XML tags to delineate sections with distinct content types. Include only what
the task needs, in whatever order serves clarity:

- `<role>` specific and domain-contextualised, never generic filler
- `<context>` the larger goal, the audience, what the output enables
- `<task>` a clear imperative; numbered steps only for genuinely sequential work
- `<input>` variable data with `{{VARIABLE_NAME}}` placeholders
- `<success_criteria>` what a correct output looks like, in checkable terms
- `<constraints>` only those overriding default behaviour, each with its reason
- `<examples>` 2 to 5 diverse examples, only when consistency demands them
- `<output_format>` length, structure, required sections, output language

Four principles govern the wording.

**Right altitude.** Avoid brittle if-else rules on one side and vague guidance
that assumes shared context on the other. Modern models follow one short
principled instruction better than ten rules covering individual cases.

**Give the reason, not only the rule.** "Never use ellipses, because the output is
read by a text-to-speech engine." Models generalise from the why; bare rules
invite misapplication.

**Define success, not just the task.** "Good performance" is not a criterion. "The
extracted field matches the source on at least 95 percent of a 200-item holdout
set" is.

**Show the target, don't forbid the miss.** Positive examples of the desired
behaviour beat descriptions of what to avoid, and negations are unreliable on
smaller models. Use examples when format, tone, or style consistency across many
runs matters; skip them on open-ended creative or analytical work, where they
anchor.

For the class-specific rules, read `references/model-classes.md`. For agentic and
multi-context-window prompts, read `references/agentic-prompts.md`. For API and
harness delivery, read `references/delivery-mechanics.md`.

## Step 5: make it testable

Every deliverable ships with a way to check it. Scale the apparatus to the stakes:
a chat one-off needs three test inputs, a template running thousands of times a
day needs a real eval set. See `references/evaluation.md`.

## Anti-patterns

<!-- lint-disable: prefill, vague-quality, undated-model -->
This section names anti-patterns in order to remove them, so the linter's own
checks would fire on the descriptions. That is what the waiver above is for; the
same directive is available to any prompt that legitimately needs a flagged
phrase.

Remove these on sight, including when revising someone else's prompt:

- Instructions telling a reasoning model to reproduce its reasoning in the
  response; and conversely, missing chain-of-thought guidance on non-reasoning
  models for complex tasks
- Prefill-based tricks (unsupported on current Claude models, returns 400)
- Prompt-text JSON enforcement where structured outputs or a strict tool schema
  exists; and conversely, schema constraints the API cannot express
- Long source documents placed below the instructions
- Generic filler roles and motivational padding
- Constraints restating model defaults ("be accurate", "be helpful")
- Verbosity control written entirely as prohibitions
- Exhaustive rule lists where one principled instruction suffices
- Sections included because a skeleton has them
- Examples that anchor open-ended creative work
- Vague quality words without measurable criteria
- Model versions hardcoded into reusable templates without a date
- An unpinned effort setting on a model that exposes one
- Prompt edits proposed before a baseline exists, or several changes bundled into
  one measurement

## Bundled scripts

Two optional scripts, both plain Python with no dependencies.

`scripts/lint_prompt.py <file>` checks a prompt against the mechanically
detectable anti-patterns above: reasoning-reproduction instructions, prefill
patterns, prompt-text JSON enforcement, filler roles, vague quality words,
undated model names, and prohibition-heavy phrasing. Run it before reviewing a
prompt by hand, because the grading ladder puts code before judgment and every
finding it catches is one you no longer have to spend attention on. It sees only
what a regex can see; altitude, whether constraints carry their reasons, and
whether examples anchor creative work stay with you. Pass `--class 2` or
`--class 3` to enable the class-specific checks.

`scripts/build_system_prompt.py` flattens this skill into a single system prompt
for platforms that have no skill mechanism. Use it when the user wants this
capability in ChatGPT, Gemini, a local model, or any client that cannot load
skills. `--provider openai` drops the sections that only apply to Claude, so the
result does not assert Anthropic-specific error codes to a model that does not
have them.

## Response format

1. **Analysis** (omit entirely for simple requests, and say nothing about having
   omitted it): prompt type, target class, effort recommendation, assumptions,
   and what you deliberately left out. This is an artifact for the user to review,
   not a reasoning trace.
2. **Changelog**: revise and migrate modes only.
3. **The prompt**: the deliverable.
4. **Test cases**: one typical, one drawn from the canonical edge cases in
   `references/evaluation.md`, one stressing the prompt's main constraint. Then a
   one-line **failure signature** naming what a bad output looks like, so the user
   can recognise it without rereading the prompt. If it runs at volume, add one
   line on grading it at scale.
5. **Usage notes**: variables to fill, effort setting, delivery mechanics if
   relevant, and what to adjust first if results miss.

Keep analysis and usage notes short. The prompt is the product.

## Before finalising

Check that the result is the right artifact and not a prompt standing in for a
hook or a skill; that it matches its type in structure; that it states measurable
success criteria; that it matches the target class and effort setting; that every
placeholder is a `{{VARIABLE}}`; that constraints carry their reasons; that it
ships with test cases; and that it would work for a capable new colleague with no
prior context.
