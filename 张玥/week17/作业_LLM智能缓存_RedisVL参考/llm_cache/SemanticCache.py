"""语义缓存组件。

把“用户问题 -> LLM 回答”存入 Redis，同时用 FAISS 保存 prompt 向量。
新问题进来后，如果与历史 prompt 足够相似，就直接返回缓存回答。
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Callable, Union

import faiss
import numpy as np

from .utils import create_redis_client, deterministic_embedding, ensure_text_list, normalize_vectors


class SemanticCache:
    def __init__(
        self,
        name: str,
        embedding_method: Callable[[Union[str, list[str]]], Any] | None = None,
        ttl: int = 3600 * 24,
        redis_url: str = "localhost",
        redis_port: int = 6379,
        redis_password: str | None = None,
        distance_threshold: float = 0.35,
        runtime_dir: str | Path = "runtime",
    ) -> None:
        self.name = name
        self.ttl = ttl
        self.distance_threshold = distance_threshold
        self.embedding_method = embedding_method or deterministic_embedding
        self.redis = create_redis_client(redis_url, redis_port, redis_password)
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.runtime_dir / f"{self.name}.faiss"
        self.index = faiss.read_index(str(self.index_path)) if self.index_path.exists() else None

    @property
    def _ids_key(self) -> str:
        return f"{self.name}:semantic_cache:ids"

    def _record_key(self, record_id: str) -> str:
        return f"{self.name}:semantic_cache:record:{record_id}"

    def _embed(self, text: str | list[str]) -> np.ndarray:
        return normalize_vectors(np.asarray(self.embedding_method(text), dtype=np.float32))

    def _ensure_index(self, dims: int) -> None:
        if self.index is None:
            self.index = faiss.IndexFlatIP(dims)

    def store(
        self,
        prompt: str | list[str],
        response: str | list[str],
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """存储 prompt 和 response，并更新 FAISS 索引。"""
        prompts, _ = ensure_text_list(prompt)
        responses, _ = ensure_text_list(response)
        if len(prompts) != len(responses):
            raise ValueError("prompt 数量必须和 response 数量一致")

        embeddings = self._embed(prompts)
        self._ensure_index(embeddings.shape[1])
        self.index.add(embeddings)
        faiss.write_index(self.index, str(self.index_path))

        record_ids = []
        with self.redis.pipeline() as pipe:
            for item_prompt, item_response in zip(prompts, responses):
                record_id = uuid.uuid4().hex
                record_ids.append(record_id)
                record = {
                    "id": record_id,
                    "prompt": item_prompt,
                    "response": item_response,
                    "metadata": metadata or {},
                }
                pipe.set(self._record_key(record_id), json.dumps(record, ensure_ascii=False), ex=self.ttl)
                pipe.rpush(self._ids_key, record_id)
            pipe.expire(self._ids_key, self.ttl)
            pipe.execute()
        return record_ids

    def check(self, prompt: str, top_k: int = 1) -> list[dict[str, Any]]:
        """检查语义缓存，返回命中结果列表。"""
        if self.index is None or self.index.ntotal == 0:
            return []

        query = self._embed(prompt)
        k = min(max(top_k, 1), self.index.ntotal)
        similarities, indexes = self.index.search(query, k)
        hits: list[dict[str, Any]] = []

        for similarity, index_id in zip(similarities[0], indexes[0]):
            if index_id < 0:
                continue
            distance = 1.0 - float(similarity)
            if distance > self.distance_threshold:
                continue
            record_id = self.redis.lindex(self._ids_key, int(index_id))
            if record_id is None:
                continue
            record_id_text = record_id.decode("utf-8") if isinstance(record_id, bytes) else record_id
            raw_record = self.redis.get(self._record_key(record_id_text))
            if raw_record is None:
                continue
            record = json.loads(raw_record)
            record["similarity"] = round(float(similarity), 4)
            record["distance"] = round(distance, 4)
            hits.append(record)
        return hits

    def call(self, prompt: str, top_k: int = 1) -> list[dict[str, Any]]:
        """兼容课程原始代码中的 call 命名。"""
        return self.check(prompt, top_k=top_k)

    def clear_cache(self) -> None:
        """清空当前语义缓存。"""
        record_ids = self.redis.lrange(self._ids_key, 0, -1)
        keys = [self._record_key(item.decode("utf-8") if isinstance(item, bytes) else item) for item in record_ids]
        if keys:
            self.redis.delete(*keys)
        self.redis.delete(self._ids_key)
        if self.index_path.exists():
            self.index_path.unlink()
        self.index = None
