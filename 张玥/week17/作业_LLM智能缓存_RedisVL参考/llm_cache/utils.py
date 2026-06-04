"""缓存组件共享工具函数。"""

from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np
import redis


def create_redis_client(
    redis_url: str = "localhost",
    redis_port: int = 6379,
    redis_password: str | None = None,
    decode_responses: bool = False,
) -> redis.Redis:
    """创建 Redis 客户端。

    这里保留课程原始代码中的 host/port 写法，方便连接 Docker Redis。
    """
    return redis.Redis(
        host=redis_url,
        port=redis_port,
        password=redis_password,
        decode_responses=decode_responses,
    )


def text_hash(text: str) -> str:
    """使用 md5 生成稳定 key，避免中文和特殊字符直接进入 Redis key。"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def ensure_text_list(text: str | list[str]) -> tuple[list[str], bool]:
    """把单条文本统一转换成列表，并记录原始输入是否为单条。"""
    if isinstance(text, str):
        return [text], True
    return list(text), False


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """把向量归一化，便于用内积近似 cosine similarity。"""
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def deterministic_embedding(text: str | list[str], dims: int = 64) -> np.ndarray:
    """本地确定性 embedding，用于无 API Key 的教学演示。

    它不是生产级 embedding 模型，只是把字符映射到固定维度向量中。
    相似文本通常会共享部分字符，因此能满足作业中的语义缓存和路由演示。
    """
    texts, _ = ensure_text_list(text)
    rows = []
    for item in texts:
        vector = np.zeros(dims, dtype=np.float32)
        for char in item.lower():
            if char.isspace():
                continue
            digest = hashlib.md5(char.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % dims
            vector[index] += 1.0
        rows.append(vector)
    return normalize_vectors(np.vstack(rows))


def decode_bytes(value: bytes | str | None) -> str | None:
    """兼容 Redis bytes 和 str 返回值。"""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def iter_redis_keys(redis_client: redis.Redis, pattern: str) -> Iterable[bytes]:
    """按 pattern 扫描 Redis key，避免生产中直接 keys 全量阻塞。"""
    yield from redis_client.scan_iter(match=pattern)
