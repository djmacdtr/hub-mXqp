"""规则版角色 Agent。

默认不用大模型，保证作业在本地可稳定运行；后续可在这些方法中接入 LLM。
"""

from __future__ import annotations

import random

from .schemas import Camp, PlayerStyle, PlayerView, Role


class RoleAgent:
    def __init__(self, player_id: int, seed: int | None = None) -> None:
        self.player_id = player_id
        self.rng = random.Random(seed)

    def choose_wolf_kill(self, view: PlayerView) -> tuple[int, str]:
        candidates = [pid for pid in view.alive_players if pid != view.self_id and pid not in view.wolf_teammates]
        target = self._prefer_target(candidates, view)
        return target, "狼人夜晚优先击杀发言强势或疑似神职的玩家。"

    def choose_seer_check(self, view: PlayerView) -> tuple[int, str]:
        candidates = [pid for pid in view.alive_players if pid != view.self_id and pid not in view.seer_results]
        target = self._prefer_target(candidates, view)
        return target, "预言家优先查验尚未确认身份且发言可疑的玩家。"

    def choose_witch_action(self, view: PlayerView) -> dict:
        if view.tonight_killed is not None and view.witch_antidote_available:
            if view.tonight_killed == view.self_id or view.style in {PlayerStyle.CAUTIOUS, PlayerStyle.BALANCED}:
                return {"save": view.tonight_killed, "poison": None, "reason": "女巫使用解药避免夜晚减员。"}

        if view.witch_poison_available and view.day >= 2:
            candidates = [pid for pid in view.alive_players if pid != view.self_id and pid != view.tonight_killed]
            if candidates and view.style == PlayerStyle.AGGRESSIVE:
                target = self._prefer_target(candidates, view)
                return {"save": None, "poison": target, "reason": "女巫激进使用毒药处理可疑目标。"}

        return {"save": None, "poison": None, "reason": "女巫保留药品，继续观察。"}

    def speak(self, view: PlayerView) -> str:
        tips = "；".join(view.experience_tips) if view.experience_tips else "暂无历史经验"
        if view.role == Role.WEREWOLF:
            return f"我目前更关注发言摇摆的人。历史经验：{tips}。我建议大家不要盲目跟票。"
        if view.role == Role.SEER and view.seer_results:
            checked_id, camp = list(view.seer_results.items())[-1]
            camp_text = "好人阵营" if camp == Camp.GOOD else "狼人阵营"
            return f"我有一条查验信息：玩家{checked_id}偏向{camp_text}。大家可以结合发言判断。"
        if view.role == Role.WITCH:
            return f"我会重点观察投票异常的人。历史经验：{tips}。"
        if view.role == Role.HUNTER:
            return "我是偏强势的好人视角，会重点看谁在推动错误票型。"
        return "我没有额外信息，会根据公开发言和投票记录找矛盾点。"

    def vote(self, view: PlayerView) -> tuple[int, str]:
        candidates = [pid for pid in view.alive_players if pid != view.self_id]
        if view.role == Role.WEREWOLF:
            candidates = [pid for pid in candidates if pid not in view.wolf_teammates] or candidates

        for checked_id, camp in view.seer_results.items():
            if camp == Camp.EVIL and checked_id in candidates:
                return checked_id, "根据预言家查验信息投出狼人。"

        target = self._prefer_target(candidates, view)
        return target, "根据公开发言、历史经验和当前策略投票。"

    def hunter_shoot(self, view: PlayerView) -> tuple[int | None, str]:
        candidates = [pid for pid in view.alive_players if pid != view.self_id]
        if not candidates:
            return None, "猎人死亡时没有可带走目标。"
        return self._prefer_target(candidates, view), "猎人死亡后带走最可疑目标。"

    def _prefer_target(self, candidates: list[int], view: PlayerView) -> int:
        if not candidates:
            raise ValueError("没有可选择目标")

        if "更积极" in "".join(view.experience_tips) or view.style == PlayerStyle.AGGRESSIVE:
            return max(candidates)
        if view.style == PlayerStyle.CAUTIOUS:
            return min(candidates)
        if view.style == PlayerStyle.RANDOM:
            return self.rng.choice(candidates)
        return candidates[len(candidates) // 2]
