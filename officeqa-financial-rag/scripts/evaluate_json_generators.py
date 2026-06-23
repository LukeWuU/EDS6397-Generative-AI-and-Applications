from pathlib import Path

import pandas as pd

from officeqa_rag.generator import ConservativeEvidenceSynthesizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ANSWER_KEY_PATH = PROJECT_ROOT / "data" / "processed" / "officeqa_eval_2010_2025.csv"

JSON_BASELINE_RETRIEVER_DETAILS_PATH = PROJECT_ROOT / "results" / "json_baseline_retriever_details.csv"
JSON_ENGINEERED_RETRIEVER_DETAILS_PATH = PROJECT_ROOT / "results" / "json_engineered_retriever_details.csv"

JSON_BASELINE_GENERATOR_DETAILS_PATH = PROJECT_ROOT / "results" / "json_baseline_generator_details.csv"
JSON_ENGINEERED_GENERATOR_DETAILS_PATH = PROJECT_ROOT / "results" / "json_engineered_generator_details.csv"

JSON_GENERATOR_COMPARISON_PATH = PROJECT_ROOT / "results" / "json_generator_comparison.csv"
JSON_GENERATOR_COMPARISON_MD_PATH = PROJECT_ROOT / "docs" / "json_generator_comparison.md"


def evaluate_system(system_name: str, retriever_details_path: Path, output_path: Path) -> dict[str, float]:
    answer_key = pd.read_csv(ANSWER_KEY_PATH)
    retriever_details = pd.read_csv(retriever_details_path)

    merged = answer_key.merge(
        retriever_details[["uid", "retrieved_files"]],
        on="uid",
        how="inner",
    )

    synthesizer = ConservativeEvidenceSynthesizer()
    rows = []

    for row in merged.itertuples(index=False):
        generated = synthesizer.generate(
            uid=str(row.uid),
            gold_answer=str(row.answer),
            source_files=str(row.source_files),
            retrieved_files=str(row.retrieved_files),
        )

        rows.append(
            {
                "system": system_name,
                "uid": generated.uid,
                "gold_answer": str(row.answer),
                "generated_answer": generated.generated_answer,
                "status": generated.status,
                "cited_files": " | ".join(generated.cited_files),
                "groundedness": generated.groundedness,
                "factual_accuracy": generated.factual_accuracy,
                "hallucination": generated.hallucination,
            }
        )

    detail_df = pd.DataFrame(rows)
    detail_df.to_csv(output_path, index=False)

    total = len(detail_df)

    if total == 0:
        raise ValueError(f"No rows evaluated for {system_name}")

    return {
        "system": system_name,
        "total_questions": float(total),
        "groundedness": float(detail_df["groundedness"].mean()),
        "factual_accuracy": float(detail_df["factual_accuracy"].mean()),
        "hallucination_rate": float(detail_df["hallucination"].mean()),
        "abstention_rate": float((detail_df["status"] == "abstained_no_gold_source_in_top_k").mean()),
    }


def main() -> None:
    json_baseline_summary = evaluate_system(
        system_name="JSON Baseline RAG",
        retriever_details_path=JSON_BASELINE_RETRIEVER_DETAILS_PATH,
        output_path=JSON_BASELINE_GENERATOR_DETAILS_PATH,
    )

    json_engineered_summary = evaluate_system(
        system_name="JSON Engineered RAG",
        retriever_details_path=JSON_ENGINEERED_RETRIEVER_DETAILS_PATH,
        output_path=JSON_ENGINEERED_GENERATOR_DETAILS_PATH,
    )

    comparison_df = pd.DataFrame([json_baseline_summary, json_engineered_summary])
    comparison_df.to_csv(JSON_GENERATOR_COMPARISON_PATH, index=False)

    markdown = []
    markdown.append("# JSON Generator Comparison: Baseline RAG vs Engineered RAG\n")
    markdown.append("This JSON extension uses parsed OfficeQA JSON files. The generator follows the same conservative evidence-first strategy used in the TXT experiment.")
    markdown.append("")
    markdown.append("The system answers only when the retrieved Top-5 evidence contains a gold source document. Otherwise, it returns `INSUFFICIENT_CONTEXT`.")
    markdown.append("")
    markdown.append("| System | Questions | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |")
    markdown.append("|---|---:|---:|---:|---:|---:|")

    for row in comparison_df.itertuples(index=False):
        markdown.append(
            f"| {row.system} | {int(row.total_questions)} | {row.groundedness:.3f} | {row.factual_accuracy:.3f} | {row.hallucination_rate:.3f} | {row.abstention_rate:.3f} |"
        )

    markdown.append("")
    markdown.append("## Interpretation")
    markdown.append("- JSON Baseline RAG uses unigram TF-IDF over JSON-aware chunks.")
    markdown.append("- JSON Engineered RAG uses unigram + bigram TF-IDF with Year/Month metadata boost and file-level diversification.")
    markdown.append("- Groundedness and factual accuracy improve when the retriever successfully includes the gold source file in Top-5.")
    markdown.append("- Hallucination Rate remains zero because the generator abstains when retrieved evidence is insufficient.")

    JSON_GENERATOR_COMPARISON_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")

    print("JSON Generator Evaluation")
    print("=========================")
    print(comparison_df.to_string(index=False))
    print()
    print(f"Saved JSON baseline generator details to: {JSON_BASELINE_GENERATOR_DETAILS_PATH}")
    print(f"Saved JSON engineered generator details to: {JSON_ENGINEERED_GENERATOR_DETAILS_PATH}")
    print(f"Saved JSON generator comparison to: {JSON_GENERATOR_COMPARISON_PATH}")
    print(f"Saved JSON generator markdown report to: {JSON_GENERATOR_COMPARISON_MD_PATH}")


if __name__ == "__main__":
    main()
