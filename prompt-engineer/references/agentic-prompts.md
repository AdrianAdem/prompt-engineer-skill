# Agentic and multi-window prompts

## Structure of an agentic build prompt

Beyond the normal sections, an agentic prompt needs:

**Sequential phases** that can be executed and verified independently, each with
its own acceptance criteria. A phase without an acceptance check is a wish.

**Self-verification with fresh context.** "Establish a method for checking your
own work as you build. Run it at the end of each phase against the acceptance
criteria, using a subagent with fresh context rather than reviewing your own
reasoning." Separate verifier subagents outperform self-critique, because a model
reviewing its own reasoning in the same context inherits its own blind spots.

**End-to-end verification, not unit-level.** Models will run unit tests or curl a
dev server and conclude a feature works when it does not work for a user. Where
the task has a user-facing surface, require verification through that surface:
browser automation, the actual CLI, the real endpoint.

**Grounded progress claims.** "Before reporting progress, audit each claim
against an actual result from this session. Only report work you can point to
evidence for. If tests fail, say so with the output."

**Scope boundaries.** "Do not add features, refactor, or introduce abstractions
beyond what the task requires. Do the simplest thing that works well. Validate
only at system boundaries such as user input and external APIs."

**Checkpoint policy.** "Pause for the user only when the work genuinely requires
them: a destructive or irreversible action, a real scope change, or input only
they can provide. Otherwise proceed end to end."

**Failure visibility** for anything automated: explicit error detection and
alerting rather than silent fallbacks. A silent fallback in an unattended system
means the user acts on stale data without knowing it is stale.

## Corrections for specific failures

Include these verbatim only when the described failure actually applies. They are
corrections, not boilerplate, and adding them speculatively costs tokens and
attention.

**Unattended operation**, when the user cannot answer mid-task:

    You are operating autonomously. The user is not watching in real time and
    cannot answer questions mid-task, so asking "Want me to...?" will block the
    work. For reversible actions that follow from the original request, proceed
    without asking.

**Early stopping**, when the model announces an action instead of taking it, or
pauses for permission it already has:

    Before ending your turn, check your last paragraph. If it is a plan, an
    analysis, a question, a list of next steps, or a promise about work you have
    not done ("I'll...", "let me know when..."), do that work now with tool
    calls. End your turn only when the task is complete or you are blocked on
    input only the user can provide.

**Context budget anxiety**, when the model truncates its work or proposes a fresh
session as the window fills. In a harness that compacts or persists state, say so
explicitly, because otherwise the model is right to be cautious:

    Your context window will be compacted automatically as it approaches its
    limit, so you can continue from where you left off. Do not stop early on
    account of token budget. As you approach the limit, save your current
    progress and state before the window refreshes, then continue.

If the harness does neither, the honest version is shorter: "You have ample
context remaining. Continue the work." Better still, stop showing the countdown
to the model if the harness allows it.

**Final-summary readability**, when after many tool calls the model writes in
shorthand the user never saw:

    Terse shorthand is fine between tool calls. Your final summary is different:
    it is for a reader who saw none of that. Open with the outcome in one
    sentence, then the supporting detail, then the one or two things you need
    from them. Drop the working vocabulary you built up unless you reintroduce
    it. Write complete sentences and give each file, commit, or flag its own
    plain clause. If you have to choose between short and clear, choose clear.

## Work spanning multiple context windows

Work that cannot finish in one context window is a different problem from a long
single session. A single prompt repeated per session fails it in two
characteristic ways: the first session tries to one-shot the whole thing and runs
out of context mid-feature, and a later session looks around, sees progress, and
declares the job done.

When the task spans sessions, write two prompts.

**Initializer prompt**, for the first context window only. Its job is to build
the environment every later session relies on, not to build the product:

- a structured feature list, one entry per end-to-end user-visible behaviour,
  each marked as failing at the start. Use JSON rather than Markdown, because
  models are markedly less willing to quietly rewrite a JSON file.
- a startup script, so no later session has to rediscover how to run the thing
- a progress file and an initial commit

**Worker prompt**, for every subsequent window:

- start by reading the progress file, the commit log, and the startup script,
  then smoke-test the current state to catch undocumented breakage
- pick exactly one feature from the list and do only that
- edit the feature list only by flipping a status field. Say plainly that
  removing or rewriting entries is unacceptable, because it silently shrinks the
  definition of done.
- flip a status to passing only after verifying end to end the way a user would
- end by committing with a descriptive message and writing a progress update

The pair costs more to write than one prompt and is the difference between an
agent that finishes and one that plateaus. Raise it whenever the user describes
work measured in days rather than hours.
