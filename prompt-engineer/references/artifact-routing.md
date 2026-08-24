# Artifact routing

Not every request for "a prompt" is best served by one. In an agent harness the
same instruction can live in several places, and the place determines whether it
actually takes effect. Route first, write second.

## The decision

**A prompt** for a one-off or parameterised task. It is invoked explicitly, it
can take arguments, and nothing about it persists.

**A hook** for anything that must happen every time with no exceptions. Hooks run
deterministically at defined points in the agent's lifecycle. Instructions in a
config file are advisory, and a capable model may reasonably decide against them
in a case the author did not foresee. A rule that cannot tolerate exceptions does
not belong in prose.

**A skill** for reusable domain or workflow knowledge across sessions. The
selection mechanism is the description field, which has to say both what the
skill does and when to use it, in the words the user will actually type. A skill
whose description only describes its function under-triggers, which looks
identical to the skill not existing.

**A subagent** when the work needs its own context window, a restricted tool set,
or an independent reviewer. The independence is the point: a model reviewing its
own output in the same context inherits its own blind spots.

**A project config file** for always-on guidance, kept short. Length here is a
standing tax on every session, because the file is loaded on every turn whether
it is relevant or not.

**A skill that is not model-invocable** for a workflow with side effects that
should only fire when explicitly asked for. It is invoked by name rather than
triggered by inference.

## Two signals the user asked for the wrong artifact

They describe a rule using "always" or "never" and want it in a config file. That
is a hook. Advisory text cannot deliver an absolute guarantee, and writing it as
if it could produces a rule that holds most of the time, which is worse than
either alternative because it looks reliable.

They ask for a prompt they clearly intend to paste again next week. That is a
skill. Writing it as a prompt guarantees it drifts across copies, and the copies
diverge silently.

## Token economy does not transfer

When the right artifact is a skill, subagent, hook, or config file, the
minimalism that governs prompt writing does not apply, and applying it does
damage.

Skills use progressive disclosure: the metadata is always loaded, the body loads
when the skill triggers, and bundled reference files load only when read. That
means the description must be dense and the body can be generous. Cutting a
skill body for brevity trades away detail that costs nothing until it is needed.

Config files are the opposite: always loaded, so every line is a permanent cost
and brevity genuinely matters.

Say which regime applies rather than writing one artifact in the shape of
another.
