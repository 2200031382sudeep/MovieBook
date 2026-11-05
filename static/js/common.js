// ==========================================================================
// BookMyShow Shared Utilities, Profile Slide-Down & City Selector
// ==========================================================================

// JSON API Client
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

// Safe DOM element builder
function h(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined && text !== null) el.textContent = text;
  return el;
}

// Date & Currency Formatters
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

// City Preference Management
function getCity() {
  try { return localStorage.getItem("bms_location") || localStorage.getItem("moviebook_location") || ""; } catch (e) { return ""; }
}

function setCity(city) {
  try {
    localStorage.setItem("bms_location", city || "");
    localStorage.setItem("moviebook_location", city || "");
    window.dispatchEvent(new CustomEvent("bms:city-changed", { detail: { city: city || "" } }));
  } catch (e) { /* ignore */ }
  updateCityLabels(city);
}

function updateCityLabels(city) {
  const label = city || "Select Location";
  const headerCity = document.getElementById("selected-city-label");
  if (headerCity) headerCity.textContent = label;
  const drawerCity = document.getElementById("drawer-city-name");
  if (drawerCity) drawerCity.textContent = city || "All Locations";
}

// Poster Rendering with BookMyShow Cinematic Card Fallback
function posterPlaceholder(movie) {
  const wrap = h("div", "bms-poster-placeholder");
  const clapper = h("div", "placeholder-clapper", "🎬");
  const title = h("div", "placeholder-title", movie.title || "Cinema");
  const genre = h("div", "placeholder-genre", [movie.language, movie.genre].filter(Boolean).join(" • ") || "In Cinemas");
  wrap.appendChild(clapper);
  wrap.appendChild(title);
  wrap.appendChild(genre);
  return wrap;
}

function posterElement(movie) {
  if (movie.poster_url && movie.poster_url.trim()) {
    const img = document.createElement("img");
    img.className = "bms-movie-poster";
    img.src = movie.poster_url.trim();
    img.alt = movie.title || "Movie";
    img.loading = "lazy";
    img.addEventListener("error", () => {
      img.replaceWith(posterPlaceholder(movie));
    });
    return img;
  }
  return posterPlaceholder(movie);
}

// Only allow redirects to internal pages
function safeNext(fallback) {
  const next = new URLSearchParams(window.location.search).get("next") || "";
  return next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}

// ==========================================================================
// PROFILE SLIDE-DOWN DRAWER CONTROLLER
// ==========================================================================
function initProfileDrawer() {
  const trigger = document.getElementById("bms-profile-btn");
  const drawer = document.getElementById("bms-profile-dropdown");
  const backdrop = document.getElementById("bms-profile-backdrop");
  const closeBtn = document.getElementById("bms-profile-close");
  const logoutBtn = document.getElementById("drawer-logout-btn");

  if (!drawer) return;

  function openDrawer() {
    drawer.classList.add("open");
    if (backdrop) backdrop.classList.add("open");
    if (trigger) trigger.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    drawer.classList.remove("open");
    if (backdrop) backdrop.classList.remove("open");
    if (trigger) trigger.classList.remove("active");
    document.body.style.overflow = "";
  }

  if (trigger) {
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      if (drawer.classList.contains("open")) {
        closeDrawer();
      } else {
        openDrawer();
      }
    });
  }

  if (closeBtn) closeBtn.addEventListener("click", closeDrawer);
  if (backdrop) backdrop.addEventListener("click", closeDrawer);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && drawer.classList.contains("open")) {
      closeDrawer();
    }
  });

  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await api("/api/auth/logout", "POST");
      } catch (e) { /* ignore */ }
      window.location.href = "/";
    });
  }
}

// ==========================================================================
// CITY SELECTION MODAL CONTROLLER
// ==========================================================================
const POPULAR_CITIES = [
  { name: "Hyderabad", icon: "🕌" },
  { name: "Bengaluru", icon: "🏛️" },
  { name: "Mumbai", icon: "🌊" },
  { name: "Delhi-NCR", icon: "🏰" },
  { name: "Chennai", icon: "🏖️" },
  { name: "Kolkata", icon: "🌉" },
  { name: "Pune", icon: "⛰️" },
  { name: "Ahmedabad", icon: "🪁" },
  { name: "Chandigarh", icon: "🌳" },
  { name: "Kochi", icon: "⛵" },
];

let availableCities = [];

async function loadCitiesList() {
  try {
    const data = await api("/api/cities");
    availableCities = data.cities || [];
  } catch (e) {
    availableCities = [];
  }
}

