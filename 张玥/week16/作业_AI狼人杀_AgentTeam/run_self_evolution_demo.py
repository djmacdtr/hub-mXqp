"""运行多局对战，展示自进化经验沉淀。"""

from __future__ import annotations

from werewolf_game.tournament import run_self_evolution


def main() -> None:
    result = run_self_evolution(rounds=3, seed=2026)

    print("=== AI 狼人杀自进化演示 ===")
    print(f"运行局数：{result['rounds']}")
    print(f"经验文件：{result['memory_path']}")
    print(f"实验日志：{result['output_path']}")
    print()

    for record in result["records"]:
        print(
            f"- 第 {record['round']} 局：胜利阵营={record['winner']}，"
            f"天数={record['days']}，对局 ID={record['game_id']}"
        )

    print()
    print("最终沉淀的角色经验：")
    for role, data in result["final_memory"].items():
        print(f"- {role}：")
        for tip in data.get("tips", []):
            print(f"  * {tip}")


if __name__ == "__main__":
    main()
