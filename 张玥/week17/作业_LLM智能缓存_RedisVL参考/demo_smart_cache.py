"""LLM Smart Cache 作业演示脚本。"""

from __future__ import annotations

import numpy as np
import redis

from llm_cache import EmbeddingsCache, Route, SemanticCache, SemanticMessageHistory, SemanticRouter
from llm_cache.utils import deterministic_embedding


def check_redis() -> None:
    client = redis.Redis(host="localhost", port=6379)
    client.ping()


def demo_embeddings_cache() -> None:
    print("\n=== 1. EmbeddingsCache ===")
    cache = EmbeddingsCache(name="week17_demo_embeddings", ttl=3600)
    cache.clear()
    text = "我想了解 Redis 语义缓存"
    vector = deterministic_embedding(text)[0]
    cache.store(text, vector)
    cached = cache.call(text)
    print("缓存命中：", cached is not None)
    print("向量维度：", cached.shape[0] if isinstance(cached, np.ndarray) else None)


def demo_semantic_cache() -> None:
    print("\n=== 2. SemanticCache ===")
    cache = SemanticCache(
        name="week17_demo_semantic",
        embedding_method=deterministic_embedding,
        distance_threshold=0.6,
    )
    cache.clear_cache()
    cache.store("如何办理退货", "请在订单详情页提交退货申请。", metadata={"source": "faq"})
    hits = cache.check("我想退货应该怎么办")
    miss = cache.check("今天北京天气怎么样")
    print("相似问题命中：", hits[0]["response"] if hits else None)
    print("不相关问题命中数量：", len(miss))


def demo_message_history() -> None:
    print("\n=== 3. SemanticMessageHistory ===")
    history = SemanticMessageHistory(name="week17-demo-session", embedding_method=deterministic_embedding)
    history.clear_history()
    history.add_messages(
        [
            {"role": "user", "content": "你好，我想咨询退货流程"},
            {"role": "llm", "content": "可以在订单详情页申请退货。"},
            {"role": "user", "content": "如果商品坏了怎么办？", "metadata": {"topic": "after_sale"}},
        ]
    )
    print("最近消息：", history.get_recent(top_k=2))
    print("相关消息：", history.get_relevant("退货怎么申请", top_k=2))


def demo_router() -> None:
    print("\n=== 4. SemanticRouter ===")
    router = SemanticRouter(name="week17_demo_router", embedding_method=deterministic_embedding, distance_threshold=0.55)
    router.add_route(Route(name="greeting", references=["你好", "早上好"], target="greeting_agent"))
    router.add_route(Route(name="refund", references=["如何退货", "我要退款"], target="refund_agent"))
    router.add_route(Route(name="tech_support", references=["系统报错", "登录失败"], target="support_agent"))

    print("问候路由：", router.route("你好呀"))
    print("退款路由：", router.route("我想退货"))
    print("技术支持路由：", router.route("登录一直失败"))


def main() -> None:
    check_redis()
    demo_embeddings_cache()
    demo_semantic_cache()
    demo_message_history()
    demo_router()


if __name__ == "__main__":
    main()