function openCityModal() {
  const modal = document.getElementById("bms-city-modal");
  if (modal) {
    modal.classList.add("open");
    document.body.style.overflow = "hidden";
    renderCityModalContent();
    const searchInput = document.getElementById("city-modal-input");
    if (searchInput) {
      searchInput.value = "";
      setTimeout(() => searchInput.focus(), 100);
    }
  }
}

function closeCityModal() {
  const modal = document.getElementById("bms-city-modal");
  if (modal) {
    modal.classList.remove("open");
    document.body.style.overflow = "";
  }
}

function renderCityModalContent(filterText = "") {
  const currentCity = getCity();
  const popularContainer = document.getElementById("popular-cities-grid");
  const allContainer = document.getElementById("all-cities-list");
  const query = filterText.trim().toLowerCase();

  if (popularContainer) {
    popularContainer.innerHTML = "";
    const filteredPopular = POPULAR_CITIES.filter(c => c.name.toLowerCase().includes(query));
    filteredPopular.forEach(c => {
      const card = h("div", "popular-city-card" + (c.name.toLowerCase() === currentCity.toLowerCase() ? " selected" : ""));
      card.appendChild(h("div", "city-icon", c.icon));
      card.appendChild(h("div", "city-name-label", c.name));
      card.addEventListener("click", () => {
        setCity(c.name);
        closeCityModal();
      });
      popularContainer.appendChild(card);
    });
  }

  if (allContainer) {
    allContainer.innerHTML = "";
    const combined = Array.from(new Set([...availableCities, ...POPULAR_CITIES.map(c => c.name)])).sort();
    const filteredAll = combined.filter(c => c.toLowerCase().includes(query));

    const allChip = h("button", "city-chip" + (!currentCity ? " selected" : ""), "All Locations");
    allChip.type = "button";
    allChip.addEventListener("click", () => {
      setCity("");
      closeCityModal();
    });
    allContainer.appendChild(allChip);

    filteredAll.forEach(city => {
      const chip = h("button", "city-chip" + (city.toLowerCase() === currentCity.toLowerCase() ? " selected" : ""), city);
      chip.type = "button";
      chip.addEventListener("click", () => {
        setCity(city);
        closeCityModal();
      });
      allContainer.appendChild(chip);
    });
  }
}

function initCityModal() {
  const cityBtn = document.getElementById("bms-city-btn");
  const drawerChangeCity = document.getElementById("drawer-change-city");
  const modalBackdrop = document.getElementById("bms-city-modal");
  const closeBtn = document.getElementById("city-modal-close");
  const searchInput = document.getElementById("city-modal-input");

  if (cityBtn) cityBtn.addEventListener("click", openCityModal);
  if (drawerChangeCity) {
    drawerChangeCity.addEventListener("click", () => {
      const drawer = document.getElementById("bms-profile-dropdown");
      const backdrop = document.getElementById("bms-profile-backdrop");
      if (drawer) drawer.classList.remove("open");
      if (backdrop) backdrop.classList.remove("open");
      document.body.style.overflow = "";
      openCityModal();
    });
  }

  if (closeBtn) closeBtn.addEventListener("click", closeCityModal);
  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", (e) => {
      if (e.target === modalBackdrop) closeCityModal();
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      renderCityModalContent(e.target.value);
    });
  }

  loadCitiesList().then(() => {
    updateCityLabels(getCity());
  });
}

// Global search handling in header
function initGlobalSearch() {
  const globalInput = document.getElementById("global-search-input");
  if (!globalInput) return;

  globalInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const val = globalInput.value.trim();
      if (window.location.pathname === "/") {
        const pageSearch = document.getElementById("q");
        if (pageSearch) {
          pageSearch.value = val;
          pageSearch.dispatchEvent(new Event("input"));
        }
      } else {
        window.location.href = "/?q=" + encodeURIComponent(val);
      }
    }
  });
}

function highlightNav() {
  const path = window.location.pathname;
  const m = document.getElementById("nav-movies");
  const t = document.getElementById("nav-theaters");
  const b = document.getElementById("nav-bookings");

  if (path === "/" && m) m.classList.add("active");
  else if (path.startsWith("/theaters") && t) t.classList.add("active");
  else if (path.startsWith("/my-bookings") && b) b.classList.add("active");
}

document.addEventListener("DOMContentLoaded", () => {
  initProfileDrawer();
  initCityModal();
  initGlobalSearch();
  highlightNav();
  updateCityLabels(getCity());
});
