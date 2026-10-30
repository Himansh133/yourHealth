# 1. Introduction

## 1.1 The problem

In many Indian households, lab reports arrive as PDFs and phone photos on WhatsApp, from different labs, in
different formats and sometimes in different units. One family member usually manages the health of several others:
parents with diabetes or thyroid disease, grandparents on blood-pressure medicines. They want to know simple things:

- Is Papa's HbA1c coming down since he started metformin?
- Dadi's sodium was marked low: is that linked to one of her medicines?
- What did the discharge summary say about follow-up?

Answering these today means scrolling through chat history and comparing numbers by hand across reports. Explaining
them to an elderly relative often means doing it in Hindi.

## 1.2 What YourHealth does

YourHealth is a family health report tracker. A user adds family members, then uploads their reports on the web or
sends them to a WhatsApp bot. The system:

1. reads lab values from PDFs and photos into a table (test, value, unit, reference range, date);
2. draws a trend chart for each test, marked with the dates medicines were started or stopped;
3. keeps each person's medicine list and shows which of their lab values each medicine is known to affect, citing the
   official drug label;
4. answers questions about the reports in English or Hindi, with every claim linked to its source;
5. builds a one-page doctor visit sheet that can be shared with a doctor through a QR code and a PIN.

## 1.3 Design principle: numbers never come from the language model

The most common objection to "an AI for medical reports" is that a language model can invent a value or give unsafe
advice. YourHealth is built so that it can't put an invented number in front of the user:

- Values are extracted by OCR and a rule-based parser, stored in SQL, and charted from SQL.
- The language model only phrases evidence it is given. A validator rejects any answer that contains a number not
  present in the evidence it cites, and any advice to start, stop or change a medicine.
- Questions about choosing or stopping a medicine get a fixed reply that defers to the doctor.
- Medicine effects come from a curated table in which every row cites a section of a public drug label, not from the
  model's memory.

## 1.4 Objectives

1. Extract lab values from Indian lab reports, including phone photos, accurately enough to chart them.
2. Link a person's medicines to their lab values using label-sourced facts, without claiming cause.
3. Answer questions in English and Hindi with citations, and decline when the reports don't answer the question or
   when the question asks for medical advice.
4. Let a family share a summary with a doctor safely: time-limited, PIN-protected, revocable and audited.
5. Measure all of the above against baselines on data with known answers.

## 1.5 Scope

In scope: family profiles, web and WhatsApp upload, extraction, trends, medicines and their known lab effects,
question answering in English and Hindi, the doctor sheet with QR sharing, and the evaluation harness.

Out of scope, and stated as future work: integration with ABHA / ABDM health records, doctor accounts, handwritten
prescriptions, medicine reminders, imaging, and any diagnosis or dose advice.

## 1.6 Contributions

- A working system covering the full path: from a WhatsApp photo to a trend chart, a cited answer in Hindi and a
  shareable doctor sheet.
- A question router that sends value and trend questions to SQL, medicine questions to a label-sourced tool, and
  only document questions to retrieval. Section 8 shows this is what makes the answers right: removing it drops
  medicine answers from 100% to 0% and lets made-up numbers through.
- An answer validator and a Hindi translation check that guarantee no unsupported number and no medicine advice
  reaches the user.
- A synthetic evaluation set with planted hard cases (degraded photos, SI units, absent tests, prompt injection) and a
  comparison against a plain-LLM and a vector-RAG baseline.

## 1.7 Report outline

Chapter 2 covers background and data sources. Chapter 3 describes the system design. Chapters 4–7 cover reading
reports, medicines, question answering and sharing. Chapter 8 is the evaluation, and Chapter 9 concludes with
limitations and future work.
