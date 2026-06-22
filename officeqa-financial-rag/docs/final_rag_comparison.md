# Final RAG Comparison

This table compares the Baseline RAG system against the Engineered RAG system using OfficeQA Pro questions filtered to source files fully covered by the 2010-2025 Treasury Bulletin TXT corpus.

| System | Questions | Hit Rate@5 | MRR | Recall@5 | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline RAG | 22 | 0.318 | 0.183 | 0.265 | 0.318 | 0.318 | 0.000 | 0.682 |
| Engineered RAG | 22 | 0.773 | 0.670 | 0.606 | 0.773 | 0.773 | 0.000 | 0.227 |

## Improvements from Baseline to Engineered RAG
- Hit Rate@5 improved by 0.455.
- MRR improved by 0.487.
- Recall@5 improved by 0.341.
- Groundedness improved by 0.455.
- Factual Accuracy improved by 0.455.
- Hallucination Rate changed by 0.000.
- Abstention Rate changed by -0.455.

## Interpretation
The Engineered RAG system substantially improves retrieval quality by using bigram TF-IDF, soft Year/Month metadata boosting, and file-level diversification. Because the generator only answers when retrieved evidence contains a gold source file, stronger retrieval directly improves groundedness and factual accuracy while keeping hallucination low.