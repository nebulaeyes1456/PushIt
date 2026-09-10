/* PushIt 前端（E 线 MVP mock）。原生 JS，无依赖；三端响应式，数据存 localStorage。
   演示链路 = 粘贴消息 → 处理报告（估代价/该接判定/话术/双质检）→ 记入台账 → 负载/净账联动。
   后端规则引擎见 backend/services/*（M2 将接真接口替换本 mock）。*/
"use strict";

/* ---------- 常量与 mock 库 ---------- */
var BASE_COMMIT = 32;             // 本周已排工时（示例承诺，含基线）
var CAP = 40;                     // 周容量
var LS_KEY = "pushit_reqs_v1";
var API_BASE = (function () {
  if (!(new URLSearchParams(location.search).has("api"))) return "";
  try { return localStorage.getItem("pushit_api_base") || "http://127.0.0.1:8765/api/v1"; } catch (e) { return ""; }
})();
var PERSON_IDS = { "王组长": "pmid", "赵总": "pboss", "小李": "ppeer" };
function isDemo() { return new URLSearchParams(location.search).has("demo"); }
function getKey() { return isDemo() ? "pushit_demo_reqs" : "pushit_reqs_v1"; }
function getKeyPeople() { return isDemo() ? "pushit_demo_people" : "pushit_people_v1"; }
var PEOPLE = loadPeople();
function loadPeople() {
  try { var raw = localStorage.getItem(getKeyPeople()); if (raw) return JSON.parse(raw); } catch (e) {}
  return isDemo() ? [
    { name: "王组长", role: "中层" }, { name: "赵总", role: "大老板" }, { name: "小李", role: "平级" }
  ] : [];  // 正式模式：提出人由用户自建（与关系画像同源）
}
function savePeople() { try { localStorage.setItem(getKeyPeople(), JSON.stringify(PEOPLE)); } catch (e) {} }
function roleMotivation(role) { return { "大老板": "boss_press", "中层": "self_achievement", "平级": "relay" }[role] || "other"; }
function roleLabel(role) { return { "大老板": "大老板拍板/中层转压", "中层": "中层要业绩 / 拍脑袋", "平级": "帮同事/别组转达" }[role] || "其他"; }
function findPerson(name) {
  for (var i = 0; i < PEOPLE.length; i++) if (PEOPLE[i].name === name) return PEOPLE[i];
  return null;
}
function renderPersonSelects() {
  var html = "";
  if (PEOPLE.length === 0) html = '<option value="">（先点“＋提出人”添加）</option>';
  else PEOPLE.forEach(function (p) { html += '<option value="' + ESC(p.name) + '">' + ESC(p.name) + "（" + ESC(p.role) + "）</option>"; });
  $("in-person").innerHTML = html;
  var rp = $("rehearse-person");
  if (rp) {
    rp.innerHTML = "";
    PEOPLE.forEach(function (p) {
      var o = document.createElement("option"); o.textContent = p.name; rp.appendChild(o);
    });
  }
}
var PERSONS = {
  "王组长": { role: "中层", motivation: "self_achievement", style: "high", label: "中层要业绩/拍脑袋" },
  "赵总":   { role: "大老板", motivation: "boss_press", style: "high", label: "大老板拍板/中层转压" },
  "小李":   { role: "平级", motivation: "relay", style: "low", label: "帮同事/别组转达" }
};
var SCALE_WORDS = { "导出":1, "报表":1, "看板":1, "页面":1.2, "接口":1.2, "权限":1.5, "迁移":2, "预演":1.3, "排查":1.3, "数据字典":0.6, "梳理":0.8, "复查":1, "统计":1 };
var ACCEPT_WORDS = /预演|核心|老板亲抓|成长|演示会|关键路径/;
var AMBIG_WORDS = ["再说", "看看吧", "尽量", "应该可以", "回头", "我考虑下", "先这样"];
var FORBIDDEN = ["你行不行", "需求很蠢", "做不到", "凭什么", "我不管", "不是我的活", "关我什么事"];
var TACTICS = {
  two_options:     { name: "给两个能接受的选项", ex: "两种走法：A 快而糙，周五先给你一版能看的；B 全而稳，下周三给，同时把低优先级那条挪出本周。您选哪个？", conclusion: "请从 A/B 两案中选一；未选前不启动。" },
  proceduralize:   { name: "升级成流程（记入排期会）", ex: "这个我记下了，先不进本周承诺；下周二排期会一起过优先级再定，会上我会把和现有 3 件事的冲突摆出来。", conclusion: "本周不承诺，进下周二排期会再定。" },
  mirror_up:       { name: "用他的逻辑反制（向上溯源）", ex: "我的判断是这周硬上会砸了演示会那场——真到那一步，您向上面最不好交代的就是这一条。所以我的建议是保演示会、这条延期，您看要不要先跟上面打个招呼？", conclusion: "建议保演示会、该需求延期；请您向上对齐口径。" },
  agree_then_cost: { name: "先热情同意、再列代价", ex: "没问题可以做——只是这周硬上，演示会那场大概率要黄。为了不让您到时候难交代，我建议保住演示会，这个挪到下周二，可以吗？", conclusion: "可做但不在本周；以您拍板时间为准。" },
  accept_pretty:   { name: "漂亮地接（该接就接）", ex: "这个对我有挑战，我接——但我需要把 X 挪后两周，才能把它做扎实。您看是挪 X，还是给这条加个人？", conclusion: "我接，但需调整资源/排期；请定 A 或 B。" },
  ball_return:     { name: "把球送回去（应对皮球 §6.10）", ex: "这个我可以评估——但我需要你先给我范围和原始数据，没有前置我没法判断它和现有承诺的冲突。你先把这两样补上，我再给你一个带前提的评估？", conclusion: "不接不拒；请您先补范围和原始数据，我对齐后再评估。" }
};
var ESC = function (s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]; }); };

