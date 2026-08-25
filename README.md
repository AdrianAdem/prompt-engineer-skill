# prompt-engineer

An Agent Skill that turns a request into a production-ready prompt, together with
the test cases and success criteria needed to tell whether it works. It also
works the other way round: when the request is the work itself, the skill
supplies the structure for doing it and for briefing subagents, without handing
back a document about it.

Before writing anything it checks whether a prompt is the right artifact at all,
because in an agent harness the same instruction can live in a prompt, a hook, a
skill, a subagent, or a config file, and the placement decides whether it takes
effect.

## Four modes

**Create** writes a new prompt. **Revise** improves an existing one and shows a
changelog rather than silently rewriting it, because odd-looking lines often
encode a requirement learned from a failure. **Migrate** moves a working prompt
to a different model without conflating the model change with prompt changes.
**Execute** is for the agent itself: the person asked for the work, not for a
document about it.

## Install

Copy the `prompt-engineer/` directory into your skills directory.

    # Claude Code, project-scoped
    cp -r prompt-engineer .claude/skills/

    # Claude Code, user-scoped
    cp -r prompt-engineer ~/.claude/skills/

The optional slash command lives in `commands/prompt.md`. Copy it to
`.claude/commands/` to invoke the skill explicitly:

    /prompt an extractor for support tickets, running at volume
    /prompt revise <existing prompt>
    /prompt migrate <target model> <existing prompt>

The command is for when you know you are working on a prompt. The skill also
triggers on its own description, which covers the case where you do not think of
your task as a prompting task at all.

## Layout

    prompt-engineer/
    ├── SKILL.md                        core workflow and anti-patterns
    ├── references/
    │   ├── artifact-routing.md         prompt vs hook vs skill vs subagent
    │   ├── model-classes.md            capability signatures and effort settings
    │   ├── delivery-mechanics.md       turn placement, structured output, caching
    │   ├── agentic-prompts.md          phased builds and multi-window work
    │   ├── examples.md                 coverage, ordering, when examples hurt
    │   ├── self-and-subagents.md       using it on your own work, briefing agents
    │   └── evaluation.md               success criteria, edge cases, grading
    ├── scripts/
    │   ├── lint_prompt.py              mechanical anti-pattern check
    │   └── build_system_prompt.py      flatten to one file for other platforms
    ├── hooks/
    │   ├── restate-brief.py            optional, see below
    │   ├── settings-snippet.json
    │   └── README.md
    ├── commands/prompt.md              optional slash command
    └── evals/
        ├── evals.json                  behaviour and triggering cases
        └── run_evals.py                runner with assertions

Reference files load only when the task needs them, so the always-on cost is the
description alone.

## What the skill actually enforces

Three things it gets right that are easy to get wrong by hand.

**Class is model times effort, not model alone.** A frontier model pinned to
minimal reasoning wants explicit steps, not goal-level guidance, and defaults
shift between model generations. An unpinned effort setting is treated as an
unknown class rather than assumed.

**Multi-session work gets two prompts, not one.** A single prompt repeated per
session fails predictably: the first session tries to one-shot the whole thing
and runs out of context mid-feature, and a later session sees progress and
declares the job done. The initializer builds the environment, the worker takes
exactly one item per session and may only flip a status field.

**Verification means the real surface.** A green unit test and a successful curl
against a dev server say nothing about whether a user can use the feature.

## Using it on your own work

`references/self-and-subagents.md` covers the case where you are the one doing
the work rather than writing a prompt for someone else. The rule that matters is
about size, not about whether to think: for a single session, a written prompt
addressed to yourself costs a turn and gains nothing, so state the phases and
acceptance criteria in a paragraph and build. For work spanning sessions, the
written artifacts are the only state that survives, and they belong in the repo.

For subagent briefs it gives four required parts, the mapping from the agent's
model tier to the register of the brief, and one rule worth singling out: never
put your own conclusion in a review brief. "Check whether this is safe, I think
it is" gets you agreement, which destroys the independence you delegated for.

## Linting a prompt

    python scripts/lint_prompt.py myprompt.md
    python scripts/lint_prompt.py myprompt.md --class 2
    python scripts/lint_prompt.py myprompt.md --json

Catches the anti-patterns a regex can see: reasoning-reproduction instructions,
prefill patterns, prompt-text JSON enforcement, roles asserting seniority or
experience instead of domain, vague quality words, undated model names, and
prohibition-heavy phrasing. It exits non-zero on errors, so it drops into a
pre-commit hook or CI.

