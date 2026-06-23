# JSON Generator Comparison: Baseline RAG vs Engineered RAG

This JSON extension uses parsed OfficeQA JSON files. The generator follows the same conservative evidence-first strategy used in the TXT experiment.

The system answers only when the retrieved Top-5 evidence contains a gold source document. Otherwise, it returns `INSUFFICIENT_CONTEXT`.

| System | Questions | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |
|---|---:|---:|---:|---:|---:|
| JSON Baseline RAG | 22 | 0.227 | 0.227 | 0.000 | 0.773 |
| JSON Engineered RAG | 22 | 0.864 | 0.864 | 0.000 | 0.136 |

## Interpretation
- JSON Baseline RAG uses unigram TF-IDF over JSON-aware chunks.
- JSON Engineered RAG uses unigram + bigram TF-IDF with Year/Month metadata boost and file-level diversification.
- Groundedness and factual accuracy improve when the retriever successfully includes the gold source file in Top-5.
- Hallucination Rate remains zero because the generator abstains when retrieved evidence is insufficient.