// Shared helpers for every page.

// Talk to the JSON API. Throws an Error with a friendly message on failure.
async function api(url, method = "GET", body) {
  const options = { method, headers: {} };
  if (method !== "GET") {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body || {});
  }
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

// Build an element safely (text is never treated as HTML).
function h(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined && text !== null) el.textContent = text;
  return el;
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
}
function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
}
function fmtDateTime(iso) {
  return fmtDate(iso) + ", " + fmtTime(iso);
}
function money(n) {
  return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

// The location the visitor picked, remembered in this browser.
function getCity() {
  try { return localStorage.getItem("moviebook_location") || ""; } catch (e) { return ""; }
}
function setCity(city) {
  try { localStorage.setItem("moviebook_location", city || ""); } catch (e) { /* ignore */ }
}

// Fill a <select> with the cities that have theaters, and pick the remembered one.
async function fillCitySelect(select, allLabel) {
  select.innerHTML = "";
  select.appendChild(new Option(allLabel || "All locations", ""));
  try {
    const data = await api("/api/cities");
    data.cities.forEach(c => select.appendChild(new Option(c, c)));
  } catch (e) { /* leave only the default option */ }
  select.value = getCity();
  if (select.value !== getCity()) select.value = "";
}

function posterPlaceholder(movie) {
  return h("div", "poster poster-ph", (movie.title || "?").charAt(0).toUpperCase());
}
function posterElement(movie) {
  if (movie.poster_url) {
    const img = document.createElement("img");
    img.className = "poster";
    img.src = movie.poster_url;
    img.alt = movie.title;
    img.loading = "lazy";
    img.addEventListener("error", () => img.replaceWith(posterPlaceholder(movie)));
    return img;
  }
  return posterPlaceholder(movie);
}

// Only allow redirects to pages on this site.
function safeNext(fallback) {
  const next = new URLSearchParams(window.location.search).get("next") || "";
  return next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}

document.addEventListener("DOMContentLoaded", () => {
  const logout = document.getElementById("logout-btn");
  if (logout) {
    logout.addEventListener("click", async () => {
      try { await api("/api/auth/logout", "POST"); } catch (e) { /* ignore */ }
      window.location.href = "/";
    });
  }
});
