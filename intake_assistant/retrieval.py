"""Tiny, dependency-free retrieval layer (BM25) over a markdown knowledge base.

Demonstrates the retrieval half of Retrieval-Augmented Generation (RAG):
chunk -> index -> rank -> cite. Swap in embeddings + a vector DB for production.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set("a an and are as at be by for from has have how i in is it of on or that the this to was what when which with you your do does can".split())


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


@dataclass
class Chunk:
    source: str
    heading: str
    text: str


@dataclass
class Hit:
    chunk: Chunk
    score: float


def load_chunks(kb_dir: Path) -> List[Chunk]:
    chunks: List[Chunk] = []
    for path in sorted(Path(kb_dir).glob("*.md")):
        heading, buf = path.stem, []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                if "".join(buf).strip():
                    chunks.append(Chunk(path.name, heading, "\n".join(buf).strip()))
                heading, buf = line.lstrip("# ").strip(), []
            else:
                buf.append(line)
        if "".join(buf).strip():
            chunks.append(Chunk(path.name, heading, "\n".join(buf).strip()))
    return chunks


class BM25Index:
    def __init__(self, chunks: List[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [tokenize(c.heading + " " + c.text) for c in chunks]
        self.avgdl = sum(map(len, self.docs)) / max(len(self.docs), 1)
        df: Counter = Counter()
        for d in self.docs:
            df.update(set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 3, min_score: float = 0.5) -> List[Hit]:
        q = tokenize(query)
        hits: List[Hit] = []
        for chunk, doc in zip(self.chunks, self.docs):
            tf = Counter(doc)
            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                num = tf[t] * (self.k1 + 1)
                den = tf[t] + self.k1 * (1 - self.b + self.b * len(doc) / self.avgdl)
                s += self.idf[t] * num / den
            if s >= min_score:
                hits.append(Hit(chunk, round(s, 3)))
        hits.sort(key=lambda h: -h.score)
        return hits[:k]
