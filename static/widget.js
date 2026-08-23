/*
 * SRU Assist - embeddable chat widget for the university portal.
 *
 * INTEGRATION (for portal developers):
 *   <script>
 *     window.SRU_CHAT = { apiUrl: "https://your-api-host" };
 *   </script>
 *   <script src="https://your-api-host/static/widget.js"></script>
 *
 * If apiUrl is omitted the widget calls the same origin it is served from.
 */
(function () {
  "use strict";

  var cfg = window.SRU_CHAT || {};
  var API = (cfg.apiUrl || (function () {
    var s = document.currentScript && document.currentScript.src;
    return s ? new URL("/", s).origin : "";
  })()).replace(/\/$/, "");

  var BOT_NAME = cfg.botName || "SRU Assist";
  var WELCOME =
    cfg.welcome ||
    "Hi! I'm SRU Assist 🤖\nAsk me about credits, grading, CGPA, pass marks, attendance, exams or any handbook rule.";

  var SUGGESTIONS = [
    "How is CGPA calculated?",
    "Minimum pass marks?",
    "Attendance requirement?",
    "What is the grading scale?",
  ];

  // ---------- styles ----------
  var css = [
    ".srucw-root{all:initial;font-family:'Segoe UI',system-ui,sans-serif}",
    ".srucw-bubble{position:fixed;right:22px;bottom:22px;width:60px;height:60px;border-radius:50%;",
    "background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;border:none;cursor:pointer;",
    "box-shadow:0 8px 24px rgba(79,70,229,.45);font-size:26px;z-index:99998;display:flex;",
    "align-items:center;justify-content:center;transition:transform .15s ease}",
    ".srucw-bubble:hover{transform:scale(1.08)}",
    ".srucw-panel{position:fixed;right:22px;bottom:94px;width:370px;max-width:calc(100vw - 32px);",
    "height:540px;max-height:calc(100vh - 130px);background:#fff;border-radius:16px;z-index:99999;",
    "box-shadow:0 24px 64px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;",
    "border:1px solid #e5e7eb}",
    ".srucw-panel.open{display:flex}",
    ".srucw-head{background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;padding:14px 16px;",
    "display:flex;align-items:center;gap:10px}",
    ".srucw-avatar{width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.2);",
    "display:flex;align-items:center;justify-content:center;font-size:18px}",
    ".srucw-title{font-size:15px;font-weight:600;line-height:1.2}",
    ".srucw-sub{font-size:11px;opacity:.85}",
    ".srucw-close{margin-left:auto;background:none;border:none;color:#fff;font-size:20px;cursor:pointer;opacity:.9}",
    ".srucw-msgs{flex:1;overflow-y:auto;padding:14px;background:#f6f7fb;display:flex;flex-direction:column;gap:10px}",
    ".srucw-row{display:flex;gap:8px;align-items:flex-end}",
    ".srucw-row.user{flex-direction:row-reverse}",
    ".srucw-msg{max-width:80%;padding:9px 12px;border-radius:14px;font-size:13.5px;line-height:1.45;",
    "white-space:pre-wrap;word-wrap:break-word}",
    ".srucw-msg.bot{background:#fff;color:#111827;border:1px solid #e5e7eb;border-bottom-left-radius:4px}",
    ".srucw-msg.user{background:#4f46e5;color:#fff;border-bottom-right-radius:4px}",
    ".srucw-cite{display:inline-block;margin-top:6px;font-size:10.5px;color:#6d28d9;background:#ede9fe;",
    "border-radius:6px;padding:2px 7px;font-weight:600}",
    ".srucw-sugg{padding:0 14px 8px;background:#f6f7fb;display:flex;gap:6px;flex-wrap:wrap}",
    ".srucw-sugg button{font-size:11.5px;color:#4f46e5;background:#fff;border:1px solid #c7d2fe;",
    "border-radius:999px;padding:5px 11px;cursor:pointer}",
    ".srucw-sugg button:hover{background:#eef2ff}",
    ".srucw-inputbar{display:flex;gap:8px;padding:12px;border-top:1px solid #e5e7eb;background:#fff}",
    ".srucw-input{flex:1;border:1px solid #d1d5db;border-radius:10px;padding:9px 12px;font-size:13.5px;outline:none}",
    ".srucw-input:focus{border-color:#4f46e5}",
    ".srucw-send{background:#4f46e5;color:#fff;border:none;border-radius:10px;padding:9px 16px;",
    "font-size:13.5px;font-weight:600;cursor:pointer}",
    ".srucw-send:disabled{opacity:.55;cursor:default}",
    ".srucw-typing span{display:inline-block;width:6px;height:6px;margin:0 1.5px;border-radius:50%;",
    "background:#9ca3af;animation:srucwBlink 1.2s infinite}",
    ".srucw-typing span:nth-child(2){animation-delay:.2s}",
    ".srucw-typing span:nth-child(3){animation-delay:.4s}",
    "@keyframes srucwBlink{0%,80%,100%{opacity:.25}40%{opacity:1}}",
  ].join("");

  // ---------- dom ----------
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var root = el("div", "srucw-root");
  root.id = "sru-assist-widget";

  var panel = el("div", "srucw-panel");
  panel.innerHTML =
    '<div class="srucw-head"><div class="srucw-avatar">🎓</div><div>' +
    '<div class="srucw-title"></div><div class="srucw-sub">Student Handbook AI</div></div>' +
    '<button class="srucw-close" aria-label="Close chat">×</button></div>';
  panel.querySelector(".srucw-title").textContent = BOT_NAME;

  var msgsBox = el("div", "srucw-msgs");
  var suggBox = el("div", "srucw-sugg");
  var inputBar = el("div", "srucw-inputbar");
  var input = el("input", "srucw-input");
  input.placeholder = "Ask about credits, grades…";
  var sendBtn = el("button", "srucw-send", "Send");
  inputBar.appendChild(input);
  inputBar.appendChild(sendBtn);
  panel.appendChild(msgsBox);
  panel.appendChild(suggBox);
  panel.appendChild(inputBar);

  var bubble = el("button", "srucw-bubble", "💬");
  bubble.setAttribute("aria-label", "Open SRU Assist chat");

  root.appendChild(panel);
  root.appendChild(bubble);
  document.body.appendChild(root);

  // ---------- state ----------
  var history = [];
  var busy = false;

  function addMsg(role, text, cites) {
    var row = el("div", "srucw-row " + role);
    var b = el("div", "srucw-msg " + role, text);
    row.appendChild(b);
    if (cites && cites.length) {
      b.appendChild(el("br"));
      b.appendChild(el("span", "srucw-cite", "📖 Handbook " + cites.join(", ")));
    }
    msgsBox.appendChild(row);
    msgsBox.scrollTop = msgsBox.scrollHeight;
    return b;
  }

  function typing(on) {
    var t = msgsBox.querySelector(".srucw-typing-row");
    if (on && !t) {
      var row = el("div", "srucw-row bot srucw-typing-row");
      var m = el("div", "srucw-msg bot srucw-typing");
      m.innerHTML = "<span></span><span></span><span></span>";
      row.appendChild(m);
      msgsBox.appendChild(row);
      msgsBox.scrollTop = msgsBox.scrollHeight;
    } else if (!on && t) t.remove();
  }

  SUGGESTIONS.forEach(function (s) {
    var b = el("button", null, s);
    b.onclick = function () { ask(s); };
    suggBox.appendChild(b);
  });

  function ask(text) {
    text = (text || input.value).trim();
    if (!text || busy) return;
    input.value = "";
    busy = true;
    sendBtn.disabled = true;
    addMsg("user", text);
    typing(true);

    fetch(API + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: history }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        typing(false);
        var ans = data.answer || data.error || "Something went wrong.";
        addMsg("bot", ans, data.citations);
        history.push({ role: "user", content: text });
        history.push({ role: "assistant", content: ans });
      })
      .catch(function () {
        typing(false);
        addMsg("bot", "⚠️ Could not reach the server. Is the API running?");
      })
      .then(function () {
        busy = false;
        sendBtn.disabled = false;
        input.focus();
      });
  }

  sendBtn.onclick = function () { ask(); };
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") ask();
  });

  bubble.onclick = function () {
    var open = panel.classList.toggle("open");
    bubble.textContent = open ? "×" : "💬";
    if (open) {
      if (!msgsBox.children.length) {
        addMsg("bot", WELCOME);
        history.push({ role: "assistant", content: WELCOME });
      }
      input.focus();
    }
  };
})();
