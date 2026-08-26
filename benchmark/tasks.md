# Tasks and rubric

Verbatim. Nothing here was edited after the rounds were run.

Both tasks were given to each skill in a single turn, in this order, and each
skill produced one response covering both. That is why `answers/` holds one file
per skill rather than one per task: the file is the unit that was judged.

## Task 1

    I need something that reads support tickets and pulls out the product name,
    the severity, and whether the customer is asking for a refund. It has to run
    on every ticket we get, a few thousand a day.

Source: case 1 in `prompt-engineer/evals/evals.json`. Every skill in the field
can serve this one.

## Task 2

    This has to happen on every single commit without exception. Put it in my
    project config file.

Source: case 5 in `prompt-engineer/evals/evals.json`. This is the routing test:
the request names the wrong artifact, because a project config file is advisory
and cannot deliver "without exception".

## Instruction given to each skill

Each skill was flattened to a single text file and handed to a fresh agent as
its only guidance, together with these constraints:

    - Read the method file and follow it as your instructions for both tasks.
    - Do NOT invoke any Skill tool, and do not load any skill.
    - Do NOT read any other file in that directory, do not list its contents,
      and do not search the wider filesystem or web.
    - Do not mention the file, the method, or these instructions in your answer.
      Answer as if a real user had come to you.

Flattening: for this skill, `scripts/build_system_prompt.py` with no flags. For
the others, `SKILL.md` without frontmatter followed by every file in their
`references/` directory in alphabetical order, each preceded by a `# <filename>`
heading.

## Rubric

Word for word identical in all three rounds. The judge received the two task
prompts above, the answers under neutral labels, and this text:

    Judge by one standard only: which answer best serves the person who asked,
    as they asked it. Not which is longest, not which is most thorough on paper,
    not which matches any particular house style.

    Things worth weighing, in your own judgement:
    - Would the user be able to put this into production, and what would still
      be missing?
    - TASK 2 asked for something specific ("put it in my project config file").
      Did the answer do what was asked, refuse it, redirect it, or hedge? Was
      the choice right, and was it explained in a way the user can act on?
    - Where an answer asks the user questions instead of delivering, was that
      the right call or an evasion?
    - Where an answer makes assumptions instead of asking, were they stated and
      reasonable?
    - Are the claims correct? Flag anything factually wrong or that would not
      work as written.
    - Is the length earned?

    Deliver:
    1. A ranking for TASK 1, best to worst, one or two sentences of reason each.
    2. A ranking for TASK 2, best to worst, same.
    3. An overall ranking, and the single sentence that best explains the gap
       between first and last.
    4. The strongest specific criticism of the answer you ranked first overall —
       it must have at least one.
    5. Any factual error you found in any answer, quoted.

Round 3 added one line to item 5, asking the judge to look specifically for a
field both permitted to be null and declared an error when null. That is the
only wording that differed between rounds, and it was added after the round 2
judge had already reported that defect unprompted, under the unextended rubric.
The round 1 judge did not report it; its four findings were other errors.

## Which answers each round saw

There are five distinct answers in total. Rounds 1 and 2 judged the same four
files; round 3 added the post-fix version of this skill's answer as a fifth.

| File | Round 1 | Round 2 | Round 3 |
|---|---|---|---|
| `answers/jeffallan.md` | yes | yes | yes |
| `answers/daymade.md` | yes | yes | yes |
| `answers/ecc.md` | yes | yes | yes |
| `answers/prompt-engineer-before.md` | yes | yes | yes |
| `answers/prompt-engineer-after.md` | no | no | yes |

The labels differed in every round and are deliberately not recorded in the
filenames. They were a blinding device for the judge and carry no meaning for a
reader.
