# Retriever Comparison: Baseline RAG vs Engineered RAG

Evaluation uses the filtered OfficeQA Pro answer key for 2010-2025 with K=5.

| System | Retriever Design | Questions | Hit Rate@5 | MRR | Recall@5 |
|---|---|---:|---:|---:|---:|
| Baseline RAG | TF-IDF unigram search; no metadata filtering; fixed 350-word chunks with 80-word overlap | 22 | 0.318 | 0.183 | 0.265 |
| Engineered RAG | TF-IDF unigram+bigram search; soft Year/Month metadata boost; file-level diversification | 22 | 0.773 | 0.670 | 0.606 |

## Improvement
- Hit Rate@5 improved by 0.455.
- MRR improved by 0.487.
- Recall@5 improved by 0.341.