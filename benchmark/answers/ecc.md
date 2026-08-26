## TASK 1 — Ticket-Extraktion, produktionsreifer Prompt

**Diagnose Ausgangs-Anfrage**

Stark: drei Felder klar benannt, Volumen genannt. Fehlt: Definition von Severity (jeder Mensch zieht die Grenze anders), Produkt-Liste (freier Text driftet), was bei Mehrdeutigkeit passiert, Output-Format, Kosten-/Latenz-Rahmen.

| Problem | Folge | Fix im Prompt unten |
|---|---|---|
| "Severity" undefiniert | Modell erfindet eigene Skala, Ergebnisse nicht vergleichbar über Zeit | Rubrik mit 4 Stufen + Entscheidungsregel |
| Produktname freier Text | "Billing", "billing module", "Rechnungs-Tool" = drei Werte für ein Produkt | Closed List + `product_verbatim` als Fallback |
| Refund binär ohne Definition | "Ich überlege zu kündigen" wird zu Refund-Ticket, Queue füllt sich mit Falschpositiven | Explizite Ja/Nein-Grenze + Beleg-Zitat Pflicht |
| Kein Unsicherheits-Signal | Falsches Label geht still in Routing | `confidence` + `needs_review` |
| Kein Output-Kontrakt | Parser bricht bei Prosa-Vorspann | JSON-only, Schema fest |

**Offene Punkte, die nur du beantworten kannst:** Produkt-Liste (unten Platzhalter), ob Echtzeit-Routing nötig oder Batch reicht, ob Tickets Anhänge/Verläufe enthalten.

---

### System-Prompt (copy-paste, Platzhalter füllen)

```
You extract three structured fields from customer support tickets. You are a
classifier, not an assistant. You never answer the ticket, never write to the
customer, and never speculate beyond the ticket text.

## Products (closed list)
<products>
Aurora Billing
Aurora Checkout
Aurora Mobile SDK
Aurora Dashboard
Aurora API
</products>
[REPLACE with your real product list. Keep names exactly as they should appear
in your database — this list is the source of truth for the `product` field.]

Rules for `product`:
- Pick the ONE list value the ticket is about. Match on meaning, not spelling:
  "the billing module", "invoices page", "Rechnungen" -> "Aurora Billing".
- If the ticket names something outside the list, or names nothing at all, set
  `product` to null and put the customer's own wording (or "") in
  `product_verbatim`.
- If two products are named, choose the one the customer is reporting a problem
  with, not the one merely mentioned as context. If genuinely both, choose the
  one named first and set needs_review to true.
- NEVER invent a product that is not in the list.

## Severity rubric
Judge business impact for the customer, from the ticket text only. Ignore how
angry the tone is — anger is not severity.

- "critical": service is fully unusable, data is lost or exposed, money moved
  incorrectly, security incident, or the customer states many users/whole team
  are blocked.
- "high": a core function is broken for this customer and no workaround is
  mentioned or obvious. Work is blocked but scope is one customer/account.
- "medium": something is broken or degraded but a workaround exists, is
  mentioned, or the customer is still able to work.
- "low": question, how-to, feature request, cosmetic issue, billing enquiry
  without an error, or feedback with no malfunction.

Tie-break rule: when a ticket sits between two levels, choose the LOWER level and
set needs_review to true. Over-escalation costs more than a second look.

## Refund
`refund_requested` is true ONLY when the customer explicitly asks for money back
in this ticket: refund, money back, reverse the charge, chargeback, credit the
amount, cancel and refund, "erstatten", "Geld zurück".

It is FALSE for all of these, no exceptions:
- threatening to cancel, asking to cancel, asking about cancellation terms
- complaining about price, asking for a discount or a cheaper plan
- disputing that an invoice is correct without asking for money back
- asking whether a refund would be possible in the abstract ("what is your
  refund policy?") -> false
- an agent or your own system mentioning refunds

When true, `refund_evidence` MUST contain the customer's own words that
triggered it, copied verbatim, max 20 words. If you cannot quote it, it is false.

## Unknown handling
If the ticket is empty, unreadable, non-text (e.g. only an attachment
reference), or in a language you cannot parse: product=null, severity="low",
refund_requested=false, confidence="low", needs_review=true.
Never guess to fill a field.

## Output
Return ONE JSON object and nothing else. No markdown fence, no commentary.

{
  "product": string|null,
  "product_verbatim": string,
  "severity": "critical"|"high"|"medium"|"low",
  "severity_reason": string,          // max 15 words, cite the ticket
  "refund_requested": boolean,
  "refund_evidence": string,          // verbatim quote, "" when false
  "confidence": "high"|"medium"|"low",
  "needs_review": boolean
}

## Examples

Ticket: "Since the update this morning nobody on our team can log into the
dashboard. We have 40 agents sitting idle."
{"product":"Aurora Dashboard","product_verbatim":"dashboard","severity":"critical","severity_reason":"whole team of 40 blocked from login","refund_requested":false,"refund_evidence":"","confidence":"high","needs_review":false}

Ticket: "Invoice PDF export is broken in Safari. Works in Chrome so we use that
for now. Also, honestly considering moving to a competitor at this price."
{"product":"Aurora Billing","product_verbatim":"Invoice PDF export","severity":"medium","severity_reason":"export fails in Safari, Chrome workaround in use","refund_requested":false,"refund_evidence":"","confidence":"high","needs_review":false}

Ticket: "You charged me twice for March. Please reverse the second charge."
{"product":"Aurora Billing","product_verbatim":"charged me twice","severity":"critical","severity_reason":"duplicate charge, money moved incorrectly","refund_requested":true,"refund_evidence":"Please reverse the second charge","confidence":"high","needs_review":false}

Ticket: "hi"
{"product":null,"product_verbatim":"","severity":"low","severity_reason":"no content to classify","refund_requested":false,"refund_evidence":"","confidence":"low","needs_review":true}
```

