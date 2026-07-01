/* IDAPS dashboard client.
 *
 * Opens a WebSocket to the server, runs a match in one of four modes, and
 * renders the stream of events: a network map on the canvas, animated attack
 * lines, a live scoreboard, and an event feed. When a human controls a side,
 * an action panel appears and the server waits for the move before resolving.
 *
 * All simulation logic lives on the server - this file only draws what it
 * receives and sends back the human player's chosen moves.
 */

"use strict";

// ---- element handles -------------------------------------------------------
const el = {
  redScore: document.getElementById("redScore"),
  blueScore: document.getElementById("blueScore"),
  status: document.getElementById("statusBadge"),
  modeGrid: document.getElementById("modeGrid"),
  seed: document.getElementById("seedInput"),
  ticks: document.getElementById("ticksInput"),
  speed: document.getElementById("speedInput"),
  start: document.getElementById("startBtn"),
  stop: document.getElementById("stopBtn"),
  canvas: document.getElementById("map"),
  banner: document.getElementById("tickBanner"),
  feed: document.getElementById("feed"),
  // action panel
  actionBar: document.getElementById("actionBar"),
  actionHead: document.getElementById("actionHead"),
  actionKindWord: document.getElementById("actionKindWord"),
  optionChips: document.getElementById("optionChips"),
  targetChips: document.getElementById("targetChips"),
  actionSummary: document.getElementById("actionSummary"),
  confirmMove: document.getElementById("confirmMove"),
  // result overlay
  overlay: document.getElementById("resultOverlay"),
  resultTitle: document.getElementById("resultTitle"),
  resultDetail: document.getElementById("resultDetail"),
  closeResult: document.getElementById("closeResult"),
};

const ctx = el.canvas.getContext("2d");

// ---- state -----------------------------------------------------------------
let ws = null;
let nodes = {};          // hostname -> {x, y, host}
let flashes = [];        // active attack animations
let running = false;
let mode = "ai_vs_ai";
let info = { vectors: [], defenses: [] };  // from /api/info

// the move the human is currently composing
let pending = { team: null, option: null, target: null };

// ---- colors ----------------------------------------------------------------
const COLORS = {
  success: "#ff4d5e",
  prevented: "#43a6ff",
  detected: "#ffce4f",
  failed: "#8a97b8",
  green: "#3ddc84",
  node: "#161e30",
  nodeBorder: "#2a3550",
  ink: "#e6ecff",
  muted: "#8a97b8",
  red: "#ff4d5e",
};

function outcomeKind(attack) {
  if (!attack) return "failed";
  if (attack.prevented) return "prevented";
  if (attack.success) return "success";
  if (attack.detected) return "detected";
  return "failed";
}

// ---- scoreboard + status + feed -------------------------------------------
function setScore(red, blue) {
  el.redScore.textContent = red;
  el.blueScore.textContent = blue;
}

function setStatus(text) {
  el.status.textContent = text;
}

function addFeed(event) {
  const li = document.createElement("li");
  const a = event.attack;
  let kind = "failed";
  let lines = [];
  if (a) {
    kind = outcomeKind(a);
    const tag = a.prevented ? "PREVENTED"
      : (a.success && a.detected) ? "SUCCESS (detected)"
      : a.success ? "SUCCESS (stealth)"
      : a.detected ? "FAILED (detected)" : "FAILED";
    lines.push(`T${event.tick}  ${a.vector} → ${a.target}  [${tag}]`);
  } else {
    lines.push(`T${event.tick}  (no attack this tick)`);
  }
  if (event.defense_deployed) {
    lines.push(`Blue deployed ${event.defense_deployed} @ ${event.defense_host}`);
  }
  li.className = "feed-item " + kind;
  li.innerHTML = lines.map((t, i) =>
    i === 0 ? `<span class="feed-main">${t}</span>`
            : `<span class="feed-sub">${t}</span>`).join("");
  el.feed.insertBefore(li, el.feed.firstChild);
  while (el.feed.children.length > 80) el.feed.removeChild(el.feed.lastChild);
}

function clearFeed() {
  el.feed.innerHTML = "";
}

