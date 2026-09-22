/* Web UI 前端逻辑：原生 JS 单页 */
let SETTINGS = null;

// ---------- 基础 ----------

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (res.status === 401) { showLogin(); throw new Error("未登录"); }
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

function $(id) { return document.getElementById(id); }
function esc(s) { const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML; }

function showLogin() {
  $("login-view").classList.remove("hidden");
  $("login-view").classList.add("login-view-full");
  $("app-view").classList.add("hidden");
}

function showApp() {
  $("login-view").classList.add("hidden");
  $("app-view").classList.remove("hidden");
  loadAll();
}

async function doLogin() {
  try {
    await api("/api/login", { method: "POST", body: JSON.stringify({ password: $("login-password").value }) });
    $("login-err").textContent = "";
    showApp();
  } catch (e) { $("login-err").textContent = e.message; }
}

// ---------- Tab 切换 ----------

document.querySelectorAll("nav a[data-tab]").forEach(a => {
  a.addEventListener("click", () => {
    document.querySelectorAll("nav a").forEach(x => x.classList.remove("active"));
    document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
    a.classList.add("active");
    $("tab-" + a.dataset.tab).classList.add("active");
    if (a.dataset.tab === "dashboard") { loadDashboard(); loadLogs(); }
    if (a.dataset.tab === "streamers") loadStreamers();
    if (a.dataset.tab === "files") loadFiles();
    if (a.dataset.tab === "notify") loadNotify();
    if (a.dataset.tab === "cookies") loadCookies();
    if (a.dataset.tab === "settings") loadSettings();
  });
});

function loadAll() {
  loadDashboard(); loadLogs(); loadStreamers(); loadFiles(); loadNotify(); loadCookies(); loadSettings();
}

// ---------- 仪表盘 ----------

async function loadDashboard() {
  try {
    const st = await api("/api/status");
    const cards = st.streamers.map(s => {
      const stateBadge = s.recording
        ? `<span class="badge rec">● 录制中</span>`
        : s.postprocessing ? `<span class="badge warn">封装中</span>`
        : s.record_error ? `<span class="badge warn" title="${esc(s.record_error)}">录制异常</span>`
        : s.live ? `<span class="badge live">🔴 直播中</span>`
        : `<span class="badge off">未开播</span>`;
      const dur = s.record_started_at ? `<div>录制开始：${esc(s.record_started_at)}</div>` : "";
      const stopBtn = (s.recording || s.postprocessing || s.record_state === "等待重连")
        ? `<button class="small danger" onclick="recordStop('${esc(s.name)}')">⏹ 停止录制</button>`
        : (s.record_enabled ? "" : `<button class="small" onclick="recordStart('${esc(s.name)}')">▶ 开始录制</button>`);
      return `<div class="card">
        <div class="head"><span class="name">${esc(s.name)}</span>${stateBadge}</div>
        <div class="meta">
          <div>平台：${s.platform === "bilibili" ? "哔哩哔哩" : "抖音"} ｜ 画质：${esc(s.quality || "-")} ｜ 通知组：${esc(s.group || "-")}</div>
          ${s.title ? `<div>直播标题：${esc(s.title)}</div>` : ""}
          ${s.record_state ? `<div>任务状态：${esc(s.record_state)}</div>` : ""}
          ${dur}
        </div>
        <div class="actions">
          <button class="small secondary" onclick="toggleRecordEnabled('${esc(s.name)}', ${!s.record_enabled})">${s.record_enabled ? "关闭自动录制" : "开启自动录制"}</button>
          ${stopBtn}
        </div>
      </div>`;
    }).join("");
    $("dashboard-cards").innerHTML = cards || `<p class="muted">还没有主播，请到「主播管理」添加。</p>`;
    $("sys-info").textContent = `监控速度 ${st.speed_level} 档` + (st.sleeping ? " ｜ 😴 休眠时段中" : "") + ` ｜ 启动于 ${st.started_at}`;
  } catch (e) { console.error(e); }
}

async function loadLogs() {
  try {
    const r = await api("/api/logs?lines=200");
    $("log-view").textContent = r.lines.join("\n") || "暂无日志";
    const v = $("log-view");
    v.scrollTop = v.scrollHeight;
  } catch (e) {}
}