/* ---------- 状态 ---------- */
var reqs = loadReqs();

function loadReqs() {
  try { var raw = localStorage.getItem(getKey()); if (raw) return JSON.parse(raw); } catch (e) {}
  if (!isDemo()) return [];  // 正式模式：空账本起步，走 Day 0 引导
  return [
    { id: "A", text: "顺手把报表导出权限也开了，这周一起上", person: "王组长", source: "口头", status: "pending", low: 3, high: 6.6, scale: 1.5, at: "今天 14:20", motivation: "self_achievement" },
    { id: "B", text: "核心迁移预演排进本周，演示会给上面看", person: "赵总", source: "会议", status: "accepted", low: 4, high: 8.8, scale: 2, at: "昨天", motivation: "boss_press" },
    { id: "C", text: "帮市场部临时拉个经营看板，很快", person: "小李", source: "消息", status: "pending", low: 2, high: 4, scale: 1, at: "今天 09:10", motivation: "relay" }
  ];
}
function saveReqs() { try { localStorage.setItem(getKey(), JSON.stringify(reqs)); } catch (e) {} }
function $(id) { return document.getElementById(id); }

/* ---------- mock 引擎：文本 → 处理报告（镜像 backend/services 规则） ---------- */
function addPersonFlow() {
  $("add-person-form").classList.remove("hidden");
  $("ap-name").focus();
}
function confirmAddPerson() {
  var name = $("ap-name").value.trim();
  if (!name) return;
  var role = $("ap-role").value;
  var p = { name: name, role: role };
  PEOPLE.push(p); savePeople();
  if (API_BASE) {
    fetch(API_BASE + "/persons", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: name, role: role }) })
      .then(function (r) { return r.json(); })
      .then(function (d) { p.id = d.person_id; savePeople(); })
      .catch(function () {});
  }
  $("add-person-form").classList.add("hidden");
  $("ap-name").value = "";
  renderPersonSelects();
  $("in-person").value = name;
  renderRel();
}

function mockProcess(text, personName, source) {
  var p = findPerson(personName) || PERSONS[personName] || { role: "其他", motivation: "other", label: "其他" };
  if (!p.motivation) p = { role: p.role, motivation: roleMotivation(p.role), label: roleLabel(p.role) };
  var auto = $("in-auto").checked;
  var accept = auto && ACCEPT_WORDS.test(text);
  // 复杂度/估算（只给保守区间，§8）
  var scale = 1;
  for (var k in SCALE_WORDS) if (text.indexOf(k) >= 0) scale = Math.max(scale, SCALE_WORDS[k]);
  var clauses = text.split(/[，。、；和及,]/).length;
  scale *= 0.8 + 0.2 * Math.min(clauses, 4);
  scale = Math.round(scale * 100) / 100;
  var low = Math.round(2 * scale * 10) / 10;
  var high = Math.round((scale >= 1.2 ? low * 2.2 : low * 1.8) * 10) / 10;
  var committed = BASE_COMMIT, remaining = CAP - committed;
  var afterHigh = committed + high - CAP;
  // 策略/话术
  var tacticId;
  var kickBall = p.motivation === "relay" && /很快|顺便|临时|简单|小事|顺手/.test(text);
  if (accept) tacticId = "accept_pretty";
  else if (kickBall) tacticId = "ball_return";
  else if (p.motivation === "relay") tacticId = "proceduralize";
  else if (p.motivation === "boss_press") tacticId = "mirror_up";
  else tacticId = "two_options";
  var t = TACTICS[tacticId];
  // 双质检
  var fb = FORBIDDEN.filter(function (w) { return text.indexOf(w) >= 0; });
  var am = AMBIG_WORDS.filter(function (w) { return text.indexOf(w) >= 0; });
  var redline = { passed: fb.length === 0 && am.length === 0, forbidden: fb, ambiguous: am };
  return {
    text: text, accept: accept, person: personName, role: p.role, source: source,
    kickBall: kickBall,
    motivation: p.motivation, motivationLabel: p.label,
    low: low, high: high, scale: scale,
    overload: afterHigh > 0,
    tacticId: tacticId, tacticName: t.name, script: t.ex, conclusion: t.conclusion,
    redline: redline, recall: "3 秒复述自检：对方能否复述出「" + t.conclusion.replace("结论：", "") + "」？能 → 明确性通过。",
    guardrail: accept ? ["should_accept"] : (tacticId === "proceduralize" ? ["attribution", "written_receipt"] : ["attribution", "clarity_conclusion_first"])
  };
}

