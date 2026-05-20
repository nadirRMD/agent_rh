from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma

try:
    from .rag_pipeline import CHROMA_DIR, PDF_DIR, OpenAIEmbeddingsAdapter
    from .rag_pipeline import build_vector_db, load_pdfs, split_documents
except ImportError:  # pragma: no cover - fallback for direct script execution
    from rag_pipeline import CHROMA_DIR, PDF_DIR, OpenAIEmbeddingsAdapter
    from rag_pipeline import build_vector_db, load_pdfs, split_documents


load_dotenv()

DEFAULT_LLM_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini")


def load_vector_db() -> Chroma:
    """Charge la base vectorielle Chroma persistée sur disque."""
    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"Aucune base vectorielle trouvée dans {CHROMA_DIR}. "
            "Lance d'abord `python rag/rag_pipeline.py`."
        )

    embeddings = OpenAIEmbeddingsAdapter()
    return Chroma(
        collection_name="rh_files",
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )


def ensure_vector_db() -> Chroma:
    """Charge la base vectorielle ou la reconstruit si elle n'existe pas encore."""
    if CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir()):
        return load_vector_db()

    documents = load_pdfs(PDF_DIR)
    chunks = split_documents(documents)
    return build_vector_db(chunks)


def build_retriever(k: int = 4):
    """Construit le retriever sur la base vectorielle."""
    vectordb = ensure_vector_db()
    return vectordb.as_retriever(search_kwargs={"k": k})


def format_context(docs) -> str:
    """Transforme les documents récupérés en contexte lisible pour le LLM."""
    parts: list[str] = []
    for index, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "n/a")
        parts.append(
            f"[Extrait {index} | source={source} | page={page}]\n{doc.page_content}"
        )
    return "\n\n".join(parts)


def build_qa_chain():
    """Construit une chaîne QA simple basée sur retrieval + génération."""
    retriever = build_retriever()
    llm = ChatOpenAI(
        model=DEFAULT_LLM_MODEL,
        temperature=0,
        max_retries=2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Tu es un assistant RH. Réponds uniquement avec le contexte fourni. "
                "Si l'information n'est pas dans le contexte, dis clairement que tu ne peux pas la déduire.",
            ),
            (
                "human",
                "Question:\n{question}\n\nContexte:\n{context}\n\nRéponse:",
            ),
        ]
    )
    return retriever, prompt | llm | StrOutputParser()


def answer_question(question: str) -> dict[str, object]:
    """Répond à une question en s'appuyant sur les PDF indexés."""
    retriever, chain = build_qa_chain()
    docs = retriever.invoke(question)
    context = format_context(docs)
    answer = chain.invoke({"question": question, "context": context})
    sources = sorted(
        {
            doc.metadata.get("source", "unknown")
            for doc in docs
        }
    )
    return {"question": question, "answer": answer, "sources": sources, "context": context}


def main() -> None:
    """Petit mode CLI pour tester le RAG localement."""
    question = input("Question RAG: ").strip()
    if not question:
        raise SystemExit("Aucune question fournie.")

    result = answer_question(question)
    print("\nRéponse:\n")
    print(result["answer"])
    print("\nSources:")
    for source in result["sources"]:
        print(f"- {source}")


if __name__ == "__main__":
    main()
