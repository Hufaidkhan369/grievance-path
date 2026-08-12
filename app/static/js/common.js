/* Shared helpers for GrievancePath pages */
const API = "";

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = localStorage.getItem("gp_token");
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch(API + path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || "Request failed (" + res.status + ")");
  return data;
}

function esc(s) {
  if (s == null) return "";
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function fmtDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function statusPill(s) {
  const key = String(s || "").toLowerCase().replace(/_/g, "-");
  return `<span class="pill ${key}">${esc(s)}</span>`;
}

function priorityPill(p) {
  return `<span class="pill ${String(p || "").toLowerCase()}">${esc(p)}</span>`;
}

function loggedIn() { return !!localStorage.getItem("gp_token"); }
function logout() {
  localStorage.removeItem("gp_token");
  localStorage.removeItem("gp_role");
  localStorage.removeItem("gp_dept");
  location.href = "/";
}

function showMsg(el, text, kind = "ok") {
  if (!el) return;
  el.className = "msg show " + kind;
  el.textContent = text;
}

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
