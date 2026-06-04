"""语义对话历史组件。"""

from __future__ import annotations

import json
from typing import Any, Callable

import numpy as np

from .utils import create_redis_client, deterministic_embedding, normalize_vectors


class SemanticMessageHistory:
    def __init__(
        self,
        name: str,
        ttl: int = 3600 * 24,
        redis_url: str = "localhost",
        redis_port: int = 6379,
        redis_password: str | None = None,
        embedding_method: Callable[[str | list[str]], Any] | None = None,
    ) -> None:
        self.name = name
        self.ttl = ttl
        self.redis = create_redis_client(redis_url, redis_port, redis_password, decode_responses=True)
        self.embedding_method = embedding_method or deterministic_embedding

    @property
    def _key(self) -> str:
        return f"semantic_history:{self.name}:messages"

    def add_message(self, message: dict[str, Any]) -> None:
        """追加单条消息。"""
        self.add_messages([message])

    def add_messages(self, messages: list[dict[str, Any]]) -> None:
        """追加多条消息。"""
        with self.redis.pipeline() as pipe:
            for message in messages:
                if "role" not in message or "content" not in message:
                    raise ValueError("message 必须包含 role 和 content")
                pipe.rpush(self._key, json.dumps(message, ensure_ascii=False))
            pipe.expire(self._key, self.ttl)
            pipe.execute()

    def get_history(self) -> list[dict[str, Any]]:
        """获取完整历史。"""
        return [json.loads(item) for item in self.redis.lrange(self._key, 0, -1)]

    def get_recent(self, role: str | list[str] | None = None, top_k: int = 10) -> list[dict[str, Any]]:
        """获取最近消息，可按 role 过滤。"""
        history = self.get_history()
        if role is not None:
            roles = {role} if isinstance(role, str) else set(role)
            history = [message for message in history if message.get("role") in roles]
        return history[-top_k:] if top_k else history

    def get_relevant(self, content: str, top_k: int = 5) -> list[dict[str, Any]]:
        """按语义相似度检索相关历史消息。"""
        history = self.get_history()
        if not history:
            return []

        texts = [message.get("content", "") for message in history]
        query_vector = normalize_vectors(np.asarray(self.embedding_method(content), dtype=np.float32))[0]
        doc_vectors = normalize_vectors(np.asarray(self.embedding_method(texts), dtype=np.float32))
        scores = doc_vectors @ query_vector
        ranked = sorted(zip(history, scores), key=lambda item: float(item[1]), reverse=True)

        results = []
        for message, score in ranked[:top_k]:
            result = dict(message)
            result["score"] = round(float(score), 4)
            results.append(result)
        return results

    def clear_history(self) -> int:
        """清空当前 session 历史。"""
        return int(self.redis.delete(self._key))