async function recordStart(name) {
  try { await api(`/api/streamers/${encodeURIComponent(name)}/record_start`, { method: "POST" }); loadDashboard(); }
  catch (e) { alert(e.message); }
}
async function recordStop(name) {
  try { await api(`/api/streamers/${encodeURIComponent(name)}/record_stop`, { method: "POST" }); loadDashboard(); }
  catch (e) { alert(e.message); }
}
async function toggleRecordEnabled(name, enabled) {
  try { await api(`/api/streamers/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify({ platform: "douyin", record_enabled: enabled }) }); loadDashboard(); loadStreamers(); }
  catch (e) { alert(e.message); }
}

setInterval(() => {
  if ($("app-view").classList.contains("hidden")) return;
  if ($("auto-refresh").checked && $("tab-dashboard").classList.contains("active")) loadDashboard();
  if ($("auto-log").checked && $("tab-dashboard").classList.contains("active")) loadLogs();
}, 5000);

// ---------- 录播文件管理 ----------

let FILES_DATA = null;
let filesPlat = "bilibili";

async function loadFiles() {
  try {
    FILES_DATA = await api("/api/files");
    renderFiles();
  } catch (e) {
    $("files-tree").innerHTML = `<p class="muted">加载失败：${esc(e.message)}</p>`;
  }
}

function switchFilesPlat(p) {
  filesPlat = p;
  document.querySelectorAll("#tab-files .seg-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.plat === p));
  renderFiles();
}

function fmtSize(n) {
  if (n == null) return "-";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0, v = n;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  if (i === 0) return v + " B";
  return (v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2)) + " " + units[i];
}

function renderFiles() {
  if (!FILES_DATA) return;
  const plat = FILES_DATA.platforms.find(p => p.key === filesPlat) ||
               { label: filesPlat, count: 0, size: 0, streamers: [] };
  $("files-summary").textContent =
    plat.count ? `共 ${plat.count} 个文件 · ${fmtSize(plat.size)}` : "暂无文件";
  if (!plat.streamers.length) {
    $("files-tree").innerHTML =
      `<p class="muted">暂无录播文件（目录 ${esc(FILES_DATA.root)}/${esc(plat.label || "")}）</p>`;
    return;
  }
  $("files-tree").innerHTML = plat.streamers.map(s => `
    <details class="tree-node" ${plat.streamers.length === 1 ? "open" : ""}>
      <summary>
        <span class="t-name">📁 ${esc(s.name)}</span>
        <span class="t-meta">${s.count} 个文件 · ${fmtSize(s.size)}</span>
      </summary>
      ${s.days.map(d => `
        <details class="tree-node sub" ${s.days.length === 1 ? "open" : ""}>
          <summary>
            <span class="t-name">📅 ${esc(d.date)}</span>
            <span class="t-meta">${d.count} 个 · ${fmtSize(d.size)}</span>
          </summary>
          <table class="file-table">
            <thead><tr><th>文件名</th><th class="num">大小</th><th>下载</th></tr></thead>
            <tbody>
              ${d.files.map(f => `
                <tr>
                  <td class="fname">${esc(f.name)}</td>
                  <td class="num">${fmtSize(f.size)}</td>
                  <td><a class="btn-a" href="/api/files/download?path=${encodeURIComponent(f.path)}" download>⬇ 下载</a></td>
                </tr>`).join("")}
            </tbody>
          </table>
        </details>`).join("")}
    </details>`).join("");
}

// ---------- 主播管理 ----------

const QUALITIES = ["原画", "蓝光", "超清", "高清", "标清"];
let STREAMERS_CACHE = []; // 最近一次加载的主播数据，用于「没有改动」判断

async function loadStreamers() {
  try {
    const r = await api("/api/streamers");
    STREAMERS_CACHE = r.streamers.map(s => ({ ...s }));
    const groups = (SETTINGS?.notification?.notification_groups) || [];
    const groupOpts = g => groups.map(x => `<option ${x.name === g ? "selected" : ""}>${esc(x.name)}</option>`).join("");
    $("streamer-table").tBodies[0].innerHTML = r.streamers.map((s, i) => `
      <tr data-name="${esc(s.name)}">
        <td><b>${esc(s.name)}</b></td>
        <td>${s.platform === "bilibili" ? "哔哩哔哩" : "抖音"}</td>
        <td><input type="text" class="e-url" value="${esc(s.url)}"></td>
        <td><select class="e-quality">${QUALITIES.map(q => `<option ${q === s.quality ? "selected" : ""}>${q}</option>`).join("")}</select></td>
        <td><input type="checkbox" class="e-monitor" ${s.monitor_enabled ? "checked" : ""}></td>
        <td><input type="checkbox" class="e-record" ${s.record_enabled ? "checked" : ""}></td>
        <td><select class="e-group"><option value="">（默认组）</option>${groupOpts(s.group)}</select></td>
        <td>
          <button class="small" onclick="saveStreamerRow(${i})">保存</button>
          <button class="small danger" onclick="deleteStreamer('${esc(s.name)}')">删除</button>
        </td>
      </tr>`).join("") || `<tr><td colspan="8" class="muted">暂无主播</td></tr>`;
  } catch (e) {}
}

async function addStreamer() {
  try {
    await api("/api/streamers", {
      method: "POST",
      body: JSON.stringify({
        platform: $("add-platform").value,
        name: $("add-name").value.trim(),
        url: $("add-url").value.trim(),
        quality: "原画",
      }),
    });
    $("add-name").value = ""; $("add-url").value = "";
    loadStreamers(); loadDashboard();
  } catch (e) { alert(e.message); }
}

async function saveStreamerRow(i) {
  const tr = $("streamer-table").tBodies[0].rows[i];
  const name = tr.dataset.name;
  const orig = STREAMERS_CACHE[i] || {};
  const next = {
    platform: orig.platform || "douyin",
    url: tr.querySelector(".e-url").value.trim(),
    quality: tr.querySelector(".e-quality").value,
    monitor_enabled: tr.querySelector(".e-monitor").checked,
    record_enabled: tr.querySelector(".e-record").checked,
    group: tr.querySelector(".e-group").value,
  };
  const unchanged =
    next.url === (orig.url || "") &&
    next.quality === (orig.quality || "") &&
    next.monitor_enabled === !!orig.monitor_enabled &&
    next.record_enabled === !!orig.record_enabled &&
    next.group === (orig.group || "");
  if (unchanged) { alert("没有改动"); return; }
  try {
    await api(`/api/streamers/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(next) });
    alert("保存成功");
    loadStreamers(); loadDashboard();
  } catch (e) {
    alert("保存失败：" + e.message);
  }
}