### User-Message-Template

```
<ticket id="{{ticket_id}}">
{{subject}}

{{body}}
</ticket>

Return the JSON object for this ticket.
```

`ticket_id` bewusst nicht im JSON-Schema — kommt aus deinem Code, nicht aus dem Modell. Sonst halluziniert es IDs.

### Betrieb bei ein paar tausend/Tag

- **Modell:** kleinste Klasse (Haiku-Klasse) reicht für Extraktion mit dieser Rubrik. Erst hochgehen, wenn der Eval-Set-Score es verlangt, nicht vorsorglich.
- **temperature 0**, sonst wackeln Labels bei identischen Tickets.
- **Prompt Caching** auf den System-Block. Er ist statisch und lang, das Ticket ist kurz — bei dem Volumen der größte Hebel.
- **Batch-Verarbeitung**, wenn Routing nicht in Sekunden passieren muss. Halber Preis.
- **Structured Output / Tool-Schema** nutzen statt auf JSON-Prosa zu hoffen, wenn dein SDK es anbietet. Dann Schema-Block oben als Doku behalten.
- **Fallback im Code:** JSON-Parse schlägt fehl → einmal retry, dann Ticket in `needs_review`-Queue. Nie stillschweigend droppen.

### Bevor das live geht

50 echte Tickets von Hand labeln, gemischt: 10 offensichtliche, 10 Grenzfälle Severity, 10 Refund-Falschpositiv-Kandidaten (kündigen/Rabatt/Policy-Frage), 10 mehrdeutiges Produkt, 10 Müll-Tickets. Das ist dein Regressionstest. Kennzahlen, die zählen:

- Refund-**Precision** (Falschpositive verstopfen die Erstattungs-Queue)
- Severity-Verwechslungsmatrix, speziell critical↔high
- Anteil `needs_review` — über ~15 % heißt Rubrik zu unscharf, nicht Modell zu schwach

Rubrik ändern → Eval-Set neu laufen lassen. Ohne das merkst du Drift erst, wenn ein critical-Ticket drei Tage liegt.

---

## TASK 2 — "auf jedem Commit, ohne Ausnahme"

Hier muss ich bremsen, denn so wie formuliert würde die Anforderung nicht halten.

**Kernpunkt: die Projekt-Config-Datei ist der falsche Ort für "ohne Ausnahme".**

`CLAUDE.md` ist beratend. Sie wird als Text in den Kontext geladen, und ein Modell darf begründet abweichen, überliest sie in langen Sessions oder priorisiert sie gegen andere Anweisungen. "Meistens" ist damit erreichbar, "ausnahmslos" nicht. Wer eine Garantie will, braucht etwas Deterministisches, das außerhalb des Modells läuft. Zwei Ebenen, je nachdem was du wirklich abdecken willst:

**Ebene A — Commits über Claude Code:** Hook in `.claude/settings.json` (im Projekt, nicht global).

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/on-commit.sh"
          }
        ]
      }
    ]
  }
}
```

Das Skript bekommt den Tool-Call als JSON auf stdin, prüft selbst, ob es ein `git commit` ist, und blockt mit Exit-Code 2 (stderr geht zurück ans Modell als Begründung).

**Ebene B — jeder Commit, auch deiner im Terminal:** echter Git-Hook, versioniert.

```bash
mkdir -p .githooks
git config core.hooksPath .githooks   # einmalig pro Clone
```

`.githooks/pre-commit`, `chmod +x`, `set -euo pipefail`, non-zero Exit blockt den Commit.

Ebene A allein deckt genau die Commits ab, die durch Claude Code laufen. Wenn "ohne Ausnahme" wörtlich gemeint ist, brauchst du B — oder, falls es auch bei umgangenem lokalen Hook (`--no-verify`) halten muss, zusätzlich einen Server-seitigen CI-Check als Required Check auf dem Branch. Lokale Hooks sind per Design umgehbar.

**Was ich brauche, bevor ich das schreibe:**

1. Was ist "this"? Der konkrete Befehl/Check entscheidet über die Ebene — Formatter (darf Dateien ändern, gehört nach B), Lint-Gate (blockend, A+B), Logging/Notification (nicht blockend), Commit-Message-Regel (`commit-msg`, nicht `pre-commit`).
2. Welches Projekt? Ich stehe gerade in `~/.claude`, nicht in einem Repo. Pfad nennen, dann lege ich Hook plus Skript dort an.
3. Blockend oder nur meldend? Blockend heißt: du kommst bei kaputtem Check nicht mehr durch, auch nicht im Notfall. Bewusste Entscheidung, keine Nebenwirkung.

Sag mir 1–3, dann liegt das in einem Zug fertig da — Skript, Settings-Eintrag, und ein Testlauf mit einem Wegwerf-Commit, damit belegt ist, dass es wirklich greift.
