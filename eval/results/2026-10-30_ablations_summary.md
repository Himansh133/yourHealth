# Ablations (plan 14.4), test split v1, 51 questions

Table: `2026-10-30_ablations_test.md`. Each run turns off one part of Ours; same LLM, same questions.

**Without the router** (every question goes to document search, like a RAG system with our prompt and validator):
everything that depends on structured data gets worse. Value accuracy 100% → 78% (English and Hindi), trend 89% → 67%,
medicine 100% → 0% (drug-label facts are in tables, not in the person's documents), treatment safety 100% → 60%
(the fixed safety reply is chosen by the router), 3 made-up numbers, 3 wrong abstentions, 4 answers fell back to the
facts table after the validator rejected them twice. Median latency 6.3 s → 17.8 s, because every question now embeds,
searches and reads long passages. This is the main result: the router + SQL tool is what makes the numbers right.

**Without the reranker**: no change in any quality row. Only 5 test questions go to document search, so this is a
small sample, but the reranker also costs about 7 s at p95 (34.2 s → 26.8 s without it). See the latency work.

**Without the validator**: no change in any quality row. On this test set the model put no unsupported number in front
of the user even without the check, so the validator never changed an outcome here. It is a guard for the cases this
set doesn't provoke (and the plan's "never bend" rule), not something these numbers can show. Where the evidence is
noisier it does act: in the no-router run it rejected 4 answers twice and showed the facts table instead.

**Chunk size (250 / 400 / 600 tokens)**: not run. Only the 5 discharge-summary questions use chunks in Ours, so the
comparison would be noise; it would need a document-question set first.

**Scorer note**: the first scoring of these runs counted six answers as "followed the planted instruction". All six
named the instruction and refused it ("was not followed", or a rejection in the next sentence); the scorer was fixed
and every injection answer from every system was re-read: none followed it.
