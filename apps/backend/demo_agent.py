"""demo_agent.py — Standalone script to test the AgentOps RAG pipeline.

Run directly (outside Docker) for quick testing:
    cd agent_ops_demo/apps/backend
    python demo_agent.py

Requires:
    - Ollama running locally (ollama serve)
    - Models pulled: ollama pull qwen2.5:14b && ollama pull nomic-embed-text
    - Langfuse running: docker compose up langfuse-db langfuse
    - pip install -r requirements.txt
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.config.logging_config import setup_logging

logger = logging.getLogger("agentops.demo")


async def main() -> None:
    from src.config.settings import settings

    setup_logging(level=settings.log_level, log_format=settings.log_format)

    from src.agents.rag_agent import ask
    from src.services.rag_service import get_collection_count, ingest_documents
    from src.services.telemetry import init_telemetry

    logger.info(
        "demo_start | llm=%s base_url=%s embed=%s langfuse=%s phoenix=%s",
        settings.llm_model,
        settings.llm_base_url,
        settings.embedding_model,
        settings.langfuse_host,
        "enabled" if settings.phoenix_enabled else "disabled",
    )

    # Initialize telemetry
    logger.info("demo_step | step=1/3 action=init_telemetry")
    init_telemetry()

    # Ingest documents
    logger.info("demo_step | step=2/3 action=check_vectorstore")
    existing = get_collection_count()
    if existing == 0:
        logger.info("demo_ingest | dir=%s", settings.docs_dir)
        count = ingest_documents()
        logger.info("demo_ingest_done | chunks=%d", count)
    else:
        logger.info("demo_vectorstore_ready | docs=%d", existing)

    # Interactive loop
    logger.info("demo_step | step=3/3 action=ready")
    print("\nReady! Type your question (or 'quit' to exit).\n")

    while True:
        try:
            question = input("You: ").strip()  # noqa: ASYNC250
        except (EOFError, KeyboardInterrupt):
            break

        if not question or question.lower() in ("quit", "exit", "q"):
            break

        logger.info("demo_question | len=%d preview=%r", len(question), question[:80])

        result = await ask(question)

        print(f"\nAssistant: {result['answer']}\n")
        metrics = result["metrics"]
        print(f"  Route:       {result.get('route_type', 'unknown')}")
        print(f"  Latency:     {metrics['latency_ms']:.0f}ms")
        total = metrics["total_tokens"]
        tok_in = metrics["input_tokens"]
        tok_out = metrics["output_tokens"]
        print(f"  Tokens:      {tok_in} in \u2192 {tok_out} out ({total} total)")
        print(f"  Efficiency:  {metrics['token_efficiency']:.3f}")
        print(f"  Retrieved:   {metrics['retrieval_docs']} docs")
        if result["trace_url"]:
            print(f"  Trace URL:   {result['trace_url']}")
        if result["phoenix_url"]:
            print(f"  Phoenix:     {result['phoenix_url']}")
        print()

    logger.info("demo_exit")
    print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
