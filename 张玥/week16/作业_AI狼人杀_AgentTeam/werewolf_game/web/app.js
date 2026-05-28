const roleNames = {
  werewolf: "狼人",
  seer: "预言家",
  witch: "女巫",
  hunter: "猎人",
  villager: "村民",
};

const styleNames = {
  cautious: "谨慎型",
  aggressive: "激进型",
  random: "随机型",
  balanced: "平衡型",
};

const winnerNames = {
  good: "好人阵营",
  evil: "狼人阵营",
};

const reasonNames = {
  night: "夜晚死亡",
  vote: "白天放逐",
};

let currentGameId = null;
let latestRecord = null;

const $ = (id) => document.getElementById(id);

function setStatus(message) {
  $("statusText").textContent = message;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `请求失败：${response.status}`);
  }
  return response.json();
}

function playerName(record, playerId) {
  const player = record.players.find((item) => item.id === playerId || item.player_id === playerId);
  return player ? player.name : `玩家${playerId}`;
}

function renderSummary(record) {
  $("gameIdText").textContent = record.game_id || currentGameId || "-";
  $("winnerText").textContent = record.winner ? winnerNames[record.winner] || record.winner : "未决出";
  $("dayText").textContent = record.day_count ?? 0;
  $("review").textContent = record.review?.summary || "暂无复盘。";
}

function renderPlayers(record) {
  const container = $("players");
  if (!record.players?.length) {
    container.className = "players empty";
    container.textContent = "暂无玩家，请先创建对局。";
    return;
  }

  container.className = "players";
  container.innerHTML = record.players
    .map((player) => {
      const role = roleNames[player.role] || "身份未公开";
      const style = styleNames[player.style] || player.style || "未知风格";
      const alive = player.alive ? "存活" : "出局";
      return `
        <div class="player-card ${player.alive ? "" : "dead"}">
          <div class="player-name">${player.name}</div>
          <span class="role-tag">${role}</span>
          <span class="alive-tag">${alive}</span>
          <div class="player-style">策略风格：${style}</div>
        </div>
      `;
    })
    .join("");
}

function eventHtml(day, title, body, tag = "") {
  return `
    <div class="event">
      <div class="event-time">第 ${day} 天</div>
      <div>
        <div class="event-title">${tag ? `<span class="event-tag">${tag}</span>` : ""}${title}</div>
        <div class="event-body">${body}</div>
      </div>
    </div>
  `;
}

function renderTimeline(record) {
  const events = [];

  for (const night of record.nights || []) {
    const details = [];
    if (night.wolf_target !== null && night.wolf_target !== undefined) {
      details.push(`狼人目标：${playerName(record, night.wolf_target)}`);
    }
    if (night.seer_check) {
      details.push(
        `预言家查验：${playerName(record, night.seer_check.target_id)}，结果：${
          winnerNames[night.seer_check.camp] || night.seer_check.camp
        }`
      );
    }
    if (night.witch_save !== null && night.witch_save !== undefined) {
      details.push(`女巫使用解药：${playerName(record, night.witch_save)}`);
    }
    if (night.witch_poison !== null && night.witch_poison !== undefined) {
      details.push(`女巫使用毒药：${playerName(record, night.witch_poison)}`);
    }
    if (night.deaths?.length) {
      details.push(`夜晚死亡：${night.deaths.map((death) => playerName(record, death.player_id)).join("、")}`);
    }
    events.push(eventHtml(night.day, "夜晚行动", details.join("<br>") || "无人死亡，所有 Agent 继续观察。", "Night"));
  }

  for (const dialogue of record.dialogues || []) {
    events.push(
      eventHtml(
        dialogue.day,
        `${dialogue.player_name} 发言`,
        dialogue.content,
        roleNames[dialogue.role] || "Speech"
      )
    );
  }

  for (const vote of record.votes || []) {
    events.push(
      eventHtml(
        vote.day,
        `${playerName(record, vote.voter_id)} 投票给 ${playerName(record, vote.target_id)}`,
        vote.reason,
        "Vote"
      )
    );
  }

  for (const death of record.deaths || []) {
    const reason = reasonNames[death.reason] || death.reason;
    events.push(eventHtml(death.day, `${playerName(record, death.player_id)} 出局`, `原因：${reason}`, "Death"));
  }

  const container = $("timeline");
  if (!events.length) {
    container.className = "timeline empty";
    container.textContent = "暂无事件。";
    return;
  }
  container.className = "timeline";
  container.innerHTML = events.join("");
}

function renderGame(record) {
  latestRecord = record;
  renderSummary(record);
  renderPlayers(record);
  renderTimeline(record);
}

function normalizeCreatedGame(data) {
  return {
    game_id: data.game_id,
    day_count: 0,
    winner: null,
    players: data.players.map((player) => ({
      id: player.player_id,
      name: player.name,
      role: null,
      style: player.style,
      alive: player.alive,
    })),
    nights: [],
    dialogues: [],
    votes: [],
    deaths: [],
    review: {},
  };
}

async function createGame() {
  try {
    setStatus("正在创建对局...");
    const seedValue = $("seedInput").value;
    const payload = seedValue === "" ? {} : { seed: Number(seedValue) };
    const data = await requestJson("/games", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    currentGameId = data.game_id;
    $("runGameBtn").disabled = false;
    renderGame(normalizeCreatedGame(data));
    setStatus("对局已创建，可以运行完整对局。");
  } catch (error) {
    setStatus(`创建失败：${error.message}`);
  }
}

async function runGame() {
  if (!currentGameId) {
    setStatus("请先创建对局。");
    return;
  }
  try {
    setStatus("AI Agent 正在进行狼人杀对局...");
    const data = await requestJson(`/games/${currentGameId}/run`, { method: "POST" });
    renderGame(data);
    setStatus("对局已完成，时间线已更新。");
  } catch (error) {
    setStatus(`运行失败：${error.message}`);
  }
}

function renderEvolution(data) {
  const rounds = data.records
    .map(
      (record) => `
        <div class="mini-card">
          <strong>第 ${record.round} 局</strong>
          <div>胜利阵营：${winnerNames[record.winner] || record.winner}</div>
          <div>总天数：${record.days}</div>
          <div>对局 ID：${record.game_id}</div>
        </div>
      `
    )
    .join("");

  const memory = Object.entries(data.final_memory || {})
    .map(([role, value]) => {
      const tips = (value.tips || []).map((tip) => `<div>· ${tip}</div>`).join("");
      return `
        <div class="mini-card">
          <strong>${roleNames[role] || role}</strong>
          <div>局数：${value.games}，胜场：${value.wins}，负场：${value.losses}</div>
          ${tips}
        </div>
      `;
    })
    .join("");

  $("evolution").className = "evolution";
  $("evolution").innerHTML = `
    <div class="evolution-rounds">${rounds}</div>
    <div class="memory-grid">${memory}</div>
  `;
}

async function runEvolution() {
  try {
    setStatus("正在运行 3 局自进化实验...");
    const data = await requestJson("/tournaments/self-evolution", {
      method: "POST",
      body: JSON.stringify({ rounds: 3, seed: Number($("seedInput").value || 2026) }),
    });
    renderEvolution(data);
    setStatus("自进化实验完成。");
  } catch (error) {
    setStatus(`自进化失败：${error.message}`);
  }
}

$("createGameBtn").addEventListener("click", createGame);
$("runGameBtn").addEventListener("click", runGame);
$("evolutionBtn").addEventListener("click", runEvolution);

if (latestRecord === null) {
  renderSummary({ players: [], day_count: 0, winner: null, review: {} });
}