async function deleteStreamer(name) {
  if (!confirm(`确定删除主播【${name}】？正在进行的录制会同时停止。`)) return;
  try { await api(`/api/streamers/${encodeURIComponent(name)}`, { method: "DELETE" }); loadStreamers(); loadDashboard(); }
  catch (e) { alert(e.message); }
}

// ---------- 通知 ----------

async function loadNotify() {
  await loadSettingsRaw();
  const n = SETTINGS.notification;
  $("n-wx-enabled").checked = !!n.wxpusher_enabled;
  $("n-wx-token").value = n.wxpusher_app_token || "";
  $("n-wx-uids").value = (n.wxpusher_uids || []).join("\n");
  $("n-wecom-enabled").checked = !!n.wecom_enabled;
  $("n-wecom-webhook").value = n.wecom_webhook || "";
  $("n-default-group").value = n.default_notification_group || "";
  renderGroups(n.notification_groups || []);
  renderPeriods("dnd-list", n.do_not_disturb_periods || [], false);
}

function renderGroups(groups) {
  $("group-list").innerHTML = groups.map((g, i) => `
    <div class="item-row">
      <input type="text" class="g-name" value="${esc(g.name)}" placeholder="组名" style="width:140px">
      <label class="muted"><input type="checkbox" class="g-wx" ${g.notify_methods?.wxpusher ? "checked" : ""}> WxPusher</label>
      <label class="muted"><input type="checkbox" class="g-wecom" ${g.notify_methods?.wecom ? "checked" : ""}> 企业微信</label>
      <button class="small danger" onclick="delGroup(${i})">删除</button>
    </div>`).join("") || `<p class="muted">暂无通知组（所有主播按 WxPusher 开启推送）</p>`;
}
function addGroup() { collectNotify(); SETTINGS.notification.notification_groups.push({ name: "", notify_methods: { wxpusher: true, wecom: false } }); renderGroups(SETTINGS.notification.notification_groups); }
function delGroup(i) { collectNotify(); SETTINGS.notification.notification_groups.splice(i, 1); renderGroups(SETTINGS.notification.notification_groups); }

