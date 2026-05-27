const state = {
  websocket: null,
  reconnectTimer: null,
};

const $ = (id) => document.getElementById(id);

function fmt(value, digits = 2) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return value.toFixed(digits);
}

function setPill(id, active, label) {
  const el = $(id);
  el.textContent = label;
  el.classList.toggle("good", active);
  el.classList.toggle("warn", !active);
}

async function postJson(path, payload = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status}`);
  }
  return response.json();
}

function bindControls() {
  $("start-stack").addEventListener("click", () => {
    postJson("/api/stack/start").catch(showError);
  });
  $("stop-stack").addEventListener("click", () => {
    postJson("/api/stack/stop").catch(showError);
  });
  $("dvl-setup").addEventListener("click", () => {
    postJson("/api/dvl/setup").catch(showError);
  });
  $("dvl-reset").addEventListener("click", () => {
    postJson("/api/dvl/reset_dr").catch(showError);
  });
  $("start-bag").addEventListener("click", () => {
    postJson("/api/bag/start").catch(showError);
  });
  $("stop-bag").addEventListener("click", () => {
    postJson("/api/bag/stop").catch(showError);
  });
}

function connectStatusSocket() {
  clearTimeout(state.reconnectTimer);
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  state.websocket = new WebSocket(`${protocol}//${window.location.host}/ws/status`);

  state.websocket.addEventListener("open", () => {
    $("connection-state").textContent = "Connected";
  });

  state.websocket.addEventListener("message", (event) => {
    renderStatus(JSON.parse(event.data));
  });

  state.websocket.addEventListener("close", () => {
    $("connection-state").textContent = "Disconnected. Reconnecting...";
    state.reconnectTimer = setTimeout(connectStatusSocket, 1000);
  });

  state.websocket.addEventListener("error", () => {
    $("connection-state").textContent = "Connection error";
  });
}

function renderStatus(payload) {
  const process = payload.process || {};
  const ros = payload.ros || {};
  const topics = ros.topics || {};
  const pose = ros.pose || {};
  const velocity = ros.velocity || {};
  const depth = ros.depth || {};
  const joy = ros.joy || {};

  setPill("stack-pill", process.stack_running, process.stack_running ? "STACK ON" : "STACK OFF");
  setPill("bag-pill", process.bag_running, process.bag_running ? "BAG ON" : "BAG OFF");
  setPill("joy-pill", topics.joy?.alive, topics.joy?.alive ? "JOY ON" : "JOY OFF");

  $("pose-value").textContent = `${fmt(pose.x)}, ${fmt(pose.y)}, ${fmt(pose.z)}`;
  $("yaw-value").textContent = `${fmt((pose.yaw || 0) * 180 / Math.PI, 1)} deg`;
  $("velocity-value").textContent = `${fmt(velocity.x)}, ${fmt(velocity.y)}, ${fmt(velocity.z)}`;
  $("depth-value").textContent = `${fmt(depth.z)} m`;
  $("joy-axes").textContent = JSON.stringify(joy.axes || [], null, 2);
  $("joy-buttons").textContent = JSON.stringify(joy.buttons || [], null, 2);
  renderTopics(topics);
  renderPath(ros.path || []);
  $("log-output").textContent = (process.logs || []).join("\n");
}

function renderTopics(topics) {
  const rows = Object.values(topics).map((topic) => {
    const age = typeof topic.age === "number" ? `${fmt(topic.age, 2)}s` : "--";
    const hz = `${fmt(topic.hz, 1)} Hz`;
    const cls = topic.alive ? "alive" : "stale";
    return `
      <div class="topic ${cls}">
        <strong>${topic.name}</strong>
        <span>${topic.alive ? "alive" : "stale"} · ${hz} · age ${age}</span>
      </div>`;
  });
  $("topic-list").innerHTML = rows.join("");
}

function renderPath(points) {
  const canvas = $("path-canvas");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#2a3731";
  ctx.lineWidth = 1;
  for (let x = 0; x <= width; x += 40) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y <= height; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  if (points.length < 2) return;

  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = Math.max(maxX - minX, 1);
  const spanY = Math.max(maxY - minY, 1);
  const scale = 0.82 * Math.min(width / spanX, height / spanY);
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;

  ctx.strokeStyle = "#6ec6ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = width / 2 + (point.x - cx) * scale;
    const y = height / 2 - (point.y - cy) * scale;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  const last = points[points.length - 1];
  const lx = width / 2 + (last.x - cx) * scale;
  const ly = height / 2 - (last.y - cy) * scale;
  ctx.fillStyle = "#52d273";
  ctx.beginPath();
  ctx.arc(lx, ly, 5, 0, Math.PI * 2);
  ctx.fill();
}

function showError(error) {
  const line = `${new Date().toLocaleTimeString()} ${error.message}`;
  $("log-output").textContent = `${$("log-output").textContent}\n${line}`.trim();
}

bindControls();
connectStatusSocket();
