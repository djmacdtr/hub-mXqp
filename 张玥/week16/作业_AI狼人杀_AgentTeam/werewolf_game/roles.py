"""狼人杀角色定义和信息边界说明。"""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import Role


@dataclass(frozen=True)
class RoleRule:
    role: Role
    goal: str
    night_action: str
    day_action: str
    private_information: str


ROLE_RULES = {
    Role.WEREWOLF: RoleRule(
        role=Role.WEREWOLF,
        goal="隐藏身份，击杀好人，使狼人数量达到或超过好人数量。",
        night_action="和狼人队友共同选择一名非狼人玩家击杀。",
        day_action="伪装成好人发言，误导投票。",
        private_information="知道自己的狼人队友。",
    ),
    Role.SEER: RoleRule(
        role=Role.SEER,
        goal="通过查验身份帮助好人找出狼人。",
        night_action="每晚查验一名玩家阵营。",
        day_action="根据查验结果决定是否公开信息。",
        private_information="只知道自己的查验结果。",
    ),
    Role.WITCH: RoleRule(
        role=Role.WITCH,
        goal="利用解药和毒药保护好人阵营。",
        night_action="可使用一次解药救人，或使用一次毒药毒人。",
        day_action="根据公开信息引导投票。",
        private_information="知道当晚被狼人击杀的玩家，以及自己的药品状态。",
    ),
    Role.HUNTER: RoleRule(
        role=Role.HUNTER,
        goal="作为强神角色，在死亡时带走可疑目标。",
        night_action="无主动夜晚行动。",
        day_action="发言分析并参与投票，死亡后可开枪。",
        private_information="知道自己是猎人。",
    ),
    Role.VILLAGER: RoleRule(
        role=Role.VILLAGER,
        goal="通过发言和投票找出狼人。",
        night_action="无夜晚行动。",
        day_action="根据公开发言、死亡和投票信息推理。",
        private_information="没有额外私有信息。",
    ),
}


def get_role_rule(role: Role) -> RoleRule:
    return ROLE_RULES[role]
