"""语义路由组件。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import faiss
import numpy as np

from .utils import create_redis_client, deterministic_embedding, normalize_vectors


@dataclass
class Route:
    name: str
    references: list[str]
    target: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    distance_threshold: float | None = None


class SemanticRouter:
    def __init__(
        self,
        name: str = "semantic_router",
        routes: list[Route] | None = None,
        embedding_method: Callable[[str | list[str]], Any] | None = None,
        redis_url: str = "localhost",
        redis_port: int = 6379,
        redis_password: str | None = None,
        distance_threshold: float = 0.35,
        runtime_dir: str | Path = "runtime",
    ) -> None:
        self.name = name
        self.embedding_method = embedding_method or deterministic_embedding
        self.redis = create_redis_client(redis_url, redis_port, redis_password, decode_responses=True)
        self.distance_threshold = distance_threshold
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.runtime_dir / f"{self.name}.router.faiss"
        self.index: faiss.IndexFlatIP | None = None
        self.references: list[dict[str, Any]] = []
        self.clear()
        for route in routes or []:
            self.add_route(route)

    @property
    def _refs_key(self) -> str:
        return f"{self.name}:semantic_router:references"

    def _embed(self, text: str | list[str]) -> np.ndarray:
        return normalize_vectors(np.asarray(self.embedding_method(text), dtype=np.float32))

    def _rebuild_index(self) -> None:
        if not self.references:
            self.index = None
            if self.index_path.exists():
                self.index_path.unlink()
            return
        vectors = self._embed([item["reference"] for item in self.references])
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        faiss.write_index(self.index, str(self.index_path))

    def add_route(
        self,
        route: Route | None = None,
        questions: list[str] | None = None,
        target: str | None = None,
    ) -> None:
        """新增路由。

        支持 `add_route(Route(...))`，也支持课程原始写法
        `add_route(questions=[...], target="refund")`。
        """
        if route is None:
            if not questions or not target:
                raise ValueError("必须传入 Route，或同时传入 questions 和 target")
            route = Route(name=target, references=questions, target=target)

        for reference in route.references:
            self.references.append(
                {
                    "route": route.name,
                    "target": route.target or route.name,
                    "reference": reference,
                    "metadata": route.metadata,
                    "distance_threshold": route.distance_threshold,
                }
            )
        self.redis.set(self._refs_key, json.dumps(self.references, ensure_ascii=False))
        self._rebuild_index()

    def route(self, question: str) -> dict[str, Any] | None:
        """返回最匹配的路由结果。"""
        if self.index is None or self.index.ntotal == 0:
            return None
        vector = self._embed(question)
        similarities, indexes = self.index.search(vector, 1)
        index_id = int(indexes[0][0])
        if index_id < 0:
            return None

        reference = self.references[index_id]
        similarity = float(similarities[0][0])
        distance = 1.0 - similarity
        threshold = reference.get("distance_threshold") or self.distance_threshold
        if distance > threshold:
            return None

        return {
            "name": reference["route"],
            "target": reference["target"],
            "matched_reference": reference["reference"],
            "metadata": reference["metadata"],
            "similarity": round(similarity, 4),
            "distance": round(distance, 4),
        }

    def __call__(self, question: str) -> dict[str, Any] | None:
        return self.route(question)

    def clear(self) -> None:
        """清空当前路由定义。"""
        self.redis.delete(self._refs_key)
        self.references = []
        self.index = None
        if self.index_path.exists():
            self.index_path.unlink()
