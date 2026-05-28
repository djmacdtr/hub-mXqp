"""AI 狼人杀作业的轻量 FastAPI 接口。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import GameEngine
from .tournament import run_self_evolution


app = FastAPI(title="AI 狼人杀 Agent Team", version="0.1.0")
WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

GAMES: dict[str, GameEngine] = {}


class CreateGameRequest(BaseModel):
    seed: int | None = Field(default=None, description="随机种子，便于复现实验")


class SelfEvolutionRequest(BaseModel):
    rounds: int = Field(default=3, ge=1, le=20, description="连续运行的对局数量")
    seed: int = Field(default=2026, description="随机种子")


def _get_engine(game_id: str) -> GameEngine:
    engine = GAMES.get(game_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    return engine


@app.get("/")
def index() -> FileResponse:
    """返回轻量观战页面。"""
    return FileResponse(WEB_DIR / "index.html")


@app.post("/games")
def create_game(request: CreateGameRequest) -> dict:
    """创建一局新的狼人杀对局。"""
    engine = GameEngine(seed=request.seed)
    GAMES[engine.record.game_id] = engine
    return {
        "game_id": engine.record.game_id,
        "status": "created",
        "player_count": len(engine.record.players),
        "players": [
            {
                "player_id": player.id,
                "name": player.name,
                "style": player.style.value,
                "alive": player.alive,
            }
            for player in engine.record.players
        ],
    }


@app.post("/games/{game_id}/run")
def run_game(game_id: str) -> dict:
    """运行完整对局并返回结构化日志。"""
    engine = _get_engine(game_id)
    if engine.record.winner is not None:
        return engine.record.to_dict()
    return engine.run().to_dict()


@app.get("/games/{game_id}")
def get_game(game_id: str) -> dict:
    """查看指定对局当前状态。"""
    return _get_engine(game_id).record.to_dict()


@app.post("/tournaments/self-evolution")
def run_self_evolution_api(request: SelfEvolutionRequest) -> dict:
    """连续运行多局，观察经验沉淀如何影响后续 Agent。"""
    return run_self_evolution(rounds=request.rounds, seed=request.seed)
