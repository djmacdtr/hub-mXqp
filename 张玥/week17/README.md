# 第17周作业说明

本目录用于提交第十七周作业：**基于 RedisVL 思路实现 LLM Smart Cache**。

作业实现放在：

```text
作业_LLM智能缓存_RedisVL参考/
```

本次作业参考课程目录：

```text
Week17/09-llm-smart-cache
```

以及 RedisVL 项目思路：

```text
https://github.com/redis/redis-vl-python
```

## 作业目标

- 使用 Docker Redis 作为缓存与消息存储。
- 使用 FAISS 做本地向量相似度检索。
- 实现 Embedding 缓存、语义缓存、语义对话历史、语义路由 4 个组件。
- 提供 demo 和 unittest，保证作业可运行、可验证。

## 启动 Redis

如果还没有 Redis 容器：

```powershell
docker run --name week17-redis-cache -p 6379:6379 -d redis:latest
```

如果容器已存在但未运行：

```powershell
docker start week17-redis-cache
```

## 运行作业

```powershell
cd D:\AI_study_env\files\study\Week17\homework\作业_LLM智能缓存_RedisVL参考
D:\AI_study_env\miniconda3\envs\py312\python.exe demo_smart_cache.py
```

## 运行测试

```powershell
D:\AI_study_env\miniconda3\envs\py312\python.exe -m unittest discover -s tests
```

> 说明：本作业是教学版实现，重点是理解 RedisVL 的能力模式，不是完整复刻 RedisVL 源码。
