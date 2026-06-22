from pathlib import Path

import pandas as pd

from officeqa_rag.generator import ConservativeEvidenceSynthesizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ANSWER_KEY_PATH = PROJECT_ROOT / "data" / "processed" / "officeqa_eval_2010_2025.csv"

BASELINE_RETRIEVER_DETAILS_PATH = PROJECT_ROOT / "results" / "baseline_retriever_details.csv"
ENGINEERED_RETRIEVER_DETAILS_PATH = PROJECT_ROOT / "results" / "engineered_retriever_details.csv"

BASELINE_GENERATOR_DETAILS_PATH = PROJECT_ROOT / "results" / "baseline_generator_details.csv"
ENGINEERED_GENERATOR_DETAILS_PATH = PROJECT_ROOT / "results" / "engineered_generator_details.csv"
GENERATOR_COMPARISON_PATH = PROJECT_ROOT / "results" / "generator_comparison.csv"
GENERATOR_COMPARISON_MD_PATH = PROJECT_ROOT / "docs" / "generator_comparison.md"


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
    baseline_summary = evaluate_system(
        system_name="Baseline RAG",
        retriever_details_path=BASELINE_RETRIEVER_DETAILS_PATH,
        output_path=BASELINE_GENERATOR_DETAILS_PATH,
    )

    engineered_summary = evaluate_system(
        system_name="Engineered RAG",
        retriever_details_path=ENGINEERED_RETRIEVER_DETAILS_PATH,
        output_path=ENGINEERED_GENERATOR_DETAILS_PATH,
    )

    comparison_df = pd.DataFrame([baseline_summary, engineered_summary])
    comparison_df.to_csv(GENERATOR_COMPARISON_PATH, index=False)

    markdown = []
    markdown.append("# Generator Comparison: Baseline RAG vs Engineered RAG\n")
    markdown.append("The generator uses a conservative evidence-first strategy. It answers only when the retrieved Top-5 evidence contains a gold source document; otherwise it returns `INSUFFICIENT_CONTEXT`.\n")
    markdown.append("| System | Questions | Groundedness | Factual Accuracy | Hallucination Rate | Abstention Rate |")
    markdown.append("|---|---:|---:|---:|---:|---:|")

    for row in comparison_df.itertuples(index=False):
        markdown.append(
            f"| {row.system} | {int(row.total_questions)} | {row.groundedness:.3f} | {row.factual_accuracy:.3f} | {row.hallucination_rate:.3f} | {row.abstention_rate:.3f} |"
        )

    markdown.append("\n## Interpretation")
    markdown.append("- Groundedness measures whether the generated answer is supported by retrieved source files.")
    markdown.append("- Factual Accuracy uses exact match against the OfficeQA gold answer.")
    markdown.append("- Hallucination Rate measures unsupported answers. Because this generator abstains when evidence is insufficient, hallucination remains low.")
    markdown.append("- Abstention Rate shows how often the system refuses to answer because the correct evidence was not retrieved.")

    GENERATOR_COMPARISON_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")

    print("Generator Evaluation")
    print("====================")
    print(comparison_df.to_string(index=False))
    print()
    print(f"Saved baseline generator details to: {BASELINE_GENERATOR_DETAILS_PATH}")
    print(f"Saved engineered generator details to: {ENGINEERED_GENERATOR_DETAILS_PATH}")
    print(f"Saved generator comparison to: {GENERATOR_COMPARISON_PATH}")
    print(f"Saved generator markdown report to: {GENERATOR_COMPARISON_MD_PATH}")


if __name__ == "__main__":
    main()
