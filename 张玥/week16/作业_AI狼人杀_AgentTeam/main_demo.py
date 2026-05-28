"""运行一局纯 AI 狼人杀对战。"""

from __future__ import annotations

from werewolf_game.engine import DEFAULT_LOG_DIR, GameEngine
from werewolf_game.schemas import ROLE_CN, STYLE_CN


def main() -> None:
    engine = GameEngine(seed=2026)
    record = engine.run()

    print("=== AI 狼人杀单局演示 ===")
    print(f"对局 ID：{record.game_id}")
    print(f"胜利阵营：{record.winner.value if record.winner else '未决出'}")
    print(f"总天数：{record.day_count}")
    print()

    print("玩家与角色：")
    for player in record.players:
        status = "存活" if player.alive else "出局"
        print(
            f"- {player.name}：{ROLE_CN[player.role]} / {STYLE_CN[player.style]} / {status}"
        )

    print()
    print("死亡顺序：")
    if not record.deaths:
        print("- 本局没有玩家出局")
    for death in record.deaths:
        player = next(item for item in record.players if item.id == death.player_id)
        print(f"- 第 {death.day} 天：{player.name}，原因：{death.reason}")

    print()
    print("复盘摘要：")
    print(record.review.get("summary", "本局暂无复盘摘要"))
    print()
    print(f"结构化日志已保存到：{DEFAULT_LOG_DIR / (record.game_id + '.json')}")


if __name__ == "__main__":
    main()