function renderPeriods(container, list, withLevel) {
  $(container).innerHTML = list.map((p, i) => `
    <div class="item-row">
      <input type="text" class="p-start" value="${esc(p.start || "")}" placeholder="23:00" style="width:80px"> -
      <input type="text" class="p-end" value="${esc(p.end || "")}" placeholder="07:00" style="width:80px">
      ${withLevel ? `<label class="muted">速度档 <input type="number" class="p-level" min="1" max="5" value="${p.level || 1}" style="width:60px"></label>` : ""}
      <button class="small danger" onclick="delPeriod('${container}',${i})">删除</button>
    </div>`).join("") || `<p class="muted">暂无</p>`;
}
function collectPeriods(container, withLevel) {
  return [...$(container).querySelectorAll(".item-row")].map(row => ({
    start: row.querySelector(".p-start").value.trim(),
    end: row.querySelector(".p-end").value.trim(),
    ...(withLevel ? { level: parseInt(row.querySelector(".p-level").value) || 1 } : {}),
  })).filter(p => p.start && p.end);
}
function delPeriod(container, i) {
  const map = { "dnd-list": () => SETTINGS.notification.do_not_disturb_periods,
                "speed-list": () => SETTINGS.global_settings.scheduled_speed_periods,
                "sleep-list": () => SETTINGS.global_settings.sleep_periods };
  map[container]().splice(i, 1);
  renderPeriods(container, map[container](), container === "speed-list");
}

function collectNotify() {
  SETTINGS.notification.wxpusher_enabled = $("n-wx-enabled").checked;
  SETTINGS.notification.wxpusher_app_token = $("n-wx-token").value.trim();
  SETTINGS.notification.wxpusher_uids = $("n-wx-uids").value.split("\n").map(x => x.trim()).filter(Boolean);
  SETTINGS.notification.wecom_enabled = $("n-wecom-enabled").checked;
  SETTINGS.notification.wecom_webhook = $("n-wecom-webhook").value.trim();
  SETTINGS.notification.default_notification_group = $("n-default-group").value.trim();
  SETTINGS.notification.notification_groups = [...$("group-list").querySelectorAll(".item-row")].map(row => ({
    name: row.querySelector(".g-name").value.trim(),
    notify_methods: { wxpusher: row.querySelector(".g-wx").checked, wecom: row.querySelector(".g-wecom").checked },
  })).filter(g => g.name);
  SETTINGS.notification.do_not_disturb_periods = collectPeriods("dnd-list", false);
}

async function saveNotify() {
  try {
    collectNotify();
    await api("/api/settings", { method: "POST", body: JSON.stringify({ notification: SETTINGS.notification }) });
    alert("已保存");
  } catch (e) { alert(e.message); }
}

async function testNotify() {
  try { await api("/api/test_notify", { method: "POST" }); alert("已发送，请注意查收"); }
  catch (e) { alert(e.message); }
}

// ---------- Cookie ----------

async function loadCookies() {
  await loadSettingsRaw();
  $("c-douyin-monitor").value = SETTINGS.cookies.douyin_monitor || "";
  $("c-douyin-record").value = SETTINGS.cookies.douyin_record || "";
  $("c-bilibili").value = SETTINGS.cookies.bilibili || "";
}
async function saveCookies() {
  try {
    await api("/api/settings", { method: "POST", body: JSON.stringify({ cookies: {
      douyin_monitor: $("c-douyin-monitor").value.trim(),
      douyin_record: $("c-douyin-record").value.trim(),
      bilibili: $("c-bilibili").value.trim(),
    } }) });
    alert("已保存");
  } catch (e) { alert(e.message); }
}

// ---------- B站扫码登录 ----------

let qrTimer = null;

async function qrStart() {
  try {
    if (qrTimer) { clearInterval(qrTimer); qrTimer = null; }
    const r = await api("/api/qrlogin/start", { method: "POST", body: "{}" });
    window._qrSid = r.sid; // 供调试/观察
    $("qr-box").classList.remove("hidden");
    $("qr-img").src = r.qr;
    $("qr-status").textContent = "等待扫码…（请用B站手机 App 扫描）";
    qrTimer = setInterval(() => qrPoll(r.sid), 2500);
  } catch (e) { alert(e.message); }
}

