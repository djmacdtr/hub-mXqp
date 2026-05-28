"""角色经验记忆，用于轻量自进化。"""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import Camp, Role


DEFAULT_MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
DEFAULT_MEMORY_PATH = DEFAULT_MEMORY_DIR / "role_experience.json"


class ExperienceMemory:
    def __init__(self, path: Path = DEFAULT_MEMORY_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def tips_for(self, role: Role) -> list[str]:
        role_data = self.data.get(role.value, {})
        return list(role_data.get("tips", []))[-3:]

    def update_role(self, role: Role, winner: Camp, tips: list[str]) -> None:
        current = self.data.setdefault(
            role.value,
            {"games": 0, "wins": 0, "losses": 0, "tips": []},
        )
        current["games"] += 1
        role_camp = Camp.EVIL if role == Role.WEREWOLF else Camp.GOOD
        if role_camp == winner:
            current["wins"] += 1
        else:
            current["losses"] += 1
        for tip in tips:
            if tip not in current["tips"]:
                current["tips"].append(tip)
        current["tips"] = current["tips"][-8:]
        self.save()

    def reset(self) -> None:
        self.data = {}
        if self.path.exists():
            self.path.unlink()
