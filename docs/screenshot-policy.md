# Screenshot and video policy

A checklist to run before you publish any screenshot or recording of NeonRadar.

## 1. Required on screen
- [ ] The synthetic demo notice is visible in the screenshot or video (source: docs/wording.md, "Synthetic demo notice").

## 2. Data
- [ ] Every id on screen starts with `syn-` (source: docs/research/2026-10-18-detection/synthetic-transactions.md:263).
- [ ] No real person or company appears next to a pattern; public demos use synthetic data only (source: docs/decisions/0006-data-licensing.md:57).

## 3. Secrets
- [ ] The `.env` file is not open or printed anywhere on screen; it holds the Neo4j password (source: docs/architecture/local-stack.md:34).
- [ ] No password is visible in the terminal or in Neo4j Browser: run `clear` before recording (an earlier command such as `grep -i neo4j .env` stays in the history), and connect to Neo4j Browser before you start, so the login screen is never recorded (source: docs/architecture/local-stack.md:53).

## 4. Words (on screen and in the voice-over)
- [ ] Next to an entity, say "pattern" or "matches the graph pattern of ...", never "money laundering", "suspicious activity", "laundered funds", "shell company", "mule" or "fraudster" (source: docs/wording.md, "Vocabulary for entity-facing text").
- [ ] Pattern strength is never called a "risk score", "suspicion score" or "likelihood of laundering": it measures how closely the evidence matches the pattern, not a probability (source: docs/wording.md, "Vocabulary for entity-facing text").

## 5. Your own screen
- [ ] Only the windows needed for the demo are open: no email, chats or personal tabs.
- [ ] Notifications are off (system updates, messaging apps).
- [ ] No one else's personal data is visible, such as names or phone numbers from a group chat.