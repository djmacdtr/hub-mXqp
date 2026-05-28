"""狼人杀对局引擎。"""

from __future__ import annotations

import json
import random
import uuid
from collections import Counter
from pathlib import Path

from .agents import RoleAgent
from .evaluator import GameEvaluator
from .memory import ExperienceMemory
from .schemas import (
    Camp,
    DeathRecord,
    DialogueRecord,
    GameRecord,
    NightRecord,
    Player,
    PlayerStyle,
    PlayerView,
    Role,
    VoteRecord,
    role_camp,
)


DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


class GameEngine:
    def __init__(
        self,
        seed: int | None = None,
        memory: ExperienceMemory | None = None,
        log_dir: Path = DEFAULT_LOG_DIR,
        max_days: int = 8,
    ) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.memory = memory or ExperienceMemory()
        self.log_dir = log_dir
        self.max_days = max_days
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.record = self._create_record()
        self.agents = {
            player.id: RoleAgent(player.id, seed=(seed or 0) + player.id)
            for player in self.record.players
        }
        self.seer_results: dict[int, dict[int, Camp]] = {}
        self.witch_antidote_available = True
        self.witch_poison_available = True

    def _create_record(self) -> GameRecord:
        roles = [
            Role.WEREWOLF,
            Role.WEREWOLF,
            Role.SEER,
            Role.WITCH,
            Role.HUNTER,
            Role.VILLAGER,
        ]
        styles = [
            PlayerStyle.CAUTIOUS,
            PlayerStyle.AGGRESSIVE,
            PlayerStyle.RANDOM,
            PlayerStyle.BALANCED,
            PlayerStyle.CAUTIOUS,
            PlayerStyle.AGGRESSIVE,
        ]
        self.rng.shuffle(roles)
        players = [
            Player(id=i, name=f"玩家{i}", role=roles[i], style=styles[i])
            for i in range(len(roles))
        ]
        return GameRecord(
            game_id=f"game_{uuid.uuid4().hex[:10]}",
            config_name="standard_6",
            players=players,
        )

    def run(self) -> GameRecord:
        while self.record.winner is None and self.record.day_count < self.max_days:
            self.record.day_count += 1
            self._run_night(self.record.day_count)
            self._judge_winner()
            if self.record.winner is not None:
                break
            self._run_day(self.record.day_count)
            self._judge_winner()

        if self.record.winner is None:
            self.record.winner = self._fallback_winner()

        GameEvaluator(self.memory).evaluate_and_update(self.record)
        self.save_log()
        return self.record

    def _run_night(self, day: int) -> None:
        night = NightRecord(day=day)
        alive_wolves = [p for p in self.alive_players() if p.role == Role.WEREWOLF]

        if alive_wolves:
            choices = []
            for wolf in alive_wolves:
                view = self.build_view(wolf.id)
                target, _reason = self.agents[wolf.id].choose_wolf_kill(view)
                choices.append(target)
            night.wolf_target = Counter(choices).most_common(1)[0][0]

        for seer in [p for p in self.alive_players() if p.role == Role.SEER]:
            view = self.build_view(seer.id)
            target, _reason = self.agents[seer.id].choose_seer_check(view)
            result = role_camp(self.player(target).role)
            self.seer_results.setdefault(seer.id, {})[target] = result
            night.seer_check = {"seer_id": seer.id, "target_id": target, "camp": result.value}

        killed = night.wolf_target
        for witch in [p for p in self.alive_players() if p.role == Role.WITCH]:
            view = self.build_view(witch.id, tonight_killed=killed)
            action = self.agents[witch.id].choose_witch_action(view)
            if action["save"] is not None and self.witch_antidote_available:
                night.witch_save = action["save"]
                self.witch_antidote_available = False
                if killed == action["save"]:
                    killed = None
            if action["poison"] is not None and self.witch_poison_available:
                night.witch_poison = action["poison"]
                self.witch_poison_available = False

        deaths: list[int] = []
        if killed is not None:
            deaths.append(killed)
        if night.witch_poison is not None and night.witch_poison not in deaths:
            deaths.append(night.witch_poison)

        for player_id in deaths:
            death = self._kill_player(player_id, day, "night")
            if death:
                night.deaths.append(death)

        self.record.nights.append(night)

    def _run_day(self, day: int) -> None:
        for player in self.alive_players():
            view = self.build_view(player.id)
            content = self.agents[player.id].speak(view)
            self.record.dialogues.append(
                DialogueRecord(
                    day=day,
                    phase="day_speech",
                    player_id=player.id,
                    player_name=player.name,
                    role=player.role.value,
                    content=content,
                )
            )

        vote_records = []
        for player in self.alive_players():
            view = self.build_view(player.id)
            target, reason = self.agents[player.id].vote(view)
            if self.player(target).alive:
                vote_records.append(VoteRecord(day=day, voter_id=player.id, target_id=target, reason=reason))

        self.record.votes.extend(vote_records)
        if not vote_records:
            return
        exile_target = Counter(vote.target_id for vote in vote_records).most_common(1)[0][0]
        self._kill_player(exile_target, day, "vote")

    def _kill_player(self, player_id: int, day: int, reason: str) -> DeathRecord | None:
        player = self.player(player_id)
        if not player.alive:
            return None
        player.alive = False
        death = DeathRecord(day=day, player_id=player.id, role=player.role.value, reason=reason)
        self.record.deaths.append(death)

        if player.role == Role.HUNTER:
            view = self.build_view(player.id)
            target, shoot_reason = self.agents[player.id].hunter_shoot(view)
            if target is not None and self.player(target).alive:
                self._kill_player(target, day, f"hunter_shoot:{shoot_reason}")
        return death

    def build_view(self, player_id: int, tonight_killed: int | None = None) -> PlayerView:
        player = self.player(player_id)
        alive_ids = [p.id for p in self.alive_players()]
        wolf_teammates = []
        if player.role == Role.WEREWOLF:
            wolf_teammates = [
                p.id for p in self.record.players
                if p.role == Role.WEREWOLF and p.id != player.id
            ]

        return PlayerView(
            day=self.record.day_count,
            self_id=player.id,
            self_name=player.name,
            role=player.role,
            style=player.style,
            alive_players=alive_ids,
            public_deaths=[
                {"day": d.day, "player_id": d.player_id, "reason": d.reason}
                for d in self.record.deaths
            ],
            public_dialogues=[
                {"day": d.day, "player_id": d.player_id, "content": d.content}
                for d in self.record.dialogues
            ],
            public_votes=[
                {"day": v.day, "voter_id": v.voter_id, "target_id": v.target_id}
                for v in self.record.votes
            ],
            wolf_teammates=wolf_teammates,
            seer_results=self.seer_results.get(player.id, {}),
            witch_antidote_available=self.witch_antidote_available if player.role == Role.WITCH else False,
            witch_poison_available=self.witch_poison_available if player.role == Role.WITCH else False,
            tonight_killed=tonight_killed if player.role == Role.WITCH else None,
            experience_tips=self.memory.tips_for(player.role),
        )

    def _judge_winner(self) -> None:
        alive = self.alive_players()
        wolves = [p for p in alive if p.role == Role.WEREWOLF]
        goods = [p for p in alive if p.role != Role.WEREWOLF]
        if not wolves:
            self.record.winner = Camp.GOOD
        elif len(wolves) >= len(goods):
            self.record.winner = Camp.EVIL

    def _fallback_winner(self) -> Camp:
        alive = self.alive_players()
        wolves = [p for p in alive if p.role == Role.WEREWOLF]
        goods = [p for p in alive if p.role != Role.WEREWOLF]
        return Camp.EVIL if len(wolves) >= len(goods) else Camp.GOOD

    def alive_players(self) -> list[Player]:
        return [player for player in self.record.players if player.alive]

    def player(self, player_id: int) -> Player:
        for player in self.record.players:
            if player.id == player_id:
                return player
        raise ValueError(f"玩家不存在：{player_id}")

    def save_log(self) -> Path:
        path = self.log_dir / f"{self.record.game_id}.json"
        path.write_text(json.dumps(self.record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
