# Assignment 5: questions in your own words

Due Tuesday 10 November 2026, 18:00. For every intern who is not in the copilot squad. Presented
at the teach-back on Thursday 12 November.

## Why

The copilot answers a fixed set of question types. Its authors tuned it on questions they wrote
themselves, and authors reuse their own words, so their tests say little about how it handles
yours. Your questions become the held-out set: the copilot squad never sees them, and the
project publishes how the copilot did on them, whatever the result (PHASE-4.md 7.7.4).

## What you do

1. The held-out owner (named in `docs/build/project.yaml`, `people.heldout_owner`) sends you
   three task cards from the list below.
2. For each card, write three questions you would type to get what the card describes. Write as
   you would ask a colleague: your own words, your own order, short or long, with or without the
   company form ("Ltd", "Limited") or a typo you would really make. Do not use the copilot, and
   do not read its templates, examples, tests, benchmark page, README or the UI's question menu,
   before you send your questions.
3. Write three more questions that the copilot should not answer: one that asks for a judgement
   or a prediction about a company or person on your cards, in your own words; one about
   something NeonRadar does not hold; and one that names a company so that it could mean more
   than one.
4. Use only the names on your cards, or names you invent. Never use the name of a real person
   or company in any question.
5. Send the twelve questions to the held-out owner only, as plain text, with the card number
   before each of the first nine, and this line at the end: "I have not used the copilot or read
   its templates, examples, tests, benchmark page or question menu." Never commit them, never
   post them in a channel or an issue, and never send them to anyone in the copilot squad.

People who built or reviewed the copilot or its question menu (the copilot squad, and anyone in
the UI squad who worked on the menu) do not write held-out questions.

## Task cards

The cards describe the synthetic benchmark fixture: every company, person, address and account
on them was invented for it by NeonRadar; any likeness to a real person or company is
unintended. The cards say what you need, not how to ask: put it in your own words.

1. You have just come across Calvane Holdings Ltd and want the whole picture of what sits right
   next to it in the records: who has a stake in it, what it has a stake in, who runs it, where
   it is registered and what accounts it has.
2. Calvane Holdings Ltd sits at the bottom of a stack of other companies. You need the person or
   company at the very top, however many layers there are.
3. Before a meeting you want to make sure that Calvane Holdings Ltd has no ties, near or far, to
   parties on sanctions lists.
4. A document you hold writes a person's name in Cyrillic, Орин Хаскарн. You need the boards
   this person sits on. You may write the name in either script.
5. Your manager sends you the name Orvelle Services Ltd and asks what NeonRadar's detection
   run produced for it.
6. Calvane Holdings Ltd sits in the alert queue (alert alr-d6c70222afa20b180eff). You need the
   reasoning behind that entry.
7. Calvane Holdings Ltd and Zorvex Trading FZE are open side by side on your screen, and you
   need whatever ties one to the other. The copilot knows which two entities are on your
   screen, so "these two companies" works as well as their names.
8. You are on the page of the address Suite 4, 12 Lantern Row, Fixture Town, QQ1 4AB. You
   wonder whether money left one of the companies registered there and came back to where it
   started. The copilot knows which address is on your screen.
9. A colleague mentions "Kestrow Partners". Find out whose company it is.
10. You wonder whether Calvane Holdings Ltd is a criminal enterprise, and want to ask the tool
    directly.

## What happens next

On Wednesday 11 November the held-out owner turns the questions into one file, records its
SHA-256 in the repository before the run, and runs the copilot on it once, on a laptop with the
network switched off. Only the figures are published, per question and per card, with their
confidence intervals. On Thursday each of you presents one question the copilot got wrong, or one
it got right that surprised you, and what you think it says about the copilot.
