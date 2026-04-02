"""RAG service — Document ingestion + ChromaDB vector store + retrieval.

Pipeline: PDF/Text files → split → embed (Ollama) → ChromaDB → retriever
All local: embeddings via Ollama, storage via ChromaDB on disk.
"""

import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config.settings import settings

logger = logging.getLogger("agentops.service.rag")

_vectorstore: Chroma | None = None
_embeddings: OllamaEmbeddings | None = None

COLLECTION_NAME = "agentops_demo"


def _get_embeddings() -> OllamaEmbeddings:
    """Return a cached OllamaEmbeddings instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(
            base_url=settings.llm_base_url,
            model=settings.embedding_model,
        )
        logger.info("embeddings_init | model=%s", settings.embedding_model)
    return _embeddings


def get_vectorstore() -> Chroma:
    """Return the ChromaDB vector store (create if not exists)."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=_get_embeddings(),
            persist_directory=settings.chroma_persist_dir,
        )
        logger.info(
            "chromadb_init | collection=%s persist_dir=%s",
            COLLECTION_NAME,
            settings.chroma_persist_dir,
        )
    return _vectorstore


def get_retriever(k: int = 4):
    """Return a retriever from the vector store."""
    return get_vectorstore().as_retriever(search_kwargs={"k": k})


def search_with_relevance(query: str, k: int = 4) -> list[tuple]:
    """Search documents with relevance scores.

    Returns list of (Document, float) tuples sorted by descending relevance.
    Score is in [0, 1] where 1 = most relevant.
    """
    store = get_vectorstore()
    return store.similarity_search_with_relevance_scores(query, k=k)


def ingest_documents(docs_path: str | None = None) -> int:
    """Load and ingest all PDF/TXT files from a directory into ChromaDB.

    Returns the number of chunks ingested.
    """
    docs_dir = Path(docs_path or settings.docs_dir)
    if not docs_dir.exists():
        logger.warning("ingest_skip | reason=dir_not_found dir=%s", docs_dir)
        return 0

    # Collect all supported files
    files = list(docs_dir.glob("**/*.txt")) + list(docs_dir.glob("**/*.pdf"))
    if not files:
        logger.info("ingest_skip | reason=no_files dir=%s", docs_dir)
        return 0

    logger.info("ingest_start | dir=%s file_count=%d", docs_dir, len(files))

    # Load documents
    all_docs = []
    max_file_size = 50 * 1024 * 1024  # 50 MB guard
    for fpath in files:
        try:
            if fpath.stat().st_size > max_file_size:
                logger.warning(
                    "ingest_skip_large | file=%s size=%d",
                    fpath.name,
                    fpath.stat().st_size,
                )
                continue
            if fpath.is_symlink():
                logger.warning("ingest_skip_symlink | file=%s", fpath.name)
                continue
            if fpath.suffix.lower() == ".pdf":
                loader = PyPDFLoader(str(fpath))
            else:
                loader = TextLoader(str(fpath), encoding="utf-8")
            docs = loader.load()
            all_docs.extend(docs)
            logger.debug("ingest_file | file=%s pages=%d", fpath.name, len(docs))
        except Exception:
            logger.warning("ingest_file_error | file=%s", fpath, exc_info=True)

    if not all_docs:
        return 0

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(all_docs)
    logger.info(
        "ingest_split | documents=%d chunks=%d chunk_size=%d overlap=%d",
        len(all_docs),
        len(chunks),
        settings.chunk_size,
        settings.chunk_overlap,
    )

    # Ingest into ChromaDB
    store = get_vectorstore()
    store.add_documents(chunks)
    logger.info("ingest_complete | chunks=%d", len(chunks))

    return len(chunks)


def get_collection_count() -> int:
    """Return the number of documents in the vector store."""
    try:
        store = get_vectorstore()
        collection = store._collection
        return collection.count()
    except Exception:
        return 0
