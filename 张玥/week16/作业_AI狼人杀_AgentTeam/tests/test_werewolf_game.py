"""AI 狼人杀作业的核心流程测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from werewolf_game.api import app
from werewolf_game.engine import GameEngine
from werewolf_game.memory import ExperienceMemory
from werewolf_game.schemas import Camp, Role
from werewolf_game.tournament import run_self_evolution


class WerewolfGameTest(unittest.TestCase):
    def test_information_isolation(self) -> None:
        """不同角色只能看到自己应该知道的信息。"""
        engine = GameEngine(seed=11)
        wolf = next(player for player in engine.record.players if player.role == Role.WEREWOLF)
        villager = next(player for player in engine.record.players if player.role == Role.VILLAGER)
        seer = next(player for player in engine.record.players if player.role == Role.SEER)
        witch = next(player for player in engine.record.players if player.role == Role.WITCH)

        wolf_view = engine.build_view(wolf.id)
        villager_view = engine.build_view(villager.id)
        seer_view = engine.build_view(seer.id)
        witch_view = engine.build_view(witch.id)

        self.assertTrue(wolf_view.wolf_teammates)
        self.assertEqual(villager_view.wolf_teammates, [])
        self.assertEqual(villager_view.seer_results, {})
        self.assertIsNone(villager_view.tonight_killed)
        self.assertEqual(seer_view.role, Role.SEER)
        self.assertTrue(witch_view.witch_antidote_available)
        self.assertTrue(witch_view.witch_poison_available)

    def test_game_runs_and_writes_log(self) -> None:
        """单局对战应能跑到胜负，并落盘结构化日志。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = ExperienceMemory(root / "memory.json")
            engine = GameEngine(
                seed=12,
                memory=memory,
                log_dir=root / "logs",
                max_days=8,
            )
            record = engine.run()

            self.assertIn(record.winner, [Camp.GOOD, Camp.EVIL])
            self.assertGreaterEqual(len(record.dialogues), 1)
            self.assertGreaterEqual(len(record.votes), 1)
            self.assertTrue((root / "logs" / f"{record.game_id}.json").exists())

    def test_self_evolution_updates_memory(self) -> None:
        """多局运行后，角色经验文件应该被更新。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_self_evolution(
                rounds=2,
                seed=13,
                memory_path=root / "role_experience.json",
                log_dir=root / "logs",
            )

            self.assertEqual(result["rounds"], 2)
            self.assertTrue((root / "role_experience.json").exists())
            self.assertTrue(result["final_memory"])

    def test_fastapi_flow(self) -> None:
        """FastAPI 应支持创建、运行、查询对局。"""
        client = TestClient(app)
        index_response = client.get("/")
        self.assertEqual(index_response.status_code, 200)
        self.assertIn("AI 狼人杀 Agent Team 观战台", index_response.text)

        create_response = client.post("/games", json={"seed": 14})
        self.assertEqual(create_response.status_code, 200)
        game_id = create_response.json()["game_id"]

        run_response = client.post(f"/games/{game_id}/run")
        self.assertEqual(run_response.status_code, 200)
        self.assertIn(run_response.json()["winner"], [Camp.GOOD, Camp.EVIL])

        get_response = client.get(f"/games/{game_id}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["game_id"], game_id)


if __name__ == "__main__":
    unittest.main()