/* ---------- 渲染：报告卡 ---------- */
function countThisWeek(person) {
  return reqs.filter(function (x) { return x.person === person; }).length + 1;
}

function renderReport(r) {
  var card = $("report-card");
  card.classList.remove("hidden");
  var risk = r.scale >= 1.2 ? "老模块耦合、返工风险偏高" : "范围边界需先确认";
  var html =
    '<div class="badge ' + (r.accept ? "accept" : "decline") + '">' + (r.accept ? "该接 · 漂亮地接" : "该拒/需对齐 · 先明确后台阶") + "</div>" +
    '<div class="item-text">' + ESC(r.text) + "</div>" +
    (r.kickBall ? '<div class="rep warnline">⚠ 疑似皮球（无前置、无信息）——已切换“把球送回去”打法（§6.10）</div>' : "") +
    '<div class="meta">提出人 ' + ESC(r.person) + "（" + ESC(r.role) + "） · 来源 " + ESC(r.source) + " · 动机：" + ESC(r.motivationLabel) + "</div>" +
    '<div class="mini" style="color:#8a7f6b">📒 基于你的账本生成：本周已排 32h · 这是 ' + ESC(r.person) + ' 本周第 ' + countThisWeek(r.person) + ' 次加活</div>' +
    '<div class="rep"><b>代价（保守区间）</b>：' + r.low + " ~ " + r.high + " 小时 · 复杂度系数 " + r.scale + "</div>" +
    '<div class="rep"><b>风险</b>：' + risk + (r.overload ? '　<span class="warnline">⚠ 已超本周容量，硬上会挤掉既有承诺</span>' : "") + "</div>" +
    '<h3>建议打法：' + ESC(r.tacticName) + "</h3>" +
    '<div class="script">' + ESC(r.script) + "<small>↑ 可直接照念 / 复制（默认安全版）</small></div>" +
    '<div class="rep">【明确结论】' + ESC(r.conclusion) + "</div>" +
    '<div class="rep okline">' + ESC(r.recall) + "</div>" +
    (r.redline.passed
      ? '<div class="rep okline">红线检测通过 · 无埋雷句 · 不会被误读为答应</div>'
      : '<div class="rep"><b>红线提示：</b>你的原话里有雷句（' + ESC(r.redline.forbidden.concat(r.redline.ambiguous).join("、")) + '），别照原话发，用上面话术卡。</div>') +
    '<div class="actions">' +
    (r.accept
      ? '<button class="primary" data-do="accept">记入 · 接受（漂亮地接）</button>'
      : '<button class="primary" data-do="decline">挡掉（赢回约 ' + r.low + 'h）</button>' +
        '<button data-do="park">记入 · 需对齐</button>' +
        '<button class="ghost" data-do="grudge">接吧 · 记妥协账</button>') +
    '<button class="ghost" data-do="copy">复制话术</button><button class="ghost" data-do="share">生成分享卡片</button></div>';
  card.innerHTML = html;
  card.querySelectorAll("[data-do]").forEach(function (b) { b.onclick = function () { onAction(b.getAttribute("data-do"), r); }; });
}

/* ---------- 动作 ---------- */
function nextId() { return "R" + Math.random().toString(36).slice(2, 7); }
function addReq(r) {
  var it = { id: nextId(), text: r.text || "", person: r.person, source: r.source, status: "pending", low: r.low, high: r.high, scale: r.scale, at: new Date().toLocaleString().slice(5, 16), motivation: r.motivation, log: [{ at: new Date().toLocaleString().slice(5, 16), act: "记入台账" }] };
  reqs.unshift(it); saveReqs(); renderAll();
  try {
    if (!localStorage.getItem("pushit_aha")) {
      localStorage.setItem("pushit_aha", "1");
      var h = $("hint-line");
      if (h) h.textContent = "这就是差异：免费内容给你一句话，PushIt 给你一本账——上面这条已留痕，可随时导出为证据。";
    }
  } catch (e) {}
  return it;
}
function onAction(doWhat, r) {
  var item;
  if (doWhat === "accept") {
    item = addReq(r); item.status = "accepted";
    if (!r.accept) { item.grudge = true; showGrudgeCard(item); return; }  // 该拒却接了 → 妥协账
  } else if (doWhat === "grudge") {
    item = addReq(r); item.status = "accepted"; item.grudge = true;
    saveReqs(); renderAll(); showGrudgeCard(item); return;
  }
  else if (doWhat === "decline" || doWhat === "park") { item = addReq(r); item.status = doWhat === "decline" ? "declined" : "aligned"; }
  else if (doWhat === "copy") { copyText(r.script); return; }
  else if (doWhat === "share") { shareCard(r); return; }
  saveReqs(); renderAll();
  if (doWhat === "decline") showDebtAction(item);
}
function showDebtAction(item) {
  var bar = $("debt-bar");
  bar.classList.remove("hidden");
  bar.innerHTML = '<b>这活挡掉后会有人做吗？</b> 若会被转派，建议先留「避坑交接」——<button id="btn-hand" class="ghost">转派给同事并生成避坑说明</button><span class="mini">（演示「拒绝债」§6.9）</span>';
  $("btn-hand").onclick = function () {
    item.handed = "同事";
    item.log.push({ at: new Date().toLocaleString().slice(5, 16), act: "转派并留避坑交接" });
    saveReqs();
    copyText("给接手的人：" + item.text + "。风险：" + (item.scale >= 1.2 ? "老模块权限口径未对齐前别改库；" : "") + "先对齐范围与前提再排期。需要的话我帮你先搭前置部分。");
    renderAll();
  };
}

