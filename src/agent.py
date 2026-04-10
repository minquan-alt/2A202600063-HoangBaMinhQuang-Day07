from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self._store = store
        self._llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        retrieved = self._store.search(question, top_k=top_k)
        context_lines = []
        for idx, item in enumerate(retrieved, start=1):
            content = item.get("content", "")
            score = item.get("score", 0.0)
            context_lines.append(f"[{idx}] (score={score:.4f}) {content}")

        context_text = "\n".join(context_lines) if context_lines else "No relevant context found."
        prompt = (
            "You are a helpful assistant. Answer the question using the provided context.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        return self._llm_fn(prompt)
