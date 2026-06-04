"""Embedding 缓存组件。

参考 RedisVL 的 EmbeddingsCache 思路：把文本到向量的结果缓存到 Redis，
避免相同文本反复调用 embedding 模型。
"""

from __future__ import annotations

from typing import Union

import numpy as np

from .utils import create_redis_client, ensure_text_list, iter_redis_keys, text_hash


class EmbeddingsCache:
    def __init__(
        self,
        name: str,
        ttl: int = 3600 * 24,
        redis_url: str = "localhost",
        redis_port: int = 6379,
        redis_password: str | None = None,
    ) -> None:
        self.name = name
        self.ttl = ttl
        self.redis = create_redis_client(redis_url, redis_port, redis_password)

    def _key(self, text: str) -> str:
        return f"{self.name}:embedding:{text_hash(text)}"

    def store(self, text: Union[list[str], str], embedding: np.ndarray) -> list[bool]:
        """写入单条或批量 embedding。"""
        texts, _ = ensure_text_list(text)
        vectors = np.asarray(embedding, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if len(texts) != vectors.shape[0]:
            raise ValueError("文本数量必须和 embedding 第一维数量一致")

        results = []
        with self.redis.pipeline() as pipe:
            for item, vector in zip(texts, vectors):
                key = self._key(item)
                pipe.hset(
                    key,
                    mapping={
                        "text": item,
                        "dtype": str(vector.dtype),
                        "dim": str(vector.shape[0]),
                        "data": vector.astype(np.float32).tobytes(),
                    },
                )
                pipe.expire(key, self.ttl)
            results = pipe.execute()
        return [bool(result) for result in results]

    def call(self, text: Union[list[str], str]) -> np.ndarray | list[np.ndarray | None] | None:
        """读取缓存。

        单条文本返回 `np.ndarray | None`，批量文本返回列表。
        """
        texts, single = ensure_text_list(text)
        keys = [self._key(item) for item in texts]
        outputs: list[np.ndarray | None] = []

        with self.redis.pipeline() as pipe:
            for key in keys:
                pipe.hgetall(key)
            rows = pipe.execute()

        for row in rows:
            if not row:
                outputs.append(None)
                continue
            dim = int(row[b"dim"])
            vector = np.frombuffer(row[b"data"], dtype=np.float32).reshape(dim)
            outputs.append(vector)

        return outputs[0] if single else outputs

    def delete(self, text: Union[list[str], str]) -> int:
        """删除指定文本的 embedding 缓存。"""
        texts, _ = ensure_text_list(text)
        keys = [self._key(item) for item in texts]
        if not keys:
            return 0
        return int(self.redis.delete(*keys))

    def clear(self) -> int:
        """清空当前命名空间下的 embedding 缓存。"""
        keys = list(iter_redis_keys(self.redis, f"{self.name}:embedding:*"))
        if not keys:
            return 0
        return int(self.redis.delete(*keys))
