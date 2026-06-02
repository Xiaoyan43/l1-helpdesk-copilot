"""知识库加载 + 检索（RAG 的 R）。

可插拔后端：
- 装了 sentence-transformers → 语义向量检索（首次会下载小模型）。
- 否则回落到 BM25（rank-bm25，纯 Python，已随基础依赖安装）。
两者接口一致：search(query, k) -> [(Article, score)]。
"""
import re
from dataclasses import dataclass
from pathlib import Path

from .config import get_settings
from .data_io import PROJECT_ROOT

_HEADER_RE = re.compile(r"#\s*(KB\d+)\s*[—\-:]\s*(.+)")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class Article:
    id: str
    title: str
    text: str


def load_articles(kb_dir: str | Path) -> list[Article]:
    path = Path(kb_dir)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    articles: list[Article] = []
    for p in sorted(path.glob("*.md")):
        raw = p.read_text(encoding="utf-8")
        m = _HEADER_RE.match(raw.splitlines()[0]) if raw.strip() else None
        aid, title = (m.group(1), m.group(2).strip()) if m else (p.stem, p.stem)
        articles.append(Article(id=aid, title=title, text=raw))
    return articles


def _tokenize(s: str) -> list[str]:
    return _TOKEN_RE.findall(s.lower())


class Retriever:
    def __init__(self, articles: list[Article]):
        self.articles = articles
        self.mode = "bm25"
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            import numpy as np

            self._np = np
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._emb = self._model.encode(
                [a.text for a in self.articles], normalize_embeddings=True
            )
            self.mode = "embeddings"
        except Exception:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi([_tokenize(a.text) for a in self.articles])
            self.mode = "bm25"

    def search(self, query: str, k: int = 2) -> list[tuple[Article, float]]:
        if not self.articles:
            return []
        if self.mode == "embeddings":
            q = self._model.encode([query], normalize_embeddings=True)[0]
            scores = self._emb @ q
            order = self._np.argsort(-scores)[:k]
            return [(self.articles[i], float(scores[i])) for i in order]
        scores = self._bm25.get_scores(_tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [(self.articles[i], float(scores[i])) for i in order]


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(load_articles(get_settings().kb_dir))
    return _retriever
