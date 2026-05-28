"""对局复盘与经验生成。"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .memory import ExperienceMemory
from .schemas import ROLE_CN, Camp, GameRecord, Role


class GameEvaluator:
    def __init__(self, memory: ExperienceMemory | None = None) -> None:
        self.memory = memory or ExperienceMemory()

    def evaluate_and_update(self, record: GameRecord) -> dict[str, Any]:
        """生成复盘结果，并写入角色经验。"""
        if record.winner is None:
            raise ValueError("游戏尚未结束，不能复盘")

        vote_counter = Counter(vote.target_id for vote in record.votes)
        death_order = [death.player_id for death in record.deaths]
        role_tips: dict[str, list[str]] = {}

        updated_roles: set[Role] = set()
        for player in record.players:
            if player.role in updated_roles:
                continue
            updated_roles.add(player.role)
            tips = self._tips_for_role(player.role, record.winner)
            role_tips[player.role.value] = tips
            self.memory.update_role(player.role, record.winner, tips)

        review = {
            "winner": record.winner.value,
            "winner_cn": "好人阵营" if record.winner == Camp.GOOD else "狼人阵营",
            "days": record.day_count,
            "total_dialogues": len(record.dialogues),
            "total_votes": len(record.votes),
            "most_voted_player": vote_counter.most_common(1)[0][0] if vote_counter else None,
            "death_order": death_order,
            "role_tips": role_tips,
            "summary": self._summary(record),
        }
        record.review = review
        return review

    def _tips_for_role(self, role: Role, winner: Camp) -> list[str]:
        role_won = (role == Role.WEREWOLF and winner == Camp.EVIL) or (
            role != Role.WEREWOLF and winner == Camp.GOOD
        )
        if role_won:
            return [f"{ROLE_CN[role]}本局阵营获胜，下一局保持当前核心策略，并继续利用公开信息。"]

        if role == Role.WEREWOLF:
            return ["狼人阵营失败，下一局需要更积极带节奏，优先处理公开怀疑狼人的玩家。"]
        if role == Role.SEER:
            return ["预言家阵营失败，下一局应更早公开关键查验信息，帮助好人形成票型。"]
        if role == Role.WITCH:
            return ["女巫阵营失败，下一局应更谨慎使用毒药，并优先保护疑似强神。"]
        if role == Role.HUNTER:
            return ["猎人阵营失败，下一局应在发言中更明确表达怀疑对象，死亡时提高带走狼人的概率。"]
        return ["村民阵营失败，下一局应更重视历史投票和发言矛盾，避免被狼人带票。"]

    def _summary(self, record: GameRecord) -> str:
        winner = "好人阵营" if record.winner == Camp.GOOD else "狼人阵营"
        return (
            f"本局共进行 {record.day_count} 天，最终 {winner} 获胜。"
            f"共产生 {len(record.dialogues)} 条发言、{len(record.votes)} 条投票记录，"
            f"死亡顺序为 {[death.player_id for death in record.deaths]}。"
        )
