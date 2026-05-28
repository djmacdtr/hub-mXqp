"""多局自进化实验。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .engine import DEFAULT_LOG_DIR, GameEngine
from .memory import DEFAULT_MEMORY_PATH, ExperienceMemory


def run_self_evolution(
    rounds: int = 3,
    seed: int = 2026,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    log_dir: Path | str = DEFAULT_LOG_DIR,
) -> dict:
    memory = ExperienceMemory(Path(memory_path))
    log_dir = Path(log_dir)
    records = []
    for index in range(rounds):
        engine = GameEngine(seed=seed + index, memory=memory, log_dir=log_dir)
        record = engine.run()
        records.append(
            {
                "round": index + 1,
                "game_id": record.game_id,
                "winner": record.winner.value if record.winner else None,
                "days": record.day_count,
                "review": record.review,
            }
        )

    result = {
        "rounds": rounds,
        "records": records,
        "memory_path": str(memory.path),
        "final_memory": memory.data,
    }
    log_dir.mkdir(parents=True, exist_ok=True)
    output_path = log_dir / f"evolution_{int(time.time())}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["output_path"] = str(output_path)
    return result