/* ---------- 渲染：各 Tab ---------- */
function statusBadge(s) { return { pending: "待处理", aligned: "已对齐", accepted: "已接受", declined: "已挡掉" }[s] || s; }
function badgeClass(s) { return { pending: "pending", aligned: "pending", accepted: "accept", declined: "decline" }[s] || "done"; }

function showGrudgeCard(item) {
  var n = reqs.filter(function (x) { return x.grudge; }).length;
  var sum = 0;
  reqs.forEach(function (x) { if (x.grudge) sum += x.low; });
  sum = Math.round(sum * 10) / 10;
  var line;
  if (n <= 1) {
    line = "记下了。这件活本可以挡，但既然接了，账本里它就是「妥协账」。这次多背约 " + item.low + " 小时——下次对齐时，这几个小时就是你谈条件的依据。";
  } else {
    line = "这是你第 " + n + " 次被迫承接（累计约 " + sum + " 小时）。不劝你了——数据替你记着；1:1 之前点「生成本周摘要」，把负担亮给对方看。";
  }
  var card = $("report-card"); card.classList.remove("hidden");
  card.innerHTML = '<div class="badge pending">已记入妥协账</div>' +
    '<div class="script" style="background:#f7f3e8">' + ESC(line) + "</div>" +
    '<div class="actions"><button id="btn-grudge-load">去负载页看累计</button></div>';
  $("btn-grudge-load").onclick = function () { switchView("load"); };
}

function renderLedger() {
  var nNew = reqs.filter(function (x) { return x.status === "pending" || x.status === "aligned"; }).length;
  var nDecl = reqs.filter(function (x) { return x.status === "declined"; }).length;
  var nAcc = reqs.filter(function (x) { return x.status === "accepted"; }).length;
  var now = new Date();
  $("ledger-range").textContent = "（" + reqs.length + " 条）";
  $("ledger-summary").textContent = "待处理 " + nNew + " · 已挡 " + nDecl + " · 已接 " + nAcc + "";
  var ul = $("ledger-list"); ul.innerHTML = "";
  var total = reqs.length;
  reqs.forEach(function (it, idx) {
    var no = total - idx;
    var li = document.createElement("li");
    var act = "";
    if (it.status === "pending" || it.status === "aligned") {
      act = '<div class="actions"><button data-k="accept">接受</button><button data-k="decline">挡掉</button><button data-k="park">需对齐</button></div>';
    } else if (it.status === "declined") {
      act = '<div class="mini okline">已挡掉 · 赢回约 ' + it.low + 'h' + (it.handed ? ' · 已留避坑交接' : '') + "</div>";
    }
    var flow = (it.log || []).slice(-2).map(function (l) { return l.at + " " + l.act; }).join(" · ");
    li.innerHTML = '<div class="item-top"><span class="badge ' + badgeClass(it.status) + '">#' + no + " · " + statusBadge(it.status) + "</span><span class='item-meta'>✓ 已留痕 · " + ESC(it.at) + "</span></div>" +
      '<div class="item-text">' + ESC(it.text) + "</div>" +
      '<div class="mini">' + ESC(it.person) + " · " + ESC(it.source) + (it.grudge ? " · 妥协账" : "") + " · 估 " + it.low + " ~ " + it.high + "h</div>" + act +
      (flow ? '<div class="mini" style="color:#8a7f6b">流水：' + ESC(flow) + "</div>" : "");
    li.querySelectorAll("[data-k]").forEach(function (b) { b.onclick = function () { changeStatus(it.id, b.getAttribute("data-k")); }; });
    ul.appendChild(li);
  });
  $("ledger-empty").classList.toggle("hidden", reqs.length > 0);
}
function changeStatus(id, k) {
  var it = reqs.filter(function (x) { return x.id === id; })[0]; if (!it) return;
  it.status = k === "decline" ? "declined" : (k === "accept" ? "accepted" : "aligned");
  it.log = it.log || [];
  it.log.push({ at: new Date().toLocaleString().slice(5, 16), act: k === "decline" ? "挡掉" : (k === "accept" ? "接受" : "需对齐") });
  if (k === "decline") showDebtAction(it);
  saveReqs(); renderAll();
}

