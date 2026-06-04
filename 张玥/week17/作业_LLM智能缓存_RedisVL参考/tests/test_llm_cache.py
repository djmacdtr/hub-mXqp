"""LLM Smart Cache 单元测试。"""

from __future__ import annotations

import unittest

import numpy as np
import redis

from llm_cache import EmbeddingsCache, Route, SemanticCache, SemanticMessageHistory, SemanticRouter
from llm_cache.utils import deterministic_embedding


class LLMCacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.redis = redis.Redis(host="localhost", port=6379)
        cls.redis.ping()

    def test_embeddings_cache(self) -> None:
        cache = EmbeddingsCache(name="test_embeddings_cache", ttl=3600)
        cache.clear()
        text = "hello redis cache"
        vector = deterministic_embedding(text)[0]

        cache.store(text, vector)
        cached = cache.call(text)

        self.assertIsInstance(cached, np.ndarray)
        self.assertEqual(cached.shape[0], vector.shape[0])
        self.assertEqual(cache.delete(text), 1)
        self.assertIsNone(cache.call(text))

    def test_semantic_cache(self) -> None:
        cache = SemanticCache(
            name="test_semantic_cache",
            embedding_method=deterministic_embedding,
            distance_threshold=0.6,
            runtime_dir="runtime/tests",
        )
        cache.clear_cache()
        cache.store("如何办理退货", "请在订单详情页提交退货申请。")

        hit = cache.check("我想退货怎么办")
        miss = cache.check("明天上海天气如何")

        self.assertTrue(hit)
        self.assertEqual(hit[0]["response"], "请在订单详情页提交退货申请。")
        self.assertEqual(miss, [])

    def test_message_history(self) -> None:
        history = SemanticMessageHistory(
            name="test-session",
            embedding_method=deterministic_embedding,
        )
        history.clear_history()
        history.add_messages(
            [
                {"role": "user", "content": "你好，我想退货"},
                {"role": "llm", "content": "请在订单详情页申请退货"},
                {"role": "user", "content": "系统登录失败"},
            ]
        )

        self.assertEqual(len(history.get_history()), 3)
        self.assertEqual(history.get_recent(role="user", top_k=1)[0]["content"], "系统登录失败")
        relevant = history.get_relevant("退货流程", top_k=1)
        self.assertIn("退货", relevant[0]["content"])

    def test_semantic_router(self) -> None:
        router = SemanticRouter(
            name="test_router",
            embedding_method=deterministic_embedding,
            distance_threshold=0.55,
            runtime_dir="runtime/tests",
        )
        router.add_route(Route(name="greeting", references=["你好", "早上好"], target="greeting_agent"))
        router.add_route(Route(name="refund", references=["如何退货", "我要退款"], target="refund_agent"))
        router.add_route(Route(name="tech_support", references=["登录失败", "系统报错"], target="support_agent"))

        self.assertEqual(router.route("你好呀")["target"], "greeting_agent")
        self.assertEqual(router.route("我想退货")["target"], "refund_agent")
        self.assertEqual(router.route("登录失败了")["target"], "support_agent")


if __name__ == "__main__":
    unittest.main()