// ---- canvas sizing + layout ------------------------------------------------
function resizeCanvas() {
  const rect = el.canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  el.canvas.width = rect.width * dpr;
  el.canvas.height = rect.height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  layoutNodes();
}
window.addEventListener("resize", resizeCanvas);

// Place host nodes across the upper area; the attacker sits bottom-center.
function layoutNodes() {
  const names = Object.keys(nodes);
  if (!names.length) return;
  const rect = el.canvas.getBoundingClientRect();
  const cx = rect.width / 2;
  const cy = rect.height * 0.42;
  const radius = Math.min(rect.width, rect.height) * 0.30;
  names.forEach((name, i) => {
    const angle = (i / names.length) * Math.PI * 2 - Math.PI / 2;
    nodes[name].x = cx + radius * Math.cos(angle);
    nodes[name].y = cy + radius * Math.sin(angle);
  });
}

function attackerOrigin() {
  const rect = el.canvas.getBoundingClientRect();
  return { x: rect.width / 2, y: rect.height - 46 };
}

// ---- drawing ---------------------------------------------------------------
function hexAlpha(hex, alpha) {
  const a = Math.round(Math.max(0, Math.min(1, alpha)) * 255)
    .toString(16).padStart(2, "0");
  return hex + a;
}

function draw() {
  const rect = el.canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);

  const origin = attackerOrigin();

  // faint links from attacker to every host (the "network")
  ctx.strokeStyle = hexAlpha(COLORS.nodeBorder, 0.5);
  ctx.lineWidth = 1;
  for (const name of Object.keys(nodes)) {
    const n = nodes[name];
    ctx.beginPath();
    ctx.moveTo(origin.x, origin.y);
    ctx.lineTo(n.x, n.y);
    ctx.stroke();
  }

  // active attack flashes
  flashes = flashes.filter((f) => f.life > 0);
  for (const f of flashes) {
    const target = nodes[f.target];
    if (!target) continue;
    const alpha = Math.min(1, f.life / 40);
    ctx.strokeStyle = hexAlpha(COLORS[f.kind], alpha);
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(origin.x, origin.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();
    // moving pulse dot
    const t = 1 - f.life / 40;
    const px = origin.x + (target.x - origin.x) * t;
    const py = origin.y + (target.y - origin.y) * t;
    ctx.fillStyle = COLORS[f.kind];
    ctx.beginPath();
    ctx.arc(px, py, 5, 0, Math.PI * 2);
    ctx.fill();
    f.life -= 1;
  }

  for (const name of Object.keys(nodes)) drawNode(nodes[name], name);
  drawAttacker(origin);

  requestAnimationFrame(draw);
}

