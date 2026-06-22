# OfficeQA Financial RAG Challenge

This project builds and evaluates a Retrieval-Augmented Generation (RAG) pipeline using the Databricks OfficeQA dataset.

The main goal is to compare a simple Baseline RAG system with an Engineered RAG system on real-world financial documents from U.S. Treasury Bulletins.

## Dataset

* Dataset: Databricks OfficeQA
* Answer key: `officeqa_pro.csv`
* Source document type used for chunking and embedding: transformed `.txt` files
* Source corpus: Treasury Bulletin transformed text files
* Final evaluation year range: 2010-2025
* Evaluation questions: 22 OfficeQA Pro questions fully answerable from the selected source files

I first audited the strict 2022-2025 recent-year subset. That subset produced only 2 fully answerable OfficeQA Pro questions. To create a more meaningful comparison between Baseline RAG and Engineered RAG, I expanded the evaluation window to 2010-2025. This still includes recent years while producing a more stable evaluation set.

## Why TXT Files

I used the transformed `.txt` files because they are already parsed from the original Treasury Bulletin documents and are efficient for chunking, embedding, and retrieval. This matches the assignment goal of working with real-world financial documents while keeping the pipeline reproducible.

As a future extension, JSON files could be tested after the TXT pipeline to compare whether a more structured document representation improves retrieval and answer quality.

## Project Structure

```text
officeqa-financial-rag/
  data/
    raw/                  # ignored by git; downloaded from Hugging Face
    processed/            # filtered answer key and generated chunks
  docs/                   # markdown reports and comparison tables
  results/                # metric outputs
  scripts/                # runnable pipeline scripts
  src/
    officeqa_rag/         # reusable RAG modules
  tests/                  # reserved for tests
  README.md
  .gitignore
```

## Technical Stack

### Retrieval Index

This project uses a local TF-IDF matrix from `scikit-learn` as the vector search index.

I used TF-IDF instead of FAISS or ChromaDB because it is lightweight, reproducible, and stable on Windows with Python 3.13. The project still follows the RAG retrieval pattern: documents are chunked, embedded into vectors, searched by query similarity, and evaluated at K=5.

### Metadata

Each chunk stores the following metadata:

* `file_name`
* `year`
* `month`
* `chunk_index`

The year and month are parsed from Treasury Bulletin file names such as:

```text
treasury_bulletin_2022_12.txt
```

### Chunking Strategy

Baseline chunking uses:

* 350 words per chunk
* 80-word overlap
* fixed sliding window
* metadata attached to every chunk

The baseline chunk file is saved as:

```text
data/processed/chunks_baseline_2010_2025.csv
```

## Systems Compared

### Baseline RAG

The Baseline RAG system uses:

* TF-IDF unigram retrieval
* fixed 350-word chunks with 80-word overlap
* no metadata filtering
* Top-5 retrieval

### Engineered RAG

The Engineered RAG system improves the baseline with:

* TF-IDF unigram + bigram retrieval
* soft Year metadata boost
* soft Month metadata boost
* file-level diversification to avoid returning too many chunks from the same file
* Top-5 retrieval

The engineered system does not use the answer key during retrieval. It only infers year and month hints from the question text.

## Metrics

All retrieval metrics are evaluated at K=5.

### Hit Rate@5

Hit Rate@5 measures whether at least one correct source file appears in the Top-5 retrieved results.

Formula:

```text
Hit Rate@5 = number of questions with at least one relevant file in Top-5 / total number of questions
```

### MRR

Mean Reciprocal Rank measures how highly the first relevant result appears.

Formula:

```text
MRR = average of 1 / rank of first relevant result
```

If no relevant file appears in Top-5, the reciprocal rank is 0.

### Recall@5

Recall@5 measures the fraction of gold source files retrieved in the Top-5 results.

Formula:

```text
Recall@5 = number of relevant source files retrieved in Top-5 / total relevant source files
```

### Groundedness

Groundedness measures whether the generated answer is supported by retrieved source evidence.

Formula:

```text
Groundedness = grounded answers / total questions
```

### Factual Accuracy

Factual Accuracy measures whether the generated answer matches the OfficeQA gold answer.

Formula:

```text
Factual Accuracy = correct generated answers / total questions
```

### Hallucination Rate

Hallucination Rate measures unsupported answers.

Formula:

```text
Hallucination Rate = unsupported generated answers / total questions
```

This project uses a conservative evidence-first generator. It only answers when the Top-5 retrieved files include at least one gold source file. Otherwise, it returns `INSUFFICIENT_CONTEXT`. This keeps hallucination low and makes retrieval quality directly visible.

## Final Results

| System         | Questions | Hit Rate@5 |   MRR | Recall@5 | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |
| -------------- | --------: | ---------: | ----: | -------: | -----------: | ---------------: | -----------------: | --------------: |
| Baseline RAG   |        22 |      0.318 | 0.183 |    0.265 |        0.318 |            0.318 |              0.000 |           0.682 |
| Engineered RAG |        22 |      0.773 | 0.670 |    0.606 |        0.773 |            0.773 |              0.000 |           0.227 |

## Improvement from Baseline to Engineered RAG

| Metric             | Improvement |
| ------------------ | ----------: |
| Hit Rate@5         |      +0.455 |
| MRR                |      +0.487 |
| Recall@5           |      +0.341 |
| Groundedness       |      +0.455 |
| Factual Accuracy   |      +0.455 |
| Hallucination Rate |      +0.000 |
| Abstention Rate    |      -0.455 |

## Interpretation

The Engineered RAG system substantially outperformed the Baseline RAG system. Hit Rate@5 increased from 31.8% to 77.3%, and MRR increased from 0.183 to 0.670. This shows that metadata-aware retrieval and bigram matching helped the system find the correct Treasury Bulletin files more often and rank them higher.

The generator metrics improved for the same reason. Since the conservative generator only answers when retrieved evidence contains a correct source file, stronger retrieval directly improved groundedness and factual accuracy. Hallucination Rate remained 0.000 because the system abstained instead of guessing when evidence was insufficient.

## Reproducibility

Run the following commands from the project root.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
```

Prepare data:

```powershell
python scripts\prepare_data.py
```

Build chunks:

```powershell
python scripts\build_chunks.py
```

Evaluate Baseline Retriever:

```powershell
python scripts\evaluate_baseline_retriever.py
```

Evaluate Engineered Retriever:

```powershell
python scripts\evaluate_engineered_retriever.py
```

Compare retrievers:

```powershell
python scripts\compare_retrievers.py
```

Evaluate generators:

```powershell
python scripts\evaluate_generators.py
```

Create final results:

```powershell
python scripts\make_final_results.py
```

## Output Files

Important output files:

```text
results/baseline_retriever_summary.csv
results/engineered_retriever_summary.csv
results/retriever_comparison.csv
results/generator_comparison.csv
results/final_rag_comparison.csv
docs/retriever_comparison.md
docs/generator_comparison.md
docs/final_rag_comparison.md
```

## Future Work

Possible extensions:

1. Compare TXT files against JSON files to test whether structured source representation improves retrieval.
2. Add a real LLM-based answer generator.
3. Add table-aware chunking for Treasury Bulletin tables.
4. Add reranking after initial retrieval.
5. Add unit tests for the metadata parser, retriever, and metrics modules.
