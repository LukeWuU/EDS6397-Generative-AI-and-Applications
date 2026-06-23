# TXT vs JSON RAG Comparison

This report compares the original TXT-based RAG pipeline with an optional JSON-based extension using parsed OfficeQA JSON files.

| System | Data Format | Questions | Hit Rate@5 | MRR | Recall@5 | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TXT Baseline RAG | Transformed TXT | 22 | 0.318 | 0.183 | 0.265 | 0.318 | 0.318 | 0.000 | 0.682 |
| TXT Engineered RAG | Transformed TXT | 22 | 0.773 | 0.670 | 0.606 | 0.773 | 0.773 | 0.000 | 0.227 |
| JSON Baseline RAG | Parsed JSON | 22 | 0.227 | 0.134 | 0.136 | 0.227 | 0.227 | 0.000 | 0.773 |
| JSON Engineered RAG | Parsed JSON | 22 | 0.864 | 0.495 | 0.674 | 0.864 | 0.864 | 0.000 | 0.136 |

## Interpretation
- TXT Baseline RAG is the simplest retrieval setup and uses transformed TXT chunks.
- TXT Engineered RAG improves retrieval by adding bigrams, Year/Month metadata boosting, and file-level diversification.
- JSON Baseline RAG performs worse than TXT Baseline because JSON-aware chunks include more structural tokens and fragmented layout information.
- JSON Engineered RAG achieves the strongest Hit Rate@5 and Recall@5, showing that parsed JSON can help when structural metadata is paired with engineered retrieval.
- JSON Engineered RAG has lower MRR than TXT Engineered RAG, meaning it often retrieves the correct file within Top-5 but not always at rank 1.
- Hallucination Rate remains zero across all systems because the conservative generator abstains when the gold source file is not retrieved.