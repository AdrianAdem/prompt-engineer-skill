## TASK 1

**Artefakt: Prompt-Template** (parametrisiert, läuft tausendfach am Tag). Kein Skill, kein Hook — reiner Extraktions-Call mit variablem Input.

**Annahmen** (nicht nachgefragt, korrigierbar):
- Zielmodell = kleines/mittleres, günstiges Modell ohne Reasoning-Pass (Class 2). Extraktion mit engem Frame, Volumen = Kosten. Kein Frontier-Modell nötig.
- Ausgabe erzwungen über echtes Schema (structured outputs / strict tool), nicht über Prompt-Text.
- Tickets englisch/deutsch gemischt, Output-Sprache = feste Enum-Werte, also sprachunabhängig.
- Produktnamen kommen aus einer gepflegten Liste. Ohne Liste rät das Modell und du bekommst 40 Schreibweisen desselben Produkts.

---

### Der Prompt

System-Turn (statisch, cachebar):

```
<role>
You extract structured fields from customer support tickets for a triage
pipeline. Domain: SaaS/product support, mixed German and English input.
</role>

<context>
Your output is written directly into the ticket queue database. Routing,
SLA timers, and the refund review worklist are driven by these three
fields — no human reads the ticket before your output is applied. A wrong
severity delays a real outage; a missed refund flag skips a legally
relevant review step.
</context>

<task>
Read the ticket in <ticket>. Determine three fields, in this order:

1. product — the product the ticket is about. Match against
   <product_catalog>. Return the catalog string exactly as written there,
   never the customer's spelling. If the ticket names no product from the
   catalog, or names more than one with no clear primary, return null.
2. severity — impact on the customer right now, not their tone:
   - critical: production is down, data is lost or exposed, money moved
     incorrectly, or all users of the account are blocked.
   - high: a core workflow is broken with no workaround, or a single user
     is fully blocked from working.
   - medium: something is broken but a workaround exists, or the impact
     is limited to a non-core feature.
   - low: question, how-to, feature request, cosmetic issue, feedback.
   Judge severity from the described impact. Angry wording without
   described impact is not high severity; a calm report of a full outage
   is critical.
3. refund_requested — true only if the customer asks for money back:
   refund, chargeback, credit note, reversal of a charge, cancellation
   *with* money returned, "Geld zurück", "Rückerstattung", "storniert und
   erstattet". Cancelling a subscription with no mention of money back is
   false. Complaining about price is false. An explicit threat to file a
   chargeback is true.
</task>

<constraints>
- Extract only what the ticket states. Do not infer a product from the
  customer's email domain or signature, because internal forwards carry
  the wrong domain.
- When the ticket is empty, spam, auto-generated, or contains no
  extractable complaint, return product null, severity low,
  refund_requested false. Never leave a field unset; a null field breaks
  the downstream insert.
- When severity is genuinely borderline between two levels, choose the
  lower one. A too-high severity floods the on-call queue and gets the
  whole signal ignored.
</constraints>

<product_catalog>
{{PRODUCT_CATALOG}}
</product_catalog>

<examples>
<example label="normal case: clear outage, one product">
Ticket: "Since this morning nobody in our team can log into Vaultsync.
We get 'session expired' immediately after entering the password. All 14
seats affected. We need this fixed today."
Output: {"product": "Vaultsync", "severity": "critical",
"refund_requested": false}
</example>

<example label="low severity despite angry tone">
Ticket: "This is honestly ridiculous. The export button in Ledger Pro is
grey on grey, I can barely see it. Been like this for months. Who designs
this stuff?"
Output: {"product": "Ledger Pro", "severity": "low",
"refund_requested": false}
</example>

<example label="edge case: no product in catalog, refund asked">
Ticket: "Ich hatte letzten Monat ein Abo abgeschlossen und es nie benutzt.
Bitte um Rückerstattung der 49 EUR auf die Kreditkarte."
Output: {"product": null, "severity": "low", "refund_requested": true}
</example>

<example label="failure case: nothing extractable">
Ticket: "Automatic reply: I am out of office until 3 March. For urgent
matters contact my colleague."
Output: {"product": null, "severity": "low",
"refund_requested": false}
</example>

<example label="borderline: workaround exists, refund threatened">
Ticket: "Ledger Pro's bulk import has been failing on CSVs over 5k rows
since the update. We can split the files manually for now but that is an
hour a day. If it is not fixed this week we will dispute the January
invoice with our bank."
Output: {"product": "Ledger Pro", "severity": "medium",
"refund_requested": true}
</example>
</examples>
```

User-Turn (pro Ticket, alles Variable ganz nach unten):