function drawNode(node, name) {
  const h = node.host;
  ctx.save();

  let ring = COLORS.nodeBorder;
  if (!h.online) ring = COLORS.muted;
  else if (h.compromised) ring = COLORS.success;
  else if (h.defenses.length) ring = COLORS.green;

  // highlight if it's a selectable / selected target
  const selectable = pending.team && node.selectable;
  if (selectable) {
    ctx.shadowColor = pending.team === "red" ? COLORS.red : COLORS.prevented;
    ctx.shadowBlur = pending.target === name ? 26 : 12;
  }

  ctx.fillStyle = COLORS.node;
  ctx.strokeStyle = pending.target === name
    ? (pending.team === "red" ? COLORS.red : COLORS.prevented) : ring;
  ctx.lineWidth = pending.target === name ? 4 : 3;
  ctx.beginPath();
  ctx.arc(node.x, node.y, 32, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.shadowBlur = 0;

  ctx.fillStyle = COLORS.ink;
  ctx.font = "bold 13px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(h.hostname, node.x, node.y - 42);

  // state text inside the node
  ctx.font = "10px sans-serif";
  if (!h.online) {
    ctx.fillStyle = COLORS.muted;
    ctx.fillText("OFFLINE", node.x, node.y + 3);
  } else if (h.compromised) {
    ctx.fillStyle = COLORS.success;
    ctx.fillText("PWNED", node.x, node.y + 3);
  } else {
    ctx.fillStyle = COLORS.green;
    ctx.fillText("SECURE", node.x, node.y + 3);
  }

  if (h.defenses.length) {
    ctx.fillStyle = COLORS.green;
    ctx.font = "10px sans-serif";
    ctx.fillText("⛨ " + h.defenses.length, node.x, node.y + 50);
  }
  ctx.restore();
}

function drawAttacker(origin) {
  ctx.save();
  ctx.fillStyle = "#2a1420";
  ctx.strokeStyle = COLORS.success;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(origin.x, origin.y, 28, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = COLORS.success;
  ctx.font = "bold 12px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("RED", origin.x, origin.y + 4);
  ctx.restore();
}

// ---- click-to-target on the canvas ----------------------------------------
el.canvas.addEventListener("click", (e) => {
  if (!pending.team) return;
  const rect = el.canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  for (const name of Object.keys(nodes)) {
    const n = nodes[name];
    if (!n.selectable) continue;
    if ((x - n.x) ** 2 + (y - n.y) ** 2 <= 34 * 34) {
      selectTarget(name);
      return;
    }
  }
});

// ---- network state ---------------------------------------------------------
function buildNodes(networkDict) {
  nodes = {};
  for (const h of networkDict.hosts) {
    nodes[h.hostname] = { x: 0, y: 0, host: h, selectable: false };
  }
  layoutNodes();
}

function updateNodes(networkDict) {
  for (const h of networkDict.hosts) {
    if (nodes[h.hostname]) nodes[h.hostname].host = h;
  }
}

// ---- /api/info -------------------------------------------------------------
async function loadInfo() {
  try {
    const res = await fetch("/api/info");
    info = await res.json();
  } catch (e) {
    info = { vectors: [], defenses: [] };
  }
}

// ---- action panel (human moves) -------------------------------------------
function showActionPanel(team) {
  pending = { team, option: null, target: null };
  el.actionBar.classList.remove("hidden");
  el.actionBar.classList.toggle("red-turn", team === "red");
  el.actionBar.classList.toggle("blue-turn", team === "blue");
  el.actionHead.textContent = team === "red"
    ? "RED's move — pick an attack and a target"
    : "BLUE's move — pick a defense and where to deploy it";
  el.actionKindWord.textContent = team === "red" ? "attack" : "defense";

  // build option chips
  el.optionChips.innerHTML = "";
  const options = team === "red" ? info.vectors : info.defenses;
  for (const o of options) {
    const chip = document.createElement("button");
    chip.className = "chip option";
    const meta = team === "red"
      ? `<span class="chip-meta sev-${o.severity}">${o.severity} · +${o.points}</span>`
      : `<span class="chip-meta">${Math.round(o.prevent_chance * 100)}% block</span>`;
    chip.innerHTML = `<span class="chip-name">${o.name}</span>${meta}`;
    chip.title = o.description || "";
    chip.addEventListener("click", () => selectOption(o.name, chip));
    el.optionChips.appendChild(chip);
  }

  // mark every online host selectable as a target
  el.targetChips.innerHTML = "";
  for (const name of Object.keys(nodes)) {
    const h = nodes[name].host;
    nodes[name].selectable = h.online;
    const chip = document.createElement("button");
    chip.className = "chip target";
    chip.dataset.host = name;
    chip.disabled = !h.online;
    chip.innerHTML = `<span class="chip-name">${name}</span>` +
      `<span class="chip-meta">${h.online ? (h.compromised ? "pwned" : "secure") : "offline"}</span>`;
    chip.addEventListener("click", () => selectTarget(name));
    el.targetChips.appendChild(chip);
  }

  updateSummary();
}

function hideActionPanel() {
  el.actionBar.classList.add("hidden");
  for (const name of Object.keys(nodes)) nodes[name].selectable = false;
  pending = { team: null, option: null, target: null };
}

function selectOption(name, chipEl) {
  pending.option = name;
  el.optionChips.querySelectorAll(".chip").forEach((c) => c.classList.remove("sel"));
  if (chipEl) chipEl.classList.add("sel");
  updateSummary();
}

function selectTarget(name) {
  pending.target = name;
  el.targetChips.querySelectorAll(".chip").forEach((c) =>
    c.classList.toggle("sel", c.dataset.host === name));
  updateSummary();
}

function updateSummary() {
  const verb = pending.team === "red" ? "Attack" : "Defend";
  if (pending.option && pending.target) {
    el.actionSummary.textContent =
      `${verb}: ${pending.option} → ${pending.target}`;
    el.confirmMove.disabled = false;
  } else {
    el.actionSummary.textContent = "Select an action and a target…";
    el.confirmMove.disabled = true;
  }
}

el.confirmMove.addEventListener("click", () => {
  if (!pending.option || !pending.target || !ws) return;
  const payload = { action: "move", target: pending.target };
  if (pending.team === "red") payload.vector = pending.option;
  else payload.defense = pending.option;
  ws.send(JSON.stringify(payload));
  hideActionPanel();
  el.banner.textContent = "Move sent — resolving…";
});

// ---- mode selection --------------------------------------------------------
el.modeGrid.addEventListener("click", (e) => {
  const btn = e.target.closest(".mode-btn");
  if (!btn || running) return;
  mode = btn.dataset.mode;
  el.modeGrid.querySelectorAll(".mode-btn").forEach((b) =>
    b.classList.toggle("active", b === btn));
});

// ---- WebSocket match flow --------------------------------------------------
function startMatch() {
  if (running) return;
  clearFeed();
  el.overlay.classList.add("hidden");
  setScore(0, 0);

  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    const seedRaw = el.seed.value.trim();
    ws.send(JSON.stringify({
      action: "start",
      mode,
      ticks: parseInt(el.ticks.value, 10) || 20,
      seed: seedRaw === "" ? null : parseInt(seedRaw, 10),
      delay: parseFloat(el.speed.value),
    }));
    running = true;
    el.start.disabled = true;
    el.stop.disabled = false;
    setStatus(modeLabel(mode));
  };

  ws.onmessage = (msg) => {
    const data = JSON.parse(msg.data);
    if (data.type === "init") {
      buildNodes(data.network);
      el.banner.textContent = "Match started";
    } else if (data.type === "await_move") {
      showActionPanel(data.team);
      el.banner.textContent = `Tick ${data.tick}: ${data.team.toUpperCase()}'s turn`;
    } else if (data.type === "tick") {
      handleTick(data);
    } else if (data.type === "end") {
      handleEnd(data);
    }
  };

  ws.onclose = () => endRunningState();
  ws.onerror = () => {
    el.banner.textContent = "Connection error — is the server running?";
    endRunningState();
  };
}

function modeLabel(m) {
  return {
    ai_vs_ai: "AI vs AI",
    player_red: "You = Red",
    player_blue: "You = Blue",
    pvp: "Player vs Player",
  }[m] || m;
}

function handleTick(data) {
  const event = data.event;
  updateNodes(data.network);
  setScore(event.red_total, event.blue_total);
  addFeed(event);
  if (event.attack) {
    flashes.push({ target: event.attack.target, kind: outcomeKind(event.attack), life: 44 });
    el.banner.textContent = `Tick ${event.tick}: ${event.attack.headline}`;
  } else {
    el.banner.textContent = `Tick ${event.tick}`;
  }
}

function handleEnd(data) {
  hideActionPanel();
  endRunningState();
  setStatus("finished");
  el.resultTitle.textContent = `${data.winner} wins`;
  el.resultTitle.className = data.winner === "Red" ? "win-red"
    : data.winner === "Blue" ? "win-blue" : "win-tie";
  el.resultDetail.textContent =
    `Final score — Red ${data.red} vs Blue ${data.blue}. ` +
    `Hosts compromised: ${data.compromised}/${data.total_hosts}.`;
  el.overlay.classList.remove("hidden");
  el.banner.textContent = `Match over — ${data.winner} wins`;
}

function stopMatch() {
  if (ws) {
    try { ws.send(JSON.stringify({ action: "stop" })); } catch (e) {}
    ws.close();
  }
  hideActionPanel();
  endRunningState();
  setStatus("stopped");
  el.banner.textContent = "Match stopped";
}

function endRunningState() {
  running = false;
  el.start.disabled = false;
  el.stop.disabled = true;
}

// ---- wire up + boot --------------------------------------------------------
el.start.addEventListener("click", startMatch);
el.stop.addEventListener("click", stopMatch);
el.closeResult.addEventListener("click", () => el.overlay.classList.add("hidden"));

loadInfo();
resizeCanvas();
requestAnimationFrame(draw);