function renderLoad() {
  var newLow = 0, newHigh = 0;
  reqs.forEach(function (it) { if (it.status === "pending" || it.status === "accepted" || it.status === "aligned") { newLow += it.low; newHigh += it.high; } });
  newLow = Math.round(newLow * 10) / 10; newHigh = Math.round(newHigh * 10) / 10;
  var total = BASE_COMMIT + newHigh;
  $("load-committed").textContent = BASE_COMMIT + "h";
  $("load-new").textContent = newLow + " ~ " + newHigh + "h";
  $("load-over").textContent = total > CAP ? "是（超 " + Math.round((total - CAP) * 10) / 10 + "h）" : "否";
  $("load-over").style.color = total > CAP ? "var(--bad)" : "var(--ok)";
  $("gauge-fill").style.width = Math.min(100, Math.round(total / CAP * 100)) + "%";
  var bl = $("baseline-list"); bl.innerHTML = "";
  [{ item: "核心迁移", base: 60 }, { item: "双写校验", base: 30 }, { item: "看板一期只读", base: 40 }].forEach(function (b) {
    var li = document.createElement("li");
    li.innerHTML = '<div class="item-top"><span>' + ESC(b.item) + "</span><span class='item-meta'>Q3 · " + b.base + "h</span></div>";
    bl.appendChild(li);
  });
}

var SPEECH_LABEL = { formal: "爱听尊敬/正式措辞（您/请示/汇报）", plain: "觉得客套做作 · 要平实直接", unknown: "语言偏好暂未知" };
function renderRel() {
  if (API_BASE) {
    fetch(API_BASE + "/persons").then(function (r) { return r.json(); }).then(function (ps) {
      renderPersonRows(ps.map(function (p) {
        var c = p.behavior_counts || {};
        return { n: p.name, role: p.role, speech: SPEECH_LABEL[p.speech_style] || SPEECH_LABEL.unknown,
          kick: c.kick_ball || 0, deflect: c.deflect || 0, reliable: c.reliable || 0 };
      }));
    }).catch(function () { renderPersonRows(localPersonRows()); });
  } else { renderPersonRows(localPersonRows()); }
}
function localPersonRows() {
  if (PEOPLE.length === 0) return [];
  return PEOPLE.map(function (p) {
    return { n: p.name, role: p.role, speech: SPEECH_LABEL.unknown, kick: 0 };
  });
}
function renderPersonRows(rows) {
  var list = $("person-list"); list.innerHTML = "";
  if (!rows || rows.length === 0) {
    list.innerHTML = '<p class="empty">还没有提出人画像——点输入区“＋提出人”建立第一个人物，交锋记录会慢慢积累成画像。</p>';
    return;
  }
  rows.forEach(function (x) {
    var li = document.createElement("li");
    var warn = x.kick >= 2 ? '<div class="mini" style="color:#c53030">⚠ 多次踢皮球：备好「把球送回去」话术（§6.10）</div>' : "";
    li.innerHTML = '<div class="item-top"><b>' + ESC(x.n) + "</b></div>" +
      '<div class="mini">角色：' + ESC(x.role) + (x.note ? " · " + ESC(x.note) : "") + "</div>" +
      '<div class="mini">语言偏好：' + ESC(x.speech) + "</div>" + warn +
      '<button class="mini ghost" data-plan="' + ESC(x.n) + '">生成预案本（当场挡）</button><div class="plan hidden"></div>';
    li.querySelector("[data-plan]").onclick = function () { showPlan(x.n, li); };
    list.appendChild(li);
  });
}

function renderMe() {
  var won = 0, debtN = 0, flowN = 0, grudgeN = 0, grudgeSum = 0;
  reqs.forEach(function (it) {
    if (it.status === "declined") won += it.low;
    if (it.handed) debtN += 1;
    flowN += (it.log || []).length;
    if (it.grudge) { grudgeN += 1; grudgeSum += it.low; }
  });
  grudgeSum = Math.round(grudgeSum * 10) / 10;
  $("mem-reqs").textContent = reqs.length + " 条";
  $("mem-flow").textContent = flowN + " 次";
  $("mem-won").textContent = "+" + (Math.round(won * 10) / 10) + "h";
  $("mem-grudge").textContent = grudgeN ? grudgeN + " 件 / " + grudgeSum + "h" : "0";
  $("me-grudge").textContent = grudgeN ? "+" + grudgeSum + "h（" + grudgeN + " 件）" : "0h";
  var debt = debtN * 6, net = Math.round((won - debt) * 10) / 10;
  won = Math.round(won * 10) / 10;
  $("me-won").textContent = "+" + won + "h";
  $("me-debt").textContent = "-" + debt + "h（" + debtN + " 次转派）";
  $("me-net").textContent = (net >= 0 ? "+" : "") + net + "h";
  $("me-net").style.color = net >= 0 ? "var(--ok)" : "var(--bad)";
  drawCurve(won, debt);
}
function drawCurve(won, debt) {
  var c = $("curve"), ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);
  var max = Math.max(won, debt, 1), step = c.width / 4;
  [["#2f7d5c", won], ["#c53030", debt]].forEach(function (pair) {
    ctx.strokeStyle = pair[0]; ctx.lineWidth = 2; ctx.beginPath();
    for (var i = 0; i <= 4; i++) {
      var h = c.height - 8 - (pair[1] * i / 4 / max) * (c.height - 16);
      var x = i * step;
      i === 0 ? ctx.moveTo(x, h) : ctx.lineTo(x, h);
    }
    ctx.stroke();
  });
  ctx.fillStyle = "#8a7f6b"; ctx.font = "10px sans-serif";
  ctx.fillText("绿=累计赢回  红=转嫁欠账（净账看上方）", 4, c.height - 2);
}