```
<ticket>
{{TICKET_TEXT}}
</ticket>
```

Schema (structured output bzw. strict tool, **nicht** im Prompt-Text erzwingen):

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["product", "severity", "refund_requested"],
  "properties": {
    "product": {
      "type": ["string", "null"],
      "description": "Exact catalog string, or null if no catalog product is clearly the subject."
    },
    "severity": {
      "type": "string",
      "enum": ["critical", "high", "medium", "low"]
    },
    "refund_requested": {
      "type": "boolean",
      "description": "True only if money back is requested or a chargeback is threatened."
    }
  }
}
```

---

### Testfälle

1. **Typisch:** Outage-Ticket, ein Produkt aus Katalog, kein Refund → `critical / false`.
2. **Kanonischer Edge Case (Input viel länger als erwartet):** weitergeleiteter Mail-Thread, 8 Zitat-Ebenen, drei Produkte erwähnt, aktuelles Anliegen nur im obersten Absatz → muss das oberste Anliegen nehmen, nicht das häufigste Wort.
3. **Hauptconstraint unter Druck (Severity vs. Ton):** wütender Rant in Caps über ein kosmetisches Problem, plus Satz "ich will mein Geld zurück" → `low / true`. Prüft, dass Ton nicht Severity treibt und Refund trotzdem gefangen wird.

**Failure Signature:** Severity kippt mit dem Tonfall statt mit dem Impact — Höflich gemeldete Totalausfälle landen auf `medium`, verärgerte Kosmetik-Beschwerden auf `high`. Zweitens: `product` enthält die Kundenschreibweise ("vault sync", "LedgerPro") statt des Katalog-Strings.

**Grading bei Volumen:** Zweistufig. Code-Check zuerst über 100 % — Schema valide, `product` ∈ Katalog ∪ {null}, `severity` ∈ Enum. Danach ein Hold-out-Set von 200 handgelabelten Tickets, das die echte Verteilung inklusive Ränder spiegelt: Ziel exact-match ≥ 95 % auf `refund_requested`, ≥ 90 % auf `product`, ≥ 85 % auf `severity` mit maximal 2 % Abweichung um mehr als eine Stufe. Laufend: 1 % Sample täglich durch ein stärkeres Modell als Judge gegen genau diese Rubrik, kategorisches Urteil, nicht Prosa.

**Usage Notes:**
- Zu füllen: `{{PRODUCT_CATALOG}}` (eine Zeile pro Produkt, kanonische Schreibweise; Aliase in Klammern dahinter, wenn es viele Fehlschreibungen gibt), `{{TICKET_TEXT}}`.
- Katalog gehört in den System-Turn, damit er im Prompt-Cache liegt. Bei 3000 Tickets/Tag ist das der größte Kostenhebel — jede Katalogänderung invalidiert den Cache, also nicht stündlich deployen.
- Effort/Reasoning: aus. Ist mechanische Extraktion in engem Frame, Reasoning kostet hier nur Latenz und Geld.
- Wenn es daneben geht, zuerst die Severity-Definitionen schärfen (die tragen die Judgment-Last), nicht Beispiele nachschieben. Erst wenn das nicht reicht, ein sechstes Beispiel für die tatsächlich häufigste Fehlklasse — vorher Baseline messen.
- Modellwechsel oder Snapshot-Wechsel → Hold-out-Set neu laufen lassen, bevor es live geht.

---

## TASK 2

**Das ist kein Config-File-Eintrag, sondern ein Hook.** Grund, kurz: eine Regel in der Projekt-Config ist beratend. Das Modell liest sie und darf begründet dagegen entscheiden — meistens hält sie, und genau das ist schlimmer als gar keine Regel, weil sie zuverlässig aussieht. "Ohne Ausnahme" bekommst du nur deterministisch. Zwei Ebenen, beide brauchst du:

**Offene Frage, die ich nicht raten will:** was genau soll bei jedem Commit passieren? Unten steht ein lauffähiges Gerüst mit Lint + Typecheck + Secret-Scan als Platzhalter. Sag mir die echte Aktion, dann tausche ich nur die Kommandozeilen.

---

### Ebene 1: Git-Hook — greift bei jedem Commit, egal wer committet

`.githooks/pre-commit` (im Repo, wird mitversioniert):

```bash
#!/usr/bin/env bash
# Runs on every commit. Non-zero exit aborts the commit.
set -euo pipefail

fail() { echo "pre-commit: $1" >&2; exit 1; }

# Only staged files — checking the whole tree makes the hook slow enough
# that people start using --no-verify, which defeats the point.
staged=$(git diff --cached --name-only --diff-filter=ACM)
[ -z "$staged" ] && exit 0

