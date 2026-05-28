# 第16周作业说明

本目录用于提交第十六周作业：**AI 狼人杀 — 多智能体协作与博弈的 Agent Team 实战**。

本次实现聚焦四件事：

- 多角色 Agent：狼人、预言家、女巫、猎人、村民。
- 完整对局引擎：夜晚行动、白天发言、投票放逐、胜负裁决。
- 信息隔离：每个 Agent 只能看到自己角色允许看到的信息。
- 自进化 Agent：对局结束后复盘，把经验写入 memory，下一局读取经验调整策略。

作业目录：

```text
作业_AI狼人杀_AgentTeam/
  需求说明.md
  架构设计.md
  测试逻辑.md
  自进化Agent设计.md
  main_demo.py
  run_self_evolution_demo.py
  werewolf_game/
    web/
  tests/
```

## 运行单局对战

```powershell
cd D:\AI_study_env\files\study\Week16\homework\作业_AI狼人杀_AgentTeam
D:\AI_study_env\miniconda3\envs\py312\python.exe main_demo.py
```

## 运行自进化多局实验

```powershell
D:\AI_study_env\miniconda3\envs\py312\python.exe run_self_evolution_demo.py
```

## 启动 FastAPI

```powershell
D:\AI_study_env\miniconda3\envs\py312\python.exe -m uvicorn werewolf_game.api:app --reload
```

启动后可在浏览器打开观战页面：

```text
http://127.0.0.1:8000/
```

页面支持创建对局、运行完整 AI 对战、查看玩家身份、发言、投票、死亡、复盘摘要，以及运行 3 局自进化实验。

## 运行测试

```powershell
D:\AI_study_env\miniconda3\envs\py312\python.exe -m unittest discover -s tests
```

> 说明：本作业默认使用本地规则 Agent，预留 LLM 接入点，但不强依赖 API Key。