/* ---------- Tab / 事件 ---------- */
function switchView(name) {
  ["ledger", "load", "rel", "rehearse", "treehole", "me"].forEach(function (v) {
    $("view-" + v).classList.toggle("on", v === name);
  });
  document.querySelectorAll("#tabs button").forEach(function (b) {
    b.classList.toggle("on", b.getAttribute("data-view") === name);
  });
  if (name === "load") renderLoad();
  if (name === "rel") renderRel();
  if (name === "me") renderMe();
  if (name === "ledger") renderDebtBar();
  if (name === "treehole") renderTreehole();
}
function renderAll() { renderLedger(); renderDebtBar(); renderLoad(); renderRel(); renderMe(); renderDayBar(); }
function renderDebtBar() {
  var n = reqs.filter(function (x) { return x.handed; }).length;
  var bar = $("debt-bar");
  if (n >= 2) { bar.classList.remove("hidden"); bar.innerHTML = '<b>拒绝债提示（§6.9）</b>：已有 ' + n + ' 次转派给同事，当心积累怨气——下次拒绝前先试「谈判换形态」或随拒绝上抛代价账。'; }
  else if (bar.getAttribute("data-tmp")) { bar.classList.add("hidden"); }
}
function copyText(txt) {
  function done() { var h = $("hint-line"); h.textContent = "已复制：给接手同事的避坑说明（或话术）——留痕即安全。"; }
  if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(txt).then(done, done); }
  else { var ta = document.createElement("textarea"); ta.value = txt; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); done(); }
}

/* ---------- 真后端模式（?api=1）：后端不可用回落本地 mock ---------- */
function apiProcess(text, personName, source) {
  var pid = PERSON_IDS[personName];
  var pp = findPerson(personName);
  if (pp && pp.id) pid = pp.id;
  fetch(API_BASE + "/requirements", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text, person_id: pid || "pmid", source: source }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      return fetch(API_BASE + "/requirements/" + d.requirement_id + "/process?use_llm=" + llmOn(),
        { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    })
    .then(function (r) { return r.json(); })
    .then(function (rep) { renderReport(normalizeReport(rep)); $("hint-line").textContent = ""; })
    .catch(function () {
      $("hint-line").textContent = "后端未启动（8765），已回落本地 mock。";
      var r = mockProcess(text, personName, source); renderReport(r);
    });
}
function normalizeReport(rep) {
  return { text: rep.requirement, accept: rep.should_accept === 1,
    person: rep.person.name, role: rep.person.role, source: "后端",
    motivationLabel: rep.motivation.label, kickBall: !!rep.kick_ball,
    low: rep.estimate.total_low, high: rep.estimate.total_high, scale: rep.estimate.scale,
    overload: rep.estimate.capacity.overload,
    tacticName: rep.strategy.tactic_name, script: rep.strategy.text,
    conclusion: (rep.strategy.conclusion || "").replace(/^结论：/, ""), recall: rep.strategy.recall_test,
    redline: rep.strategy.redline_report, guardrail: rep.strategy.guardrail_tags,
    motivation: rep.motivation.id, mode: rep.strategy.mode };
}

/* ---------- 激活/预演/预案/数据（框架层，后续精进） ---------- */
function llmOn() {
  var el = $("opt-llm");
  return !el || el.checked;
}

function renderDayBar() {
  var n = reqs.filter(function (r) { return r.status === "pending" || r.status === "aligned"; }).length;
  var bar = $("day-bar");
  if (n > 0) {
    bar.classList.remove("hidden");
    $("day-bar-text").textContent = "你还有 " + n + " 件待对齐的活——沉默会被默认为答应（§6.8）。2 分钟生成对齐记录，把结论钉给对方。";
  } else { bar.classList.add("hidden"); }
}

function localAlignText() {
  var rows = reqs.filter(function (r) { return r.status === "pending" || r.status === "aligned"; });
  if (!rows.length) return "当前没有待对齐的加活。";
  var lines = ["本周对齐记录（PushIt 生成）", ""];
  rows.forEach(function (r, i) {
    lines.push((i + 1) + ". " + r.text + "（提出：" + r.person + "）—— 待对齐");
  });
  lines.push("", "以上均未计入本周承诺；请确认优先级后再排期。");
  return lines.join("\n");
}

function showNoteCard(text) {
  var card = $("report-card"); card.classList.remove("hidden");
  card.innerHTML = '<div class="badge accept">对齐记录 · 可复制</div>' +
    '<div class="script" style="white-space:pre-wrap">' + ESC(text) + "</div>" +
    '<div class="actions"><button id="btn-copynote">复制全文</button></div>';
  $("btn-copynote").onclick = function () { copyText(text); };
  window.scrollTo({ top: card.offsetTop - 80, behavior: "smooth" });
}

function shareCard(r) {
  var txt = (r.script || "") + "\n\n—— 来自 PushIt：让不合理需求自己现形（分享卡已去标识化）";
  showNoteCard(txt);
}