async function qrPoll(sid) {
  let r;
  try { r = await api(`/api/qrlogin/status?sid=${encodeURIComponent(sid)}`); }
  catch (e) { clearInterval(qrTimer); qrTimer = null; $("qr-status").textContent = e.message; return; }
  const el = $("qr-status");
  if (r.status === "waiting") { el.textContent = "⏳ 等待扫码…"; }
  else if (r.status === "scanned") { el.textContent = "📱 已扫码，请在手机上点确认"; }
  else {
    clearInterval(qrTimer); qrTimer = null;
    if (r.status === "success" && r.saved) {
      el.textContent = `✅ ${r.message}`;
      loadCookies(); // 刷新输入框里显示的 Cookie
    } else { el.textContent = `❌ ${r.message}`; }
  }
}

// ---------- 设置 ----------

async function loadSettingsRaw() {
  SETTINGS = await api("/api/settings");
}

async function loadSettings() {
  try {
    await loadSettingsRaw();
    const gs = SETTINGS.global_settings;
    $("s-check-interval").value = gs.check_interval;
    $("s-speed").value = gs.monitor_speed_level;
    $("s-save-folder").value = gs.save_folder;
    $("s-split").value = gs.split_size || 0;
    $("s-keep-flv").checked = !!gs.keep_flv;
    $("s-tolerance").value = gs.size_tolerance_mb ?? 25;
    $("s-host").value = gs.webui_host || "0.0.0.0";
    $("s-port").value = gs.webui_port || 6657;
    renderPeriods("speed-list", gs.scheduled_speed_periods || [], true);
    renderPeriods("sleep-list", gs.sleep_periods || [], false);
    renderAutomations(SETTINGS.automations || []);
  } catch (e) {}
}

function renderAutomations(list) {
  const names = SETTINGS.streamers.map(s => s.name);
  $("auto-list").innerHTML = list.map((a, i) => `
    <div class="item-row">
      <select class="a-streamer">${names.map(n => `<option ${n === a.streamer ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>
      <select class="a-trigger">
        <option ${a.trigger === "直播中" ? "selected" : ""}>直播中</option>
        <option ${a.trigger === "未开播" ? "selected" : ""}>未开播</option>
      </select>
      <input type="text" class="a-script grow" value="${esc(a.script || "")}" placeholder="脚本路径（.py / .sh）">
      <button class="small danger" onclick="delAutomation(${i})">删除</button>
    </div>`).join("") || `<p class="muted">暂无自动化任务</p>`;
}
function addAutomation() {
  SETTINGS.automations.push({ streamer: SETTINGS.streamers[0]?.name || "", trigger: "直播中", script: "" });
  renderAutomations(SETTINGS.automations);
}
function delAutomation(i) { SETTINGS.automations.splice(i, 1); renderAutomations(SETTINGS.automations); }

async function saveSettings() {
  try {
    const gs = {
      check_interval: parseInt($("s-check-interval").value) || 60,
      monitor_speed_level: parseInt($("s-speed").value) || 1,
      save_folder: $("s-save-folder").value.trim() || "Recordings",
      split_size: parseFloat($("s-split").value) || 0,
      keep_flv: $("s-keep-flv").checked,
      size_tolerance_mb: parseInt($("s-tolerance").value) || 0,
      webui_host: $("s-host").value.trim() || "0.0.0.0",
      webui_port: parseInt($("s-port").value) || 6657,
      scheduled_speed_periods: collectPeriods("speed-list", true),
      sleep_periods: collectPeriods("sleep-list", false),
    };
    SETTINGS.automations = [...$("auto-list").querySelectorAll(".item-row")].map(row => ({
      streamer: row.querySelector(".a-streamer").value,
      trigger: row.querySelector(".a-trigger").value,
      script: row.querySelector(".a-script").value.trim(),
    })).filter(a => a.script);
    await api("/api/settings", { method: "POST", body: JSON.stringify({ global_settings: gs, automations: SETTINGS.automations }) });
    alert("已保存（监听地址/端口需重启生效）");
  } catch (e) { alert(e.message); }
}

async function changePassword() {
  try {
    await api("/api/password", { method: "POST", body: JSON.stringify({
      old_password: $("s-old-pass").value, new_password: $("s-new-pass").value }) });
    $("s-old-pass").value = ""; $("s-new-pass").value = "";
    alert("口令已更新，下次登录生效");
  } catch (e) { alert(e.message); }
}

// ---------- 启动 ----------

(async function init() {
  try {
    const r = await api("/api/auth_required");
    if (r.required) {
      showLogin();
    } else {
      showApp();
    }
  } catch (e) { showLogin(); }
})();
