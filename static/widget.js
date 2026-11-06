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

  var BOT_NAME = cfg.botName || "AURA";
  var WELCOME =
    cfg.welcome ||
    "Hi! I'm AURA 🤖\n(Autonomous University RAG Agent)\n\nAsk me about credits, grading, CGPA, pass marks, attendance, exams or any handbook rule.";

  var SUGGESTIONS = [
    "Promotion rules",
    "Attendance criteria",
    "CGPA / grading",
  ];

  // ---------- styles ----------
  var css = [
    ".srucw-root{all:initial;font-family:'Segoe UI',system-ui,sans-serif}",
    ".srucw-bubble{position:fixed;right:22px;bottom:22px;width:60px;height:60px;border-radius:50%;",
    "background:linear-gradient(135deg,#23468A,#3E6BC0);color:#fff;border:none;cursor:pointer;",
    "box-shadow:0 8px 24px rgba(79,70,229,.45);font-size:26px;z-index:99998;display:flex;",
    "align-items:center;justify-content:center;transition:transform .15s ease}",
    ".srucw-bubble:hover{transform:scale(1.08)}",
    ".srucw-panel{position:fixed;right:22px;bottom:94px;width:460px;max-width:calc(100vw - 32px);",
    "height:min(680px,calc(100vh - 120px));background:#fff;border-radius:16px;z-index:99999;",
    "box-shadow:0 24px 64px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;",
    "border:1px solid #e5e7eb}",
    ".srucw-panel.open{display:flex}",
    ".srucw-head{background:linear-gradient(135deg,#23468A,#3E6BC0);color:#fff;padding:12px 14px;",
    "display:flex;align-items:center;gap:10px}",
    ".srucw-avatar{width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.2);",
    "display:flex;align-items:center;justify-content:center;font-size:18px}",
    ".srucw-title{font-size:15px;font-weight:600;line-height:1.2}",
    ".srucw-sub{font-size:11px;opacity:.9;display:flex;align-items:center;gap:4px}",
    ".srucw-badge{background:rgba(255,255,255,.22);border-radius:10px;padding:2px 7px;font-size:10.5px;",
    "font-weight:600;display:inline-flex;align-items:center;gap:4px;cursor:pointer}",
    ".srucw-badge:hover{background:rgba(255,255,255,.35)}",
    ".srucw-badge-x{font-size:11px;opacity:.8;margin-left:2px}",
    ".srucw-badge-x:hover{opacity:1;color:#ffcaca}",
    ".srucw-clear{margin-left:auto;background:rgba(255,255,255,.16);border:none;color:#fff;border-radius:6px;font-size:13px;cursor:pointer;opacity:.9;padding:4px 7px;display:flex;align-items:center;transition:background .15s ease}",
    ".srucw-clear:hover{background:rgba(255,255,255,.28);opacity:1}",
    ".srucw-msgs{flex:1;overflow-y:auto;padding:14px;background:#f6f7fb;display:flex;flex-direction:column;gap:10px}",
    ".srucw-row{display:flex;gap:8px;align-items:flex-end}",
    ".srucw-row.user{flex-direction:row-reverse}",
    ".srucw-msg{max-width:80%;padding:9px 12px;border-radius:14px;font-size:13.5px;line-height:1.45;",
    "white-space:pre-wrap;word-wrap:break-word}",
    ".srucw-msg.bot{background:#fff;color:#111827;border:1px solid #e5e7eb;border-bottom-left-radius:4px;white-space:normal;overflow-x:auto}",
    ".srucw-msg.user{background:#23468A;color:#fff;border-bottom-right-radius:4px}",
    ".srucw-msg table{border-collapse:collapse;width:100%;margin:6px 0;font-size:11.5px}",
    ".srucw-msg th,.srucw-msg td{border:1px solid #e5e7eb;padding:3.5px 6px;text-align:left}",
    ".srucw-msg th{background:#f3f4f6;font-weight:600}",
    ".srucw-msg ul,.srucw-msg ol{margin:4px 0 6px;padding-left:18px}",
    ".srucw-msg li{margin:2.5px 0}",
    ".srucw-msg h3,.srucw-msg h4{margin:8px 0 4px;font-size:13px;color:#111827}",
    ".srucw-msg p{margin:0 0 7px}",
    ".srucw-msg p:last-child{margin-bottom:0}",
    ".srucw-msg code{background:#dbe7f7;border-radius:4px;padding:1px 5px;font-size:12px}",
    ".srucw-cite{display:inline-block;margin-top:6px;font-size:10.5px;color:#23468A;background:#dbe7f7;",
    "border-radius:6px;padding:2px 7px;font-weight:600}",
    ".srucw-sugg{padding:0 14px 8px;background:#f6f7fb;display:flex;gap:6px;flex-wrap:wrap}",
    ".srucw-sugg button{font-size:11.5px;color:#23468A;background:#fff;border:1px solid #b7cbe8;",
    "border-radius:999px;padding:5px 11px;cursor:pointer}",
    ".srucw-sugg button:hover{background:#dbe7f7}",
    ".srucw-inputbar{display:flex;gap:8px;padding:12px;border-top:1px solid #e5e7eb;background:#fff}",
    ".srucw-input{flex:1;border:1px solid #d1d5db;border-radius:10px;padding:9px 12px;font-size:13.5px;outline:none}",
    ".srucw-input:focus{border-color:#23468A}",
    ".srucw-send{background:#23468A;color:#fff;border:none;border-radius:10px;padding:9px 16px;",
    "font-size:13.5px;font-weight:600;cursor:pointer;transition:background .2s ease}",
    ".srucw-send.srucw-stop{background:#dc2626;color:#fff}",
    ".srucw-send.srucw-stop:hover{background:#b91c1c}",
    ".srucw-send:disabled{opacity:.55;cursor:default}",
    ".srucw-typing span{display:inline-block;width:6px;height:6px;margin:0 1.5px;border-radius:50%;",
    "background:#9ca3af;animation:srucwBlink 1.2s infinite}",
    ".srucw-typing span:nth-child(2){animation-delay:.2s}",
    ".srucw-typing span:nth-child(3){animation-delay:.4s}",
    "@keyframes srucwBlink{0%,80%,100%{opacity:.25}40%{opacity:1}}",
    ".srucw-history-divider{display:flex;align-items:center;text-align:center;color:#6b7280;font-size:11px;margin:10px 0;gap:8px}",
    ".srucw-history-divider span{background:#e5e7eb;color:#4b5563;padding:2px 8px;border-radius:10px;font-weight:600}",
    ".srucw-history-divider::before,.srucw-history-divider::after{content:'';flex:1;border-bottom:1px dashed #cbd5e1}",
    ".srucw-cta-container{margin-top:9px;padding:9px 11px;background:#f0f4fc;border:1px solid #c9dafb;border-radius:10px}",
    ".srucw-cta-header{font-size:10.5px;font-weight:700;color:#23468A;margin-bottom:6px;display:flex;align-items:center;gap:4px;text-transform:uppercase;letter-spacing:0.5px}",
    ".srucw-cta-bar{display:flex;flex-wrap:wrap;gap:6px}",
    ".srucw-cta-btn{font-size:11.5px;font-weight:600;text-decoration:none;padding:5px 10px;border-radius:6px;border:1px solid #23468A;background:#fff;color:#23468A;cursor:pointer;display:inline-flex;align-items:center;gap:4px;transition:all .15s ease;font-family:inherit}",
    ".srucw-cta-btn:hover{background:#23468A;color:#fff}",
    ".srucw-cta-call{border-color:#16a34a;color:#16a34a}",
    ".srucw-cta-call:hover{background:#16a34a;color:#fff}",
    ".srucw-cta-mail{border-color:#2563eb;color:#2563eb;background:#eff6ff}",
    ".srucw-cta-mail:hover{background:#2563eb;color:#fff}",
    ".srucw-cta-copy{border-color:#64748b;color:#475569}",
    ".srucw-cta-copy:hover{background:#475569;color:#fff}",
    ".srucw-modal-backdrop{position:absolute;inset:0;background:rgba(15,23,42,.65);backdrop-filter:blur(2px);z-index:100000;display:flex;align-items:center;justify-content:center;padding:12px}",
    ".srucw-modal{background:#fff;border-radius:12px;width:100%;max-height:94%;display:flex;flex-direction:column;box-shadow:0 20px 40px rgba(0,0,0,.3);overflow:hidden;border:1px solid #cbd5e1;font-family:inherit}",
    ".srucw-modal-head{background:linear-gradient(135deg,#23468A,#3E6BC0);color:#fff;padding:10px 14px;display:flex;align-items:center;justify-content:space-between}",
    ".srucw-modal-title{font-size:13px;font-weight:700;display:flex;align-items:center;gap:6px}",
    ".srucw-modal-close{background:none;border:none;color:#fff;font-size:16px;cursor:pointer;opacity:.8;padding:2px 6px;border-radius:4px}",
    ".srucw-modal-close:hover{opacity:1;background:rgba(255,255,255,.2)}",
    ".srucw-modal-body{padding:12px 14px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:8px;font-size:12px}",
    ".srucw-field{display:flex;flex-direction:column;gap:3px}",
    ".srucw-field label{font-size:10px;font-weight:700;color:#475569;text-transform:uppercase}",
    ".srucw-field input,.srucw-field textarea{width:100%;padding:6px 9px;font-size:12px;border:1px solid #cbd5e1;border-radius:6px;outline:none;font-family:inherit;box-sizing:border-box}",
    ".srucw-field input:focus,.srucw-field textarea:focus{border-color:#23468A;box-shadow:0 0 0 2px rgba(35,70,138,.15)}",
    ".srucw-field input[readonly]{background:#f8fafc;color:#64748b}",
    ".srucw-field textarea{resize:vertical;min-height:120px;font-size:11.5px;line-height:1.45}",
    ".srucw-modal-footer{padding:10px 14px;background:#f8fafc;border-top:1px solid #e2e8f0;display:flex;gap:8px;justify-content:flex-end;align-items:center}",
    ".srucw-btn-pri{background:#23468A;color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:4px}",
    ".srucw-btn-pri:hover{background:#1a3466;color:#fff}",
    ".srucw-btn-sec{background:#fff;color:#334155;border:1px solid #cbd5e1;border-radius:6px;padding:7px 12px;font-size:12px;font-weight:600;cursor:pointer}",
    ".srucw-btn-sec:hover{background:#f1f5f9}",
    ".srucw-toast{position:absolute;bottom:65px;left:50%;transform:translateX(-50%);background:#0f172a;color:#fff;font-size:11.5px;font-weight:600;padding:6px 14px;border-radius:20px;box-shadow:0 4px 12px rgba(0,0,0,.25);z-index:100001;pointer-events:none;transition:opacity .3s}",
    ".srucw-close{background:rgba(255,255,255,.16);border:none;color:#fff;border-radius:6px;font-size:14px;cursor:pointer;opacity:.9;padding:4px 8px;display:flex;align-items:center;transition:background .15s ease}",
    ".srucw-close:hover{background:rgba(255,255,255,.28);opacity:1}",
    "@media(max-width:600px){",
    "  .srucw-panel{position:fixed!important;top:0!important;left:0!important;right:0!important;bottom:0!important;width:100%!important;max-width:100vw!important;height:100%!important;height:100dvh!important;border-radius:0!important;border:none!important;box-shadow:none!important;z-index:999999!important}",
    "  .srucw-panel.open ~ .srucw-bubble{display:none!important}",
    "  .srucw-bubble{right:16px;bottom:16px;width:54px;height:54px;font-size:24px}",
    "  .srucw-msg{max-width:88%}",
    "  .srucw-inputbar{padding:10px 12px;padding-bottom:max(10px,env(safe-area-inset-bottom,10px))}",
    "  .srucw-input{font-size:16px!important}",
    "  .srucw-cta-bar{gap:6px}",
    "  .srucw-cta-btn{flex:1 1 auto;text-align:center;justify-content:center}",
    "  .srucw-modal{max-height:92dvh;border-radius:12px 12px 0 0}",
    "}",
    "@media(max-width:360px){",
    "  .srucw-title{font-size:13.5px}",
    "  .srucw-sub{font-size:10px}",
    "  .srucw-msg{max-width:94%;font-size:13px}",
    "  .srucw-sugg button{font-size:10.5px;padding:4px 8px}",
    "  .srucw-inputbar{gap:6px;padding:8px 10px}",
    "  .srucw-send{padding:8px 12px;font-size:12.5px}",
    "}",
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
    '<div style="margin-left:auto;display:flex;align-items:center;gap:6px">' +
    '<button class="srucw-clear" title="Clear chat & reset" aria-label="Clear chat">🔄</button>' +
    '<button class="srucw-close" title="Close chat" aria-label="Close chat">✕</button></div></div>';
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
  bubble.setAttribute("aria-label", "Open AURA chat");

  root.appendChild(panel);
  root.appendChild(bubble);
  document.body.appendChild(root);

  // ---------- state ----------
  var history = [];
  var busy = false;
  var PF_KEY = "sru_profile";
  var SESS_KEY = "sru_chat_msgs";
  var SESS_ID_KEY = "sru_session_id";

  function getSessionId() {
    var sid = localStorage.getItem(SESS_ID_KEY);
    if (!sid) {
      sid = "sess_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
      localStorage.setItem(SESS_ID_KEY, sid);
    }
    return sid;
  }

  function fetchAndRestoreHistory(htno, onComplete) {
    if (!htno) return;
    fetch(API + "/api/history?htno=" + encodeURIComponent(htno))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.profile) {
          for (var k in data.profile) { profile[k] = data.profile[k]; }
          saveProfile();
        }
        if (data && Array.isArray(data.messages) && data.messages.length > 0) {
          msgsBox.innerHTML = "";
          history = [];
          addMsg("bot", WELCOME);
          history.push({ role: "assistant", content: WELCOME });

          var divRow = el("div", "srucw-history-divider");
          divRow.innerHTML = "<span>Previous Conversation Restored</span>";
          msgsBox.appendChild(divRow);

          data.messages.forEach(function (m) {
            addMsg(m.role === "user" ? "user" : "bot", m.content, m.citations, m.cta);
            history.push({ role: m.role, content: m.content, citations: m.citations, cta: m.cta });
          });
          saveSessionMsgs();
          msgsBox.scrollTop = msgsBox.scrollHeight;
        }
        if (data && Array.isArray(data.suggestions) && data.suggestions.length > 0) {
          setChips(data.suggestions);
        }
        if (typeof onComplete === "function") onComplete(data);
      })
      .catch(function (err) {
        console.warn("History restore failed:", err);
        if (typeof onComplete === "function") onComplete(null);
      });
  }

  function saveSessionMsgs() {
    try { sessionStorage.setItem(SESS_KEY, JSON.stringify(history)); } catch (e) {}
  }

  function loadSessionMsgs() {
    try {
      var saved = JSON.parse(sessionStorage.getItem(SESS_KEY) || "[]");
      if (Array.isArray(saved) && saved.length) {
        if (saved[0] && saved[0].role === "assistant" && /SRU Assist/i.test(saved[0].content)) {
          saved[0].content = WELCOME;
        }
        history = saved;
        msgsBox.innerHTML = "";
        history.forEach(function (m) {
          addMsg(m.role === "user" ? "user" : "bot", m.content, m.citations, m.cta);
        });
        saveSessionMsgs();
        return true;
      }
    } catch (e) {}
    return false;
  }

  var clearBtn = panel.querySelector(".srucw-clear");
  if (clearBtn) {
    clearBtn.onclick = function (e) {
      e.stopPropagation();
      if (busy) stopCurrentTask();
      var oldSid = getSessionId();
      var oldHtno = profile && profile.roll_number;
      try {
        var delUrl = API + "/api/history?" + (oldHtno ? "htno=" + encodeURIComponent(oldHtno) : "session_id=" + encodeURIComponent(oldSid));
        fetch(delUrl, { method: "DELETE" }).catch(function () {});
      } catch (err) {}
      localStorage.removeItem(SESS_ID_KEY);
      history = [];
      try { sessionStorage.removeItem(SESS_KEY); } catch (err) {}
      msgsBox.innerHTML = "";
      addMsg("bot", WELCOME);
      history.push({ role: "assistant", content: WELCOME });
      saveSessionMsgs();
      refreshSuggestions();
    };
  }

  var closeHeaderBtn = panel.querySelector(".srucw-close");
  if (closeHeaderBtn) {
    closeHeaderBtn.onclick = function (e) {
      e.stopPropagation();
      if (panel.classList.contains("open")) {
        bubble.click();
      }
    };
  }

  function loadProfile() {
    try { return JSON.parse(localStorage.getItem(PF_KEY) || "{}") || {}; }
    catch (e) { return {}; }
  }

  function profileSummary(p) {
    if (!p) return "";
    if (p.roll_number) {
      return (p.degree || "B.Tech") + " " + (p.stream || p.branch || "") + " (" + (p.regulation || p.batch || "") + ")";
    }
    return [
      p.batch || "",
      p.programme || "",
      p.branch || "",
      p.year ? "Year " + p.year : "",
      p.semester ? "Sem " + p.semester : "",
    ].filter(Boolean).join(" · ");
  }

  var profile = loadProfile();

  function updateSubtitle() {
    var sub = panel.querySelector(".srucw-sub");
    if (!sub) return;
    if (profile && profile.roll_number) {
      sub.innerHTML = '<span class="srucw-badge" title="Click to change roll number">' +
        '🎓 ' + esc(profile.roll_number) + ' · ' + esc(profile.stream || profile.degree || "Student") +
        '<span class="srucw-badge-x" title="Reset roll number">✕</span></span>';
      var badgeX = sub.querySelector(".srucw-badge-x");
      if (badgeX) {
        badgeX.onclick = function (e) {
          e.stopPropagation();
          profile = {};
          try { localStorage.removeItem(PF_KEY); } catch (err) {}
          updateSubtitle();
          addMsg("bot", "Profile reset. You can enter another roll number anytime!");
        };
      }
    } else {
      sub.textContent = profileSummary(profile) || "Autonomous University RAG Agent";
    }
  }

  function saveProfile() {
    try { localStorage.setItem(PF_KEY, JSON.stringify(profile)); } catch (e) {}
    updateSubtitle();
  }

  // The bot asks clarifying questions in the chat (batch, hostel, programme,
  // branch, year, semester). Whatever the student picks from a chip or types
  // plainly is remembered, so the bot never asks for the same detail twice.
  function captureProfile(text) {
    var t = (text || "").trim(), match;
    if (!t) return;
    var changed = false;
    function add(k, v) {
      if (v && profile[k] !== v) { profile[k] = v; changed = true; }
    }

    match = t.match(/\b(2023[-–/]?24|23[-–/]?24|2023|2024|r23)\b/i);
    if (match) add("batch", "2023-24 (R23)");
    match = t.match(/\b(2026[-–/]?27|26[-–/]?27|2026|2027|r26)\b/i);
    if (match) add("batch", "2026-27");

    if (/hostel/i.test(t)) {
      if (/\b(?:boys?)\b|bh-?\d/i.test(t)) add("hostel", "Boys");
      else if (/\b(?:girls?)\b|gh-?\d/i.test(t)) add("hostel", "Girls");
    }

    var PROGS = [
      [/\bm\.?\s?tech\b/i, "M.Tech"],
      [/\bb\.?\s?tech\b/i, "B.Tech"],
      [/\bb\.?\s?sc\.?\b/i, "B.Sc."],
      [/\bbba\b/i, "BBA"],
      [/\bbca\b/i, "BCA"],
      [/\bdiploma\b/i, "Diploma"],
    ];
    for (var i = 0; i < PROGS.length; i++) {
      if (PROGS[i][0].test(t)) { add("programme", PROGS[i][1]); break; }
    }

    match = t.match(/\b(cse|ece|eee|aiml|ai[ &]*ml|data ?science|mech(?:anical)?|civil)\b/i);
    if (match) add("branch", match[1].toUpperCase().replace(/\s*&\s*/g, "&"));

    match = t.match(/\b(?:sem|semester)[\s\-:]*(1|2|3|4|5|6|7|8)\b/i);
    if (match) add("semester", match[1]);

    match = t.match(/\b(?:year|yr)[\s\-:]*(1|2|3|4|5)\b/i) ||
           t.match(/\b(1st|2nd|3rd|4th|5th|first|second|third|fourth|fifth)\s+(?:year|yr)\b/i);
    if (match) {
      var WORD = { first: "1", second: "2", third: "3", fourth: "4", fifth: "5" };
      var ord = (match[0].split(/\s+/)[0] || "").toLowerCase();
      var val = (match[1] || "").replace(/\D/g, "") || WORD[ord] ||
                (ord.match(/\d/) ? ord.match(/\d/)[0] : "") || "";
      add("year", val);
    }

    if (changed) saveProfile();
  }

  updateSubtitle();

  function showToast(msg) {
    var toast = el("div", "srucw-toast", msg);
    panel.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = "0";
      setTimeout(function () { toast.remove(); }, 300);
    }, 2000);
  }

  function openMailModal(draft) {
    if (!draft) return;
    var backdrop = el("div", "srucw-modal-backdrop");
    var modal = el("div", "srucw-modal");

    modal.innerHTML =
      '<div class="srucw-modal-head">' +
        '<div class="srucw-modal-title">✉️ Official Email Draft</div>' +
        '<button class="srucw-modal-close" title="Close (Esc)">✕</button>' +
      '</div>' +
      '<div class="srucw-modal-body">' +
        '<div class="srucw-field"><label>To:</label><input type="text" class="srucw-field-to" readonly value="' + esc(draft.recipient || "") + '"></div>' +
        (draft.cc ? '<div class="srucw-field"><label>CC:</label><input type="text" class="srucw-field-cc" readonly value="' + esc(draft.cc || "") + '"></div>' : '') +
        '<div class="srucw-field"><label>Subject:</label><input type="text" class="srucw-field-subject" value="' + esc(draft.subject || "") + '"></div>' +
        '<div class="srucw-field"><label>Body (editable):</label><textarea class="srucw-field-body">' + esc(draft.body || "") + '</textarea></div>' +
      '</div>' +
      '<div class="srucw-modal-footer">' +
        '<button class="srucw-btn-sec srucw-modal-copy-btn">📋 Copy Draft</button>' +
        '<a class="srucw-btn-pri srucw-modal-send-btn" href="' + esc(draft.mailto_url || "#") + '" target="_blank">🚀 Open in Mail</a>' +
      '</div>';

    backdrop.appendChild(modal);
    panel.appendChild(backdrop);

    var subjInput = modal.querySelector(".srucw-field-subject");
    var bodyInput = modal.querySelector(".srucw-field-body");
    var sendBtn = modal.querySelector(".srucw-modal-send-btn");
    var copyBtn = modal.querySelector(".srucw-modal-copy-btn");
    var closeBtn = modal.querySelector(".srucw-modal-close");

    function updateMailto() {
      var s = encodeURIComponent(subjInput.value);
      var b = encodeURIComponent(bodyInput.value);
      var url = "mailto:" + encodeURIComponent(draft.recipient || "");
      var params = ["subject=" + s, "body=" + b];
      if (draft.cc) params.push("cc=" + encodeURIComponent(draft.cc));
      sendBtn.href = url + "?" + params.join("&");
    }

    subjInput.oninput = updateMailto;
    bodyInput.oninput = updateMailto;

    function closeModal() {
      document.removeEventListener("keydown", onEsc);
      backdrop.remove();
    }

    function onEsc(e) {
      if (e.key === "Escape" || e.keyCode === 27) closeModal();
    }

    closeBtn.onclick = closeModal;
    backdrop.onclick = function (e) {
      if (e.target === backdrop) closeModal();
    };
    document.addEventListener("keydown", onEsc);

    copyBtn.onclick = function () {
      var fullText = "Subject: " + subjInput.value + "\n\n" + bodyInput.value;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(fullText).then(function () {
          showToast("Application letter copied!");
        });
      } else {
        bodyInput.select();
        document.execCommand("copy");
        showToast("Application letter copied!");
      }
    };
  }

  function renderCtaBar(container, cta) {
    if (!cta || typeof cta !== "object") return;
    var ctaBox = el("div", "srucw-cta-container");
    var header = el("div", "srucw-cta-header", "⚡ Quick Actions:");
    ctaBox.appendChild(header);

    var bar = el("div", "srucw-cta-bar");

    if (cta.phone) {
      var callA = el("a", "srucw-cta-btn srucw-cta-call", "📞 Call (" + cta.phone + ")");
      callA.href = "tel:" + cta.phone;
      callA.title = "Call official contact number";
      bar.appendChild(callA);
    }

    if (cta.mail_draft) {
      var mailBtn = el("button", "srucw-cta-btn srucw-cta-mail", "✉️ Draft Email");
      mailBtn.title = "Review & send pre-filled formal email";
      mailBtn.onclick = function (e) {
        e.stopPropagation();
        openMailModal(cta.mail_draft);
      };
      bar.appendChild(mailBtn);

      var copyBtn = el("button", "srucw-cta-btn srucw-cta-copy", "📋 Copy Text");
      copyBtn.title = "Copy formal letter to clipboard";
      copyBtn.onclick = function (e) {
        e.stopPropagation();
        var textToCopy = "Subject: " + (cta.mail_draft.subject || "") + "\n\n" + (cta.mail_draft.body || "");
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(textToCopy).then(function () {
            showToast("Formal draft copied to clipboard!");
          });
        } else {
          openMailModal(cta.mail_draft);
        }
      };
      bar.appendChild(copyBtn);
    }

    if (bar.children.length > 0) {
      ctaBox.appendChild(bar);
      container.appendChild(ctaBox);
    }
  }

  function addMsg(role, text, cites, cta) {
    var row = el("div", "srucw-row " + role);
    var b = el("div", "srucw-msg " + role);
    if (role === "bot") { b.innerHTML = renderMarkdown(text); }
    else { b.textContent = text; }
    row.appendChild(b);
    if (cites && cites.length) {
      b.appendChild(el("br"));
      b.appendChild(el("span", "srucw-cite", "📖 " + cites.join(" · ")));
    }
    if (role === "bot" && cta) {
      renderCtaBar(b, cta);
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

  var currentAbort = null;

  function stopCurrentTask() {
    if (currentAbort) {
      try { currentAbort.abort(); } catch (e) {}
      currentAbort = null;
    }
    typing(false);
    busy = false;
    sendBtn.textContent = "Send";
    sendBtn.classList.remove("srucw-stop");
    sendBtn.disabled = false;
    addMsg("bot", "⏹️ Response stopped.");
    input.focus();
  }

  function ask(text) {
    if (busy) {
      stopCurrentTask();
      return;
    }
    text = (text || input.value).trim();
    if (!text) return;
    captureProfile(text);
    input.value = "";
    busy = true;
    sendBtn.textContent = "Stop";
    sendBtn.classList.add("srucw-stop");
    sendBtn.disabled = false;
    addMsg("user", text);
    typing(true);

    currentAbort = typeof AbortController !== "undefined" ? new AbortController() : null;

    fetch(API + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: history.slice(-8), profile: profile, session_id: getSessionId(), htno: profile.roll_number || null }),
      signal: currentAbort ? currentAbort.signal : undefined,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        currentAbort = null;
        typing(false);
        var ans = data.answer || data.error || "Something went wrong.";
        addMsg("bot", ans, data.citations, data.cta);
        history.push({ role: "user", content: text });
        history.push({ role: "assistant", content: ans, citations: data.citations, cta: data.cta });
        saveSessionMsgs();
        if (data.session_id) localStorage.setItem(SESS_ID_KEY, data.session_id);
        if (data.htno && !profile.roll_number) {
          profile.roll_number = data.htno;
        }
        if (data.profile && typeof data.profile === "object") {
          for (var k in data.profile) { profile[k] = data.profile[k]; }
          saveProfile();
        }
        if (data.suggestions && data.suggestions.length) {
          setChips(data.suggestions);
        } else if (data.options && data.options.length) {
          setChips(data.options, 8);
        } else {
          maybeClarifyChips(ans);
        }
        refreshSuggestions();
      })
      .catch(function (err) {
        if (err && (err.name === "AbortError" || err.message === "The user aborted a request.")) {
          return; // Already stopped by stopCurrentTask()
        }
        typing(false);
        addMsg("bot", "⚠️ Could not reach the server. Is the API running?");
      })
      .then(function () {
        if (busy) {
          currentAbort = null;
          busy = false;
          sendBtn.textContent = "Send";
          sendBtn.classList.remove("srucw-stop");
          sendBtn.disabled = false;
          input.focus();
        }
      });
  }

  sendBtn.onclick = function () { ask(); };
  input.addEventListener("keydown", function (e) {
    var isEnter = e.key === "Enter" || e.keyCode === 13 || e.which === 13;
    if (isEnter && !e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      if (!busy) ask();
    }
  });

  // ---------- suggestion chips (capped: 3 for recency-bandit, 8 for clarifications) ----------
  var SUGGESTION_LIMIT = 3;
  function setChips(list, max) {
    suggBox.innerHTML = "";
    list.filter(Boolean).slice(0, max || SUGGESTION_LIMIT).forEach(function (s) {
      var b = el("button", null, s);
      b.onclick = function () { ask(s); };
      suggBox.appendChild(b);
    });
  }

  function refreshSuggestions() {
    fetch(API + "/api/suggestions")
      .then(function (r) { return r.json(); })
      .then(function (d) { if (d.suggestions && d.suggestions.length) setChips(d.suggestions); })
      .catch(function () {});
  }

  // When the bot asks a clarifying question or offers a follow-up, offer one-tap chips.
  function maybeClarifyChips(ans) {
    if (!ans) return;
    var trimmed = ans.trim();
    var endsWithQ = /\?["']?\s*$/.test(trimmed);
    var opts = null;

    if (/would you like (?:me to )?(?:detail|explain|more details|elaborate)|want me to (?:brief|elaborate)|need more details/i.test(trimmed)) {
      opts = ["Yes, explain in detail", "What are the exact penalties?", "Tell me the appeal process"];
    } else if (endsWithQ && trimmed.length <= 320) {
      if (/batch|regulation|r23|2023|2026/i.test(trimmed)) {
        opts = ["2023–24 Batch (R23)", "2026–27 Batch", "Explain both"];
      } else if (/boys? hostel|girls? hostel|which hostel|boys or girls|hostel .* boys?/i.test(trimmed)) {
        opts = ["Boys Hostel", "Girls Hostel"];
      } else if (/sem(?:ester)?\b/i.test(trimmed)) {
        opts = ["Semester 1", "Semester 2", "Semester 3", "Semester 4",
                "Semester 5", "Semester 6", "Semester 7", "Semester 8"];
      } else if (/programme|program\b|b\.?tech|bba|bca|b\.?sc|diploma/i.test(trimmed)) {
        opts = ["B.Tech", "BBA", "BCA", "B.Sc.", "M.Tech", "Diploma"];
      } else if (/branch|speciali[sz]ation|stream|course offered/i.test(trimmed)) {
        opts = ["CSE", "ECE", "EEE", "Mechanical", "Civil"];
      } else if (/\byear\b|\byr\b/i.test(trimmed)) {
        opts = ["Year 1", "Year 2", "Year 3", "Year 4"];
      }
    }
    if (opts) setChips(opts, 8);
  }

  bubble.onclick = function () {
    var open = panel.classList.toggle("open");
    bubble.textContent = open ? "×" : "💬";
    if (open) {
      if (!msgsBox.children.length) {
        if (!loadSessionMsgs()) {
          addMsg("bot", WELCOME);
          history.push({ role: "assistant", content: WELCOME });
          saveSessionMsgs();
        }
      }
      refreshSuggestions();
      input.focus();
    }
  };

  // Close when clicking anywhere outside the chat panel on the portal
  document.addEventListener("click", function (e) {
    if (panel.classList.contains("open") && !root.contains(e.target)) {
      bubble.click();
    }
  });

  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", function () {
      if (panel.classList.contains("open") && window.innerWidth <= 640) {
        panel.style.height = Math.min(window.visualViewport.height - 16, 680) + "px";
        msgsBox.scrollTop = msgsBox.scrollHeight;
      }
    });
  }

  // Eager background warmup ping: wakes up sleeping Render containers the moment
  // the student loads the university portal, before they even click the chat bubble!
  try {
    fetch(API + "/api/health", { method: "GET", cache: "no-store" }).catch(function () {});
  } catch (e) {}

  // Global demo hook for portal page buttons
  window.SRU_CHAT_API = {
    setStudentRoll: function (roll) {
      if (!panel.classList.contains("open")) {
        panel.classList.add("open");
        bubble.textContent = "×";
      }
      fetchAndRestoreHistory(roll, function (data) {
        if (!data || !data.messages || data.messages.length === 0) {
          ask("My roll number is " + roll);
        }
      });
    },
    askQuestion: function (q) {
      if (!panel.classList.contains("open")) {
        panel.classList.add("open");
        bubble.textContent = "×";
      }
      ask(q);
    },
    open: function () {
      if (!panel.classList.contains("open")) {
        panel.classList.add("open");
        bubble.textContent = "×";
        input.focus();
      }
    },
    close: function () {
      if (panel.classList.contains("open")) {
        panel.classList.remove("open");
        bubble.textContent = "💬";
      }
    },
    resetProfile: function () {
      profile = {};
      try { localStorage.removeItem(PF_KEY); } catch (e) {}
      updateSubtitle();
      if (clearBtn) clearBtn.click();
    }
  };
})();