function summaryNote() {
  if (API_BASE) {
    fetch(API_BASE + "/notes/summary", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ use_llm: llmOn() }) })
      .then(function (r) { return r.json(); })
      .then(function (d) { showNoteCard(d.text); })
      .catch(function () { showNoteCard("后端未启动：请保持 ?api=1 并启动后端（8765）。"); });
  } else { showNoteCard("1:1 摘要需后端（?api=1 模式）；本地 mock 版待精进。"); }
}

function alignNote() {
  if (API_BASE) {
    fetch(API_BASE + "/notes/alignment", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ use_llm: llmOn() }) })
      .then(function (r) { return r.json(); })
      .then(function (d) { showNoteCard(d.text); })
      .catch(function () { showNoteCard(localAlignText()); });
  } else { showNoteCard(localAlignText()); }
}

var rehearseHistory = "";
function appendChat(who, text) {
  var d = document.createElement("div");
  d.className = "bubble " + who;
  d.textContent = text;
  $("chat-box").appendChild(d);
  $("chat-box").scrollTop = $("chat-box").scrollHeight;
}
function localRehearseReply(pname) {
  if (pname === "小李") return "（小李）行啊——不过这个真的很简单，你顺手弄一下呗？";
  return "（" + pname + "）那你说说，这周你手里哪些能挪？";
}
function sendRehearse() {
  var pname = $("rehearse-person").value;
  var pp = findPerson(pname);
  var role = (pp && pp.role) || "中层";
  var line = $("rehearse-line").value.trim();
  if (!line) return;
  appendChat("me", line);
  $("rehearse-line").value = "";
  if (API_BASE) {
    fetch(API_BASE + "/rehearse", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ person_name: pname, role: role, your_line: line, history: rehearseHistory }) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        rehearseHistory += "我：" + line + "\n对方：" + d.reply + "\n";
        appendChat("them", d.reply);
      })
      .catch(function () { var rep = localRehearseReply(pname); rehearseHistory += "我：" + line + "\n对方：" + rep + "\n"; appendChat("them", rep); });
  } else {
    var rep = localRehearseReply(pname);
    rehearseHistory += "我：" + line + "\n对方：" + rep + "\n";
    appendChat("them", rep);
  }
}

function showPlan(name, li) {
  var box = li.querySelector(".plan");
  if (!box.classList.contains("hidden")) { box.classList.add("hidden"); return; }
  var plans = {
    "王组长": ["这周硬上，演示会那场有风险——我建议保演示会，这条挪下周二，您看？",
      "我记下了，排期会一起过优先级；会上我把和现有 3 件事的冲突摆出来。",
      "可以，但需要先把 X 挪后，您帮我定挪哪条。"],
    "赵总": ["我的判断是这条和季度目标冲突，您看是不是先保核心迁移？",
      "我按您拍板的优先级来——请确认哪条可以暂缓。"],
    "小李": ["你先给我范围和原始数据，我对齐后再评估。",
      "这不在已对齐承诺里，先找组长对齐优先级？"]
  };
  var rows = plans[name] || ["先给明确结论，再给理由与替代（先明确、后台阶）。"];
  box.innerHTML = "";
  rows.forEach(function (p) {
    var d = document.createElement("div"); d.textContent = "· " + p;
    box.appendChild(d);
  });
  box.classList.remove("hidden");
}

