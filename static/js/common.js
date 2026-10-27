// ---------- Talk to the Flask API ----------
async function api(url, method = "GET", body = null) {
  const options = { method, headers: { "Content-Type": "application/json" }, credentials: "same-origin" };
  if (method !== "GET") options.body = JSON.stringify(body || {});
  const res = await fetch(url, options);
  let data = {};
  try { data = await res.json(); } catch (e) { /* no JSON body */ }
  if (!res.ok) {
    const err = new Error(data.error || "Something went wrong. Please try again.");
    err.status = res.status;
    throw err;
  }
  return data;
}

// ---------- Helpers ----------
function esc(value) {  // makes text safe to put inside HTML
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function money(n) { return "₹" + Number(n).toFixed(2).replace(/\.00$/, ""); }
function fmtDateTime(iso) {
  return new Date(iso).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}
function fmtDay(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}
function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
}
function toast(message, type = "info") {
  const box = document.getElementById("toastContainer");
  const el = document.createElement("div");
  el.className = "toast " + type;
  el.textContent = message;
  box.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}
function posterHTML(movie) {
  if (movie.poster_url) {
    return `<img class="poster-img" src="${esc(movie.poster_url)}" alt="${esc(movie.title)} poster" loading="lazy">`;
  }
  let hue = 0;
  for (const ch of movie.title) hue = (hue * 31 + ch.charCodeAt(0)) % 360;
  return `<div class="poster-fallback" style="--h:${hue}"><span>🎬</span><b>${esc(movie.title)}</b></div>`;
}

// ---------- Navbar ----------
const menuToggle = document.getElementById("menuToggle");
const navLinks = document.getElementById("navLinks");
menuToggle.addEventListener("click", () => {
  const open = navLinks.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", open);
});
const logoutBtn = document.getElementById("logoutBtn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    try { await api("/api/auth/logout", "POST"); } finally { window.location.href = "/"; }
  });
}
