from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks



class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        chunks = []
        current = []
        
        for sen in sentences:
            current.append(sen)
            if len(current) >= self.max_sentences_per_chunk:
                chunks.append(' '.join(current))
                current = []
        
        if current:
            chunks.append(" ".join(current))
        
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size
        self.fixed_size_chunker = FixedSizeChunker(chunk_size = self.chunk_size, overlap=0)

    def chunk(self, text: str) -> list[str]:
        if len(text) == 0:
            return []
        results = self._split(text, self.separators)
        return [chunk.strip() for chunk in results if chunk and chunk.strip()]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if len(current_text) <= self.chunk_size:
            return [current_text]
        if len(remaining_separators) == 0:
            return self.fixed_size_chunker.chunk(current_text)

        sep = remaining_separators[0]
        if sep == "":
            return self.fixed_size_chunker.chunk(current_text)

        parts = current_text.split(sep)
        if len(parts) == 1:
            return self._split(current_text, remaining_separators[1:])

        grouped: list[str] = []
        buffer = ""

        for part in parts:
            if not part:
                continue
            candidate = part if not buffer else f"{buffer}{sep}{part}"
            if len(candidate) <= self.chunk_size:
                buffer = candidate
            else:
                if buffer:
                    grouped.append(buffer)
                if len(part) <= self.chunk_size:
                    buffer = part
                else:
                    grouped.extend(self._split(part, remaining_separators[1:]))
                    buffer = ""

        if buffer:
            grouped.append(buffer)

        result: list[str] = []
        for chunk in grouped:
            if len(chunk) <= self.chunk_size:
                result.append(chunk)
            else:
                result.extend(self._split(chunk, remaining_separators[1:]))
        return result


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    mag_a = math.sqrt(_dot(vec_a, vec_a))
    mag_b = math.sqrt(_dot(vec_b, vec_b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (mag_a * mag_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=max(0, chunk_size // 10)),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }

        def _stats(chunks: list[str]) -> dict:
            if not chunks:
                return {"count": 0, "avg_length": 0.0, "chunks": []}

            lengths = [len(c) for c in chunks]
            return {
                "count": len(chunks),
                "avg_length": round(sum(lengths) / len(lengths), 2),
                "chunks": chunks,
            }

        result: dict = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text) if text else []
            result[name] = _stats(chunks)

        return result