/* ---------- 情绪树洞（§5 树洞窗口）：倾诉共情 + 隐形画像吸收 ---------- */
var TH_KEY = "pushit_treehole_v1";   // 树洞独立分仓，与台账/人物隔离
var TH_RULES = [
  "我在听。先把最堵的那件说出来，不用组织语言。",
  "嗯，这件事听起来确实很消耗人。后来呢？",
  "被这样对待还压在心里，换谁都会难受。你最气的是哪一点？",
  "我记下了。你觉得对方当时是有意的，还是没意识到？",
  "说出来的那一刻，它对你的控制就小了一分。还有别的吗？"
];
var TH_RULE_I = 0;
function thLoadLocal() {
  try { var raw = localStorage.getItem(TH_KEY); if (raw) return JSON.parse(raw); } catch (e) {}
  return [];
}
function thSaveLocal(msgs) { try { localStorage.setItem(TH_KEY, JSON.stringify(msgs)); } catch (e) {} }
function thAppend(who, text) {
  var d = document.createElement("div");
  d.className = "bubble " + who;
  d.textContent = text;
  $("th-chat").appendChild(d);
  $("th-chat").scrollTop = $("th-chat").scrollHeight;
}
function renderTreehole() {
  $("th-chat").innerHTML = "";
  if (API_BASE) {
    fetch(API_BASE + "/treehole")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        (d.messages || []).forEach(function (m) { thAppend(m.role === "user" ? "me" : "them", m.content); });
        if (!d.messages || !d.messages.length) thAppend("them", "这里只属于你。最近有什么让你憋着难受的？");
      })
      .catch(function () { thRenderLocal(); });
  } else { thRenderLocal(); }
}
function thRenderLocal() {
  var msgs = thLoadLocal();
  if (!msgs.length) thAppend("them", "这里只属于你。最近有什么让你憋着难受的？");
  msgs.forEach(function (m) { thAppend(m.role === "user" ? "me" : "them", m.content); });
}
function sendTreehole() {
  var line = $("th-line").value.trim();
  if (!line) return;
  thAppend("me", line);
  $("th-line").value = "";
  if (API_BASE) {
    fetch(API_BASE + "/treehole", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: line, use_llm: llmOn() }) })
      .then(function (r) { return r.json(); })
      .then(function (d) { thAppend("them", d.reply); })
      .catch(function () { thAppend("them", TH_RULES[TH_RULE_I++ % TH_RULES.length]); });
  } else {
    var msgs = thLoadLocal();
    msgs.push({ role: "user", content: line });
    var rep = TH_RULES[TH_RULE_I++ % TH_RULES.length];
    msgs.push({ role: "assistant", content: rep });
    thSaveLocal(msgs);
    thAppend("them", rep);
  }
}
function clearTreehole() {
  if (!confirm("清空全部树洞记录？只删树洞倾诉，不影响台账与画像积累。")) return;
  if (API_BASE) {
    fetch(API_BASE + "/treehole", { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function () { $("th-chat").innerHTML = ""; thAppend("them", "树洞已清空。这里只属于你。"); })
      .catch(function () {});
  } else { thSaveLocal([]); $("th-chat").innerHTML = ""; thAppend("them", "树洞已清空。这里只属于你。"); }
}

function exportData() {
  var data = { version: "pushit_reqs_v1", exported_at: new Date().toISOString(), requirements: reqs };
  var json = JSON.stringify(data, null, 2);
  try {
    var blob = new Blob([json], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "pushit_export.json";
    document.body.appendChild(a); a.click(); a.remove();
  } catch (e) {}
  copyText(json);
}

function wipeData() {
  if (!confirm("确定清空本地全部数据？此操作不可恢复。")) return;
  try { localStorage.removeItem("pushit_reqs_v1"); localStorage.removeItem("pushit_demo_reqs"); } catch (e) {}
  reqs = []; saveReqs(); renderAll();
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("#tabs button").forEach(function (b) {
    b.onclick = function () { switchView(b.getAttribute("data-view")); };
  });
  $("btn-process").onclick = function () {
    var text = $("in-text").value.trim();
    if (!text) { $("hint-line").textContent = "先把话贴进来（口头加活大多落在消息里）。"; return; }
    var pk = $("in-person").value;
    if (!pk) { $("hint-line").textContent = "先点“＋提出人”建立人物，画像与账本都挂在这人身上。"; return; }
    var src = $("in-source").value;
    if (API_BASE) { apiProcess(text, pk, src); return; }
    var r = mockProcess(text, pk, src);
    renderReport(r);
    $("hint-line").textContent = "";
    window.scrollTo({ top: $("report-card").offsetTop - 80, behavior: "smooth" });
  };
  $("btn-example").onclick = function () {
    var exs = ["顺手把报表导出权限也开了，这周一起上", "帮市场部临时拉个经营看板，很快", "这周把全量数据迁移也做了吧，顺带把老权限逻辑梳理一遍，月底要演示会"];
    $("in-text").value = exs[Math.floor(Math.random() * exs.length)];
  };
  $("btn-align").onclick = alignNote;
  $("btn-summary").onclick = summaryNote;
  $("btn-rehearse").onclick = sendRehearse;
  $("btn-treehole").onclick = sendTreehole;
  $("btn-treehole-clear").onclick = clearTreehole;
  $("btn-export").onclick = exportData;
  $("btn-wipe").onclick = wipeData;
  if (isDemo()) { var ex = $("btn-example"); if (ex) ex.classList.remove("hidden"); }
  $("btn-help").onclick = function () { $("help-panel").classList.toggle("hidden"); };
  $("btn-help-close").onclick = function () { $("help-panel").classList.add("hidden"); };
  $("btn-add-person").onclick = function () { addPersonFlow(); };
  $("ap-ok").onclick = function () { confirmAddPerson(); };
  $("ap-cancel").onclick = function () { $("add-person-form").classList.add("hidden"); };
  renderPersonSelects();
  var demoBtn = $("btn-demo");
  if (demoBtn) {
    demoBtn.textContent = isDemo() ? "退出演示模式" : "载入演示数据（体验示例）";
    demoBtn.onclick = function () {
      var sep = location.search ? "&" : "?";
      if (isDemo()) { location.href = location.pathname + location.search.replace(/[&?]demo=1/, ""); }
      else { location.href = location.pathname + location.search + sep + "demo=1"; }
    };
  }
  try {
    var apiInput = $("opt-api-base");
    if (apiInput) apiInput.value = localStorage.getItem("pushit_api_base") || "";
  } catch (e) {}
  $("btn-save-api").onclick = function () {
    var v = $("opt-api-base").value.trim();
    if (v) localStorage.setItem("pushit_api_base", v); else localStorage.removeItem("pushit_api_base");
    $("hint-line").textContent = "后端地址已保存，刷新页面生效。";
  };
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(function () {});
  }
  switchView("ledger"); renderAll();
});
