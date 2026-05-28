"""狼人杀游戏核心数据结构。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    VILLAGER = "villager"


class Camp(StrEnum):
    GOOD = "good"
    EVIL = "evil"


class PlayerStyle(StrEnum):
    CAUTIOUS = "cautious"
    AGGRESSIVE = "aggressive"
    RANDOM = "random"
    BALANCED = "balanced"


ROLE_CN = {
    Role.WEREWOLF: "狼人",
    Role.SEER: "预言家",
    Role.WITCH: "女巫",
    Role.HUNTER: "猎人",
    Role.VILLAGER: "村民",
}

STYLE_CN = {
    PlayerStyle.CAUTIOUS: "谨慎型",
    PlayerStyle.AGGRESSIVE: "激进型",
    PlayerStyle.RANDOM: "随机型",
    PlayerStyle.BALANCED: "平衡型",
}


def role_camp(role: Role) -> Camp:
    return Camp.EVIL if role == Role.WEREWOLF else Camp.GOOD


@dataclass
class Player:
    id: int
    name: str
    role: Role
    style: PlayerStyle
    alive: bool = True

    @property
    def camp(self) -> Camp:
        return role_camp(self.role)


@dataclass
class DialogueRecord:
    day: int
    phase: str
    player_id: int
    player_name: str
    role: str
    content: str
    visible_to: str = "public"


@dataclass
class VoteRecord:
    day: int
    voter_id: int
    target_id: int
    reason: str


@dataclass
class DeathRecord:
    day: int
    player_id: int
    role: str
    reason: str


@dataclass
class NightRecord:
    day: int
    wolf_target: int | None = None
    seer_check: dict[str, Any] | None = None
    witch_save: int | None = None
    witch_poison: int | None = None
    deaths: list[DeathRecord] = field(default_factory=list)


@dataclass
class PlayerView:
    """发送给 Agent 的隔离视角。"""

    day: int
    self_id: int
    self_name: str
    role: Role
    style: PlayerStyle
    alive_players: list[int]
    public_deaths: list[dict[str, Any]]
    public_dialogues: list[dict[str, Any]]
    public_votes: list[dict[str, Any]]
    wolf_teammates: list[int] = field(default_factory=list)
    seer_results: dict[int, Camp] = field(default_factory=dict)
    witch_antidote_available: bool = False
    witch_poison_available: bool = False
    tonight_killed: int | None = None
    experience_tips: list[str] = field(default_factory=list)


@dataclass
class GameRecord:
    game_id: str
    config_name: str
    players: list[Player]
    dialogues: list[DialogueRecord] = field(default_factory=list)
    nights: list[NightRecord] = field(default_factory=list)
    votes: list[VoteRecord] = field(default_factory=list)
    deaths: list[DeathRecord] = field(default_factory=list)
    winner: Camp | None = None
    day_count: int = 0
    review: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_plain(asdict(self))


def _to_plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, StrEnum):
        return str(value)
    return value