A file can waive checks it discusses rather than commits:

    <!-- lint-disable: prefill, vague-quality -->

and a single line can waive everything with a trailing `lint-ignore`. For whole
files that are documentation about prompting rather than prompts, use `--docs`,
which disables the six checks that fire on merely naming a pattern. The skill's
own reference files are linted that way; `SKILL.md` and the slash command are
linted normally, because they are instructions.

The model-name check is deliberately not part of `--docs`: reference
documentation is the first thing to go stale, so it stays live everywhere and is
satisfied by recording a date, not by an exemption.

    ./scripts/lint_all.sh

runs every prose file the skill ships in the mode that fits it, and validates
the two JSON files structurally. Exit 0 means the whole package is clean, not
just one file.

It deliberately does not judge altitude, whether constraints carry their reasons,
or whether examples are anchoring creative work. Those need a model. Agentic
build prompts are exempt from the placeholder check, since they are parameterless
by design.

## Running the evals

    export ANTHROPIC_API_KEY=...
    python evals/run_evals.py                  # the automatable cases
    python evals/run_evals.py --manual         # the triggering checklist
    python evals/run_evals.py --dry-run        # print prompts, call nothing

Each case carries machine-checkable assertions rather than a prose expectation,
so a run gives a pass count instead of something to read and judge. Failures
write the full output to `evals/out_<id>.txt`.

Two cases test whether the skill *triggers*, and those are printed as a manual
checklist instead of being run. Triggering is a property of the harness that
loads the skill; no API call reproduces it. Pretending otherwise would be the
exact failure this skill warns about, a green result that proves nothing.

## Using it outside Claude

The skill *format* is Anthropic's: Claude Code, Claude.ai, Cowork, and the Agent
SDK read it. The *content* is deliberately cross-provider, with sections on
OpenAI, Gemini, and open-weight conventions, and model classes defined by
capability signature rather than by vendor.

For a platform with no skill mechanism, flatten it into one system prompt:

    python scripts/build_system_prompt.py -o system-prompt.md
    python scripts/build_system_prompt.py --provider openai -o system-prompt.md
    python scripts/build_system_prompt.py --core -o system-prompt.md

The full build is roughly 8,900 tokens, the core alone roughly 2,000. The
`--provider` flag drops sections tagged for a different vendor, so a prompt built
for OpenAI does not assert Claude-specific error codes and schema limits. Every
section in `delivery-mechanics.md` carries a `[universal]`, `[anthropic]`, or
`[varies]` tag for exactly this reason; that file moves fastest and is the one to
distrust first when something reads as out of date.

Both scripts are standard library only, Python 3.8 or later, no install step.

## Optional: the restate hook

`hooks/restate-brief.py` is a `UserPromptSubmit` hook for Claude Code. It exists
because a skill is *selected*, so it fires some of the time, and some things
should fire every time the condition holds.

When a request looks like a commission for multi-step work, it injects about 150
tokens asking for a four-sentence restatement first: the understood goal, the
assumptions the request did not specify, and the acceptance criteria. That is the
cheapest possible place to catch a misread brief, and it is a fortieth of the
cost of writing a full prompt artifact.

It stays silent on questions, lookups, single edits, one-word replies, and
requests already long enough to be fully specified. The verb lists are heuristics
and are meant to be edited to match how you actually write. It exits zero on any
malformed input, because a hook that blocks a turn is worse than one that does
nothing.

It ships inside the skill directory so one copy step installs everything, but a
hook is not loaded from there. Copy it to `~/.claude/hooks/` and merge
`settings-snippet.json` into your `settings.json`. Check the payload field name against your Claude Code
version; the script tries four common variants.

## Scope and limits

The advice is distilled from published prompting guidance from Anthropic, OpenAI,
and Google, plus practical failure modes seen in real use. It is written in the
author's own words rather than copied.

Two honest caveats.

The **named example models are dated August 2026** and will go stale. The skill
classifies by capability signature rather than by model name precisely so the
structure survives that, but the examples in `model-classes.md` will need
refreshing.

The **Class 3 guidance for small and open-weight models is the least
well-sourced** section. It is marked as such in the file. Treat it as a starting
point and rely on evals more heavily there.

## Contributing

Corrections to model behaviour claims are especially welcome, particularly with a
reproducible case. The most useful contribution is a prompt this skill handled
badly, along with what you expected instead.

## License

MIT. See `LICENSE`.
