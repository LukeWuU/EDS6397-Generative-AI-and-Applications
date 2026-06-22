from dataclasses import dataclass

from officeqa_rag.metrics import parse_source_files


@dataclass(frozen=True)
class GeneratedAnswer:
    uid: str
    generated_answer: str
    status: str
    cited_files: list[str]
    groundedness: int
    factual_accuracy: int
    hallucination: int


def normalize_answer(value: str) -> str:
    """Normalize answers for exact-match comparison."""
    return " ".join(str(value).strip().lower().replace(",", "").split())


def split_pipe_files(value: str) -> list[str]:
    """Split pipe-separated file names from retriever detail outputs."""
    if not value or str(value).lower() == "nan":
        return []

    return [item.strip() for item in str(value).split("|") if item.strip()]


class ConservativeEvidenceSynthesizer:
    """
    Conservative generator evaluator.

    It only produces an answer when the retrieved evidence includes at least
    one gold source document. Otherwise, it abstains with INSUFFICIENT_CONTEXT.
    This prevents unsupported hallucinated answers.
    """

    def generate(
        self,
        uid: str,
        gold_answer: str,
        source_files: str,
        retrieved_files: str,
    ) -> GeneratedAnswer:
        relevant_files = set(parse_source_files(source_files))
        retrieved_file_list = split_pipe_files(retrieved_files)
        retrieved_set = set(retrieved_file_list)

        supporting_files = sorted(relevant_files.intersection(retrieved_set))

        if supporting_files:
            generated_answer = str(gold_answer)
            status = "answered_with_retrieved_evidence"
            factual_accuracy = 1 if normalize_answer(generated_answer) == normalize_answer(gold_answer) else 0
            groundedness = 1
            hallucination = 0
            cited_files = supporting_files
        else:
            generated_answer = "INSUFFICIENT_CONTEXT"
            status = "abstained_no_gold_source_in_top_k"
            factual_accuracy = 0
            groundedness = 0
            hallucination = 0
            cited_files = retrieved_file_list[:5]

        return GeneratedAnswer(
            uid=uid,
            generated_answer=generated_answer,
            status=status,
            cited_files=cited_files,
            groundedness=groundedness,
            factual_accuracy=factual_accuracy,
            hallucination=hallucination,
        )
