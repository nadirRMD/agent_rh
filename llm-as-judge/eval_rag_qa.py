from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from rag.rag_qa import answer_question


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "rag_test_dataset.csv"
DEFAULT_OUTPUT = BASE_DIR / "rag_qa_results.csv"
DEFAULT_JUDGE_MODEL = os.getenv("OPENAI_JUDGE_MODEL", os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini"))


class JudgeResult(BaseModel):
    score: int = Field(ge=1, le=5)
    verdict: str
    justification: str


def build_judge() -> ChatOpenAI:
    return ChatOpenAI(
        model=DEFAULT_JUDGE_MODEL,
        temperature=0,
        max_retries=2,
        api_key=os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(JudgeResult)


def judge_answer(
    question: str,
    expected_answer: str,
    rag_answer: str,
    question_type: str,
) -> JudgeResult:
    judge = build_judge()
    prompt = (
        "Tu es un juge RAG strict et cohérent. "
        "Compare la réponse attendue et la réponse du RAG. "
        "Attribue un score entier de 1 à 5 selon la proximité sémantique, "
        "la fidélité au document et le respect du type de question.\n\n"
        "Règles:\n"
        "- 5: réponse équivalente, fidèle et complète.\n"
        "- 4: très proche, mineure différence de formulation ou de détail.\n"
        "- 3: partiellement correcte, manque une partie importante.\n"
        "- 2: majoritairement incorrecte ou trop vague.\n"
        "- 1: hors sujet, hallucination, ou refus inapproprié.\n\n"
        "Cas particuliers:\n"
        "- Pour une question hors corpus, une réponse qui refuse proprement reçoit un bon score.\n"
        "- Pour une question ambiguë, une réponse qui demande des précisions reçoit un bon score.\n"
        "- Ne pénalise pas une différence de style si le fond est correct.\n\n"
        f"Type de question: {question_type}\n"
        f"Question: {question}\n"
        f"Réponse attendue: {expected_answer}\n"
        f"Réponse RAG: {rag_answer}"
    )
    return judge.invoke(prompt)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate rag_qa on a CSV dataset.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Dataset not found: {input_path}")

    rows: list[dict[str, str]] = []
    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            question = (row.get("Question") or "").strip()
            if not question:
                continue

            result = answer_question(question)
            judged = judge_answer(
                question=question,
                expected_answer=row.get("Réponse attendue", "") or "",
                rag_answer=str(result["answer"]),
                question_type=row.get("Type", "") or "",
            )
            rows.append(
                {
                    "#": row.get("#", ""),
                    "Question": question,
                    "Type": row.get("Type", ""),
                    "Réponse attendue": row.get("Réponse attendue", ""),
                    "Score attendu": row.get("Score attendu", ""),
                    "Réponse RAG": str(result["answer"]),
                    "Sources": " | ".join(result["sources"]),
                    "Score juge": str(judged.score),
                    "Verdict juge": judged.verdict,
                    "Justification juge": judged.justification,
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "#",
                "Question",
                "Type",
                "Réponse attendue",
                "Score attendu",
                "Réponse RAG",
                "Sources",
                "Score juge",
                "Verdict juge",
                "Justification juge",
            ],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Evaluated {len(rows)} questions.")
    print(f"Results written to: {output_path}")


if __name__ == "__main__":
    main()
