# prompt-engineer

An Agent Skill that turns a request into a production-ready prompt, together with
the test cases and success criteria needed to tell whether it works.

It handles three modes. **Create** writes a new prompt. **Revise** improves an
existing one and shows a changelog rather than silently rewriting it. **Migrate**
moves a working prompt to a different model without conflating the model change
with prompt changes.

Before writing anything it checks whether a prompt is the right artifact at all,
because in an agent harness the same instruction can live in a prompt, a hook, a
skill, a subagent, or a config file, and the placement decides whether it takes
effect.

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
your task as a prompting task.

## Layout

    prompt-engineer/
    ├── SKILL.md                        core workflow and anti-patterns
    ├── references/
    │   ├── model-classes.md            capability signatures and effort settings
    │   ├── delivery-mechanics.md       turn placement, structured output, caching
    │   ├── evaluation.md               success criteria, edge cases, grading
    │   ├── agentic-prompts.md          phased builds and multi-window work
    │   └── artifact-routing.md         prompt vs hook vs skill vs subagent
    ├── scripts/
    │   ├── lint_prompt.py              mechanical anti-pattern check
    │   └── build_system_prompt.py      flatten to one file for other platforms
    ├── commands/prompt.md              optional slash command
    └── evals/evals.json                trigger and behaviour test cases

Reference files load only when the task needs them, so the always-on cost is the
description alone.

## Using it outside Claude

The skill *format* is Anthropic's: Claude Code, Claude.ai, Cowork, and the Agent
SDK read it. The *content* is deliberately cross-provider, with sections on
OpenAI, Gemini, and open-weight conventions, and model classes defined by
capability signature rather than by vendor.

For a platform with no skill mechanism, flatten it into one system prompt:

    python scripts/build_system_prompt.py -o system-prompt.md
    python scripts/build_system_prompt.py --provider openai -o system-prompt.md
    python scripts/build_system_prompt.py --core -o system-prompt.md

The full build is roughly 6,900 tokens, the core alone roughly 2,000. The
`--provider` flag drops sections tagged for a different vendor, so a prompt built
for OpenAI does not assert Claude-specific error codes and schema limits. Every
section in `delivery-mechanics.md` carries a `[universal]`, `[anthropic]`, or
`[varies]` tag for exactly this reason; that file moves fastest and is the one to
distrust first when something reads as out of date.

## Linting a prompt

    python scripts/lint_prompt.py myprompt.md
    python scripts/lint_prompt.py myprompt.md --class 2
    python scripts/lint_prompt.py myprompt.md --json

Catches the anti-patterns a regex can see and exits non-zero on errors, so it
drops into a pre-commit hook or CI. It deliberately does not judge altitude,
whether constraints carry their reasons, or whether examples are anchoring
creative work. Those need a model.

Both scripts are standard library only, Python 3.8 or later, no install step.

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
reproducible case. The most useful contribution is a prompt that this skill
handled badly, along with what you expected.

## License

MIT. See `LICENSE`.