npm run lint -- $staged   || fail "lint failed"
npm run typecheck         || fail "typecheck failed"

if git diff --cached | grep -nE '(sk-[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY|SUPABASE_SERVICE_ROLE_KEY *=)'; then
  fail "possible secret in staged diff — move it to .env and update .env.example"
fi
```

Aktivieren, einmal pro Klon:

```bash
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
```

`.git/hooks/` wird nicht mitversioniert, deshalb `core.hooksPath` auf einen Ordner im Repo. Setz die `git config`-Zeile ins Setup-Skript bzw. in ein `postinstall`, sonst hat ein frischer Klon den Hook nicht.

Ehrlicher Vorbehalt, ohne den die Garantie eine Lüge wäre: `git commit --no-verify` umgeht jeden lokalen Git-Hook. Wirklich ausnahmslos wird es erst, wenn dieselben Checks zusätzlich in der CI auf dem Branch laufen und der Merge ohne grünen Check blockiert ist. Der lokale Hook ist die schnelle Rückmeldung, die CI ist die Durchsetzung.

---

### Ebene 2: Claude-Code-Hook — greift bei jedem Commit, den ein Agent absetzt

`.claude/settings.json` im Projekt:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/commit-gate.sh",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

`.claude/hooks/commit-gate.sh`:

```bash
#!/usr/bin/env bash
# PreToolUse gate. Receives the tool call as JSON on stdin.
# Exit 2 blocks the tool call and shows stderr to the agent.
set -uo pipefail

cmd=$(jq -r '.tool_input.command // ""')

# Not a commit → let it through untouched.
case "$cmd" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

# Refuse the bypass explicitly, otherwise the gate is decorative.
case "$cmd" in
  *--no-verify*|*-n\ *)
    echo "Commit blocked: --no-verify is not permitted in this project." >&2
    exit 2 ;;
esac

cd "$CLAUDE_PROJECT_DIR" || exit 0

if ! out=$(.githooks/pre-commit 2>&1); then
  echo "Commit blocked by pre-commit checks:" >&2
  echo "$out" >&2
  exit 2
fi
exit 0
```

```bash
chmod +x .claude/hooks/commit-gate.sh
```

Der Claude-Hook ruft bewusst dasselbe Skript wie der Git-Hook auf. Zwei getrennte Check-Listen driften auseinander, und dann bestimmt der Zufall, welche Ebene gerade greift.

---

### Testfälle

1. **Typisch:** Datei mit Lint-Fehler stagen, `git commit -m "x"` → Commit bricht ab, Fehlerausgabe nennt die Datei. Danach Fehler beheben, gleicher Commit läuft durch.
2. **Kanonischer Edge Case (irrelevanter Input):** `git commit` mit ausschließlich gelöschten Dateien im Staging, also `staged` leer → Hook beendet sauber mit 0, Commit geht durch. Ein Gate, das leere Diffs blockiert, wird innerhalb einer Woche umgangen.
3. **Hauptconstraint (Ausnahmslosigkeit):** Agent versucht `git commit --no-verify -m "quick fix"` → Tool-Call wird geblockt, Begründung landet im Agent-Kontext. Zweiter Teil desselben Tests: dieselbe Zeile manuell im Terminal → läuft durch, und genau das ist die Lücke, die die CI schließen muss. Wenn dieser Teil nicht ausdrücklich rot ist, hältst du deine Absicherung für stärker als sie ist.

**Failure Signature:** Commits gehen durch, ohne dass Hook-Output erscheint — dann ist `core.hooksPath` im Klon nicht gesetzt oder das Skript nicht ausführbar. Umgekehrte Variante: der Hook feuert bei jedem Bash-Call statt nur bei Commits, weil das `case`-Matching zu breit ist, und macht jeden Befehl langsam.

**Usage Notes:**
- Ersetz die drei Check-Blöcke im `pre-commit` durch das, was bei dir wirklich laufen soll. Alles andere bleibt gleich.
- Halt den Hook unter etwa fünf Sekunden. Ein langsamer Pre-Commit-Hook ist die häufigste Ursache dafür, dass ein Team sich `--no-verify` angewöhnt, und dann schützt dich nur noch die CI.
- Der `jq`-Aufruf setzt `jq` im PATH voraus. Fehlt es, exit 0 wäre stillschweigendes Durchwinken — dann lieber vorher prüfen und mit exit 2 blocken.
- In die Projekt-Config (CLAUDE.md) gehört zu dem Thema höchstens ein Einzeiler, der auf den Hook zeigt. Die Regel selbst dort zu wiederholen kostet in jedem Turn Tokens und suggeriert eine Garantie, die die Datei nicht geben kann.
