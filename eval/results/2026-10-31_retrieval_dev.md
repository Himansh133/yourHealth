# Long-document retrieval development probe

development diagnostic; dense retrieval only, no full-text fusion or answer generation

| Words | System | MRR | Recall@1 | Recall@3 | Recall@6 | Recall@10 |
|---|---|---|---|---|---|---|
| 190 | dense | 0.579 | 0.500 | 0.500 | 0.833 | 1.000 |
| 190 | dense+reranker | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 300 | dense | 0.694 | 0.500 | 1.000 | 1.000 | 1.000 |
| 300 | dense+reranker | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 450 | dense | 0.722 | 0.500 | 1.000 | 1.000 | 1.000 |
| 450 | dense+reranker | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Six synthetic questions over three similar long discharge notes. This small development probe
does not establish a general reranker benefit or replace the frozen 90-question test.
