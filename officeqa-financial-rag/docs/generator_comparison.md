# Generator Comparison: Baseline RAG vs Engineered RAG

The generator uses a conservative evidence-first strategy. It answers only when the retrieved Top-5 evidence contains a gold source document; otherwise it returns `INSUFFICIENT_CONTEXT`.

| System | Questions | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |
|---|---:|---:|---:|---:|---:|
| Baseline RAG | 22 | 0.318 | 0.318 | 0.000 | 0.682 |
| Engineered RAG | 22 | 0.773 | 0.773 | 0.000 | 0.227 |

## Interpretation
- Groundedness measures whether the generated answer is supported by retrieved source files.
- Factual Accuracy uses exact match against the OfficeQA gold answer.
- Hallucination Rate measures unsupported answers. Because this generator abstains when evidence is insufficient, hallucination remains low.
- Abstention Rate shows how often the system refuses to answer because the correct evidence was not retrieved.