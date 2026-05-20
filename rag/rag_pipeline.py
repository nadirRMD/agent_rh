from __future__ import annotations

from pathlib import Path

from openai import OpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter


BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "data" / "RH_files"
CHROMA_DIR = BASE_DIR / "vector_db"
EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingsAdapter:
    """Minimal LangChain-compatible embeddings wrapper around the OpenAI SDK."""

    def __init__(self, model: str = EMBEDDING_MODEL):
        self.client = OpenAI()
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float",
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float",
        )
        return response.data[0].embedding


def load_pdfs(pdf_dir: Path) -> list:
    """Charge tous les PDF du dossier et retourne une liste de Documents."""
    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"Aucun PDF trouvé dans: {pdf_dir}")

    documents = []
    for pdf_file in pdf_files:
        loader = PyPDFLoader(str(pdf_file))
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = pdf_file.name
        documents.extend(docs)
    return documents


def split_documents(documents: list):
    """Découpe les documents en chunks pour l'indexation vectorielle."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""],
    )
    return text_splitter.split_documents(documents)


def build_vector_db(chunks: list):
    """Construit et persiste la base vectorielle Chroma."""
    embeddings = OpenAIEmbeddingsAdapter()
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="rh_files",
    )
    return vectordb


def main():
    print("1. PDF -> Loader")
    documents = load_pdfs(PDF_DIR)
    print(f"   Documents chargés: {len(documents)}")

    print("2. Documents -> TextSplitter")
    chunks = split_documents(documents)
    print(f"   Chunks créés: {len(chunks)}")

    print("3. Chunks -> Vector DB")
    vectordb = build_vector_db(chunks)
    print(f"   Vector DB créée dans: {CHROMA_DIR}")

    print("Pipeline terminé.")
    return vectordb


if __name__ == "__main__":
    main()
