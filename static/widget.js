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
    ".srucw-msg.bot{background:#fff;color:#111827;border:1px solid #e5e7eb;border-bottom-left-radius:4px;white-space:normal}",
    ".srucw-msg.user{background:#4f46e5;color:#fff;border-bottom-right-radius:4px}",
    ".srucw-msg table{border-collapse:collapse;width:100%;margin:6px 0;font-size:12px}",
    ".srucw-msg th,.srucw-msg td{border:1px solid #e5e7eb;padding:4px 7px;text-align:left}",
    ".srucw-msg th{background:#f3f4f6;font-weight:600}",
    ".srucw-msg ul,.srucw-msg ol{margin:4px 0 6px;padding-left:18px}",
    ".srucw-msg li{margin:2.5px 0}",
    ".srucw-msg h3,.srucw-msg h4{margin:8px 0 4px;font-size:13px;color:#111827}",
    ".srucw-msg p{margin:0 0 7px}",
    ".srucw-msg p:last-child{margin-bottom:0}",
    ".srucw-msg code{background:#eef2ff;border-radius:4px;padding:1px 5px;font-size:12px}",
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

  // ---------- mini markdown ----------
  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function inline(t) {
    return t
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?:;]|$)/g, "$1<em>$2</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
  }

  function cells(line) {
    return line.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map(function (c) { return c.trim(); });
  }

  function renderMarkdown(raw) {
    var s = raw
      .replace(/\\\[([\s\S]*?)\\\]/g, "$1")   // \[ ... \] -> content
      .replace(/\\\(([\s\S]*?)\\\)/g, "$1");  // \( ... \) -> content
    s = s
      .replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "($1) ÷ ($2)")
      .replace(/\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "($1) ÷ ($2)")
      .replace(/\\times/g, " × ").replace(/\\cdot/g, " · ")
      .replace(/\\sum/g, "Σ").replace(/\\approx/g, "≈")
      .replace(/\\text\s*\{([^{}]*)\}/g, "$1");
    s = esc(s);
    s = s.replace(/_\{?([A-Za-z0-9])\}?/g, "<sub>$1</sub>");

    var lines = s.split("\n"), out = [], i = 0, m;
    while (i < lines.length) {
      var L = lines[i];
      if (/^\s*$/.test(L)) { i++; continue; }

      if ((m = L.match(/^\s*#{1,6}\s+(.*)$/))) {
        out.push("<h4>" + inline(m[1]) + "</h4>"); i++; continue;
      }

      if (L.indexOf("|") >= 0 && i + 1 < lines.length &&
          /^\s*\|?[\s:|\-]+\|?\s*$/.test(lines[i + 1]) && lines[i + 1].indexOf("-") >= 0) {
        var head = cells(L), body = [];
        i += 2;
        while (i < lines.length && lines[i].indexOf("|") >= 0 && !/^\s*$/.test(lines[i])) {
          body.push(cells(lines[i])); i++;
        }
        var t = "<table><thead><tr>";
        head.forEach(function (c) { t += "<th>" + inline(c) + "</th>"; });
        t += "</tr></thead><tbody>";
        body.forEach(function (r) {
          t += "<tr>"; r.forEach(function (c) { t += "<td>" + inline(c) + "</td>"; }); t += "</tr>";
        });
        out.push(t + "</tbody></table>");
        continue;
      }

      if (/^\s*[-*•]\s+/.test(L)) {
        var ul = "<ul>";
        while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) {
          ul += "<li>" + inline(lines[i].replace(/^\s*[-*•]\s+/, "")) + "</li>"; i++;
        }
        out.push(ul + "</ul>"); continue;
      }

      if (/^\s*\d+[.)]\s+/.test(L)) {
        var ol = "<ol>";
        while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
          ol += "<li>" + inline(lines[i].replace(/^\s*\d+[.)]\s+/, "")) + "</li>"; i++;
        }
        out.push(ol + "</ol>"); continue;
      }

      out.push("<p>" + inline(L.trim()) + "</p>"); i++;
    }
    return out.join("");
  }

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
    var b = el("div", "srucw-msg " + role);
    if (role === "bot") { b.innerHTML = renderMarkdown(text); }
    else { b.textContent = text; }
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
