// Admin portal: one page, four tabs. Everything is loaded from and saved to /api/admin/...
const state = { tab: "movies", movies: [], theaters: [], showtimes: [], bookings: [], editing: null };

const badge = (on, yes, no) => `<span class="badge ${on ? "on" : "off"}">${on ? yes : no}</span>`;

// What each tab shows (columns) and which form fields it has (fields)
const CONFIG = {
  movies: {
    title: "Movies", api: "/api/admin/movies", canEdit: true,
    columns: [
      { h: "Title", r: (m) => `<strong>${esc(m.title)}</strong><br><small>${esc(m.genre)}${m.genre && m.language ? " · " : ""}${esc(m.language)}</small>` },
      { h: "Duration", r: (m) => esc(m.duration_min) + " min" },
      { h: "Rating", r: (m) => esc(m.rating) },
      { h: "Status", r: (m) => badge(m.is_active, "On website", "Hidden") },
    ],
    fields: [
      { n: "title", l: "Title", t: "text", req: true },
      { n: "description", l: "Description", t: "textarea" },
      { n: "genre", l: "Genre", t: "text" },
      { n: "language", l: "Language", t: "text" },
      { n: "duration_min", l: "Duration (minutes)", t: "number", req: true, min: 1, max: 600 },
      { n: "rating", l: "Rating (0–10)", t: "number", step: "0.1", min: 0, max: 10, def: 7 },
      { n: "poster_url", l: "Poster image link (optional, https://…)", t: "url" },
      { n: "is_active", l: "Show on website", t: "checkbox", def: true },
    ],
  },
  theaters: {
    title: "Theaters", api: "/api/admin/theaters", canEdit: true,
    columns: [
      { h: "Theater", r: (t) => `<strong>${esc(t.name)}</strong><br><small>${esc(t.location)}</small>` },
      { h: "Seat layout", r: (t) => `${esc(t.rows)} rows × ${esc(t.seats_per_row)} seats` },
      { h: "Capacity", r: (t) => esc(t.capacity) },
    ],
    fields: [
      { n: "name", l: "Theater name", t: "text", req: true },
      { n: "location", l: "Location", t: "text", req: true },
      { n: "rows", l: "Rows (A, B, C…) max 20", t: "number", req: true, min: 1, max: 20, def: 8 },
      { n: "seats_per_row", l: "Seats per row (max 20)", t: "number", req: true, min: 1, max: 20, def: 10 },
    ],
  },
  showtimes: {
    title: "Showtimes & ticket prices", api: "/api/admin/showtimes", canEdit: true,
    columns: [
      { h: "Movie", r: (s) => `<strong>${esc(s.movie_title)}</strong>` },
      { h: "Theater", r: (s) => esc(s.theater_name) },
      { h: "Date & time", r: (s) => esc(fmtDateTime(s.start_time)) },
      { h: "Ticket price", r: (s) => esc(money(s.price)) },
    ],
    fields: [
      { n: "movie_id", l: "Movie", t: "select", req: true, options: () => state.movies.map((m) => ({ v: m.id, t: m.title })) },
      { n: "theater_id", l: "Theater", t: "select", req: true, options: () => state.theaters.map((t) => ({ v: t.id, t: `${t.name} (${t.location})` })) },
      { n: "start_time", l: "Date & time", t: "datetime-local", req: true },
      { n: "price", l: "Ticket price (₹)", t: "number", req: true, min: 1, step: "0.01", def: 250 },
    ],
  },
  bookings: {
    title: "All bookings", api: "/api/admin/bookings", canEdit: false,
    columns: [
      { h: "Reference", r: (b) => `<strong>${esc(b.reference)}</strong>` },
      { h: "Customer", r: (b) => `${esc(b.user_name)}<br><small>${esc(b.user_email)}</small>` },
      { h: "Movie", r: (b) => `${esc(b.movie.title)}<br><small>${esc(b.theater.name)} · ${esc(fmtDateTime(b.showtime.start_time))}</small>` },
      { h: "Seats", r: (b) => esc(b.seats.join(", ")) },
      { h: "Total", r: (b) => esc(money(b.total)) },
      { h: "Status", r: (b) => badge(b.status === "Confirmed", "Confirmed", "Cancelled") },
    ],
    fields: [],
  },
};

const $ = (id) => document.getElementById(id);

// ---------- load data ----------
async function refreshAll() {
  try {
    const [m, t, s, b, st] = await Promise.all([
      api("/api/admin/movies"), api("/api/admin/theaters"), api("/api/admin/showtimes"),
      api("/api/admin/bookings"), api("/api/admin/stats"),
    ]);
    state.movies = m.movies; state.theaters = t.theaters; state.showtimes = s.showtimes; state.bookings = b.bookings;
    $("stats").innerHTML = [
      ["Movies", st.movies], ["Theaters", st.theaters], ["Showtimes", st.showtimes],
      ["Bookings", st.bookings], ["Revenue", money(st.revenue)],
    ].map(([label, value]) => `<div class="stat"><b>${esc(value)}</b><span>${label}</span></div>`).join("");
    renderTable();
  } catch (err) {
    $("tableWrap").innerHTML = `<p class="empty">${esc(err.message)}</p>`;
  }
}

// ---------- table ----------
function renderTable() {
  const cfg = CONFIG[state.tab];
  const rows = state[state.tab];
  $("tabTitle").textContent = cfg.title;
  $("addBtn").hidden = !cfg.canEdit;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === state.tab));

  if (!rows.length) {
    $("tableWrap").innerHTML = `<div class="empty">Nothing here yet.${cfg.canEdit ? " Click <b>+ Add</b> to create the first one." : ""}</div>`;
    return;
  }
  const head = cfg.columns.map((c) => `<th>${c.h}</th>`).join("") + (cfg.canEdit ? "<th>Actions</th>" : "");
  const body = rows.map((row) => `<tr>
      ${cfg.columns.map((c) => `<td>${c.r(row)}</td>`).join("")}
      ${cfg.canEdit ? `<td class="actions">
        <button type="button" class="btn-outline" data-edit="${row.id}">Edit</button>
        <button type="button" class="btn-outline danger" data-delete="${row.id}">Delete</button></td>` : ""}
    </tr>`).join("");
  $("tableWrap").innerHTML = `<table class="admin-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

$("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-tab]");
  if (!btn) return;
  state.tab = btn.dataset.tab;
  renderTable();
});

$("tableWrap").addEventListener("click", async (e) => {
  const cfg = CONFIG[state.tab];
  const editBtn = e.target.closest("[data-edit]");
  const delBtn = e.target.closest("[data-delete]");
  if (editBtn) {
    openForm(state[state.tab].find((r) => r.id == editBtn.dataset.edit));
  } else if (delBtn) {
    if (!confirm("Delete this item? This cannot be undone.")) return;
    try {
      await api(`${cfg.api}/${delBtn.dataset.delete}`, "DELETE");
      toast("Deleted.", "success");
      refreshAll();
    } catch (err) {
      toast(err.message, "error");
    }
  }
});

// ---------- add / edit form ----------
function fieldHTML(f, row) {
  let value = row ? row[f.n] : f.def;
  value = value ?? "";
  const common = `id="f_${f.n}" name="${f.n}" ${f.req ? "required" : ""}`;
  if (f.t === "checkbox") {
    return `<label class="check"><input type="checkbox" ${common.replace("required", "")} ${value ? "checked" : ""}> ${esc(f.l)}</label>`;
  }
  let input;
  if (f.t === "textarea") {
    input = `<textarea ${common} rows="3">${esc(value)}</textarea>`;
  } else if (f.t === "select") {
    const opts = f.options().map((o) => `<option value="${o.v}" ${o.v == value ? "selected" : ""}>${esc(o.t)}</option>`).join("");
    input = `<select ${common}><option value="">Choose…</option>${opts}</select>`;
  } else {
    const attrs = ["min", "max", "step"].filter((a) => f[a] !== undefined).map((a) => `${a}="${f[a]}"`).join(" ");
    input = `<input type="${f.t}" ${common} ${attrs} value="${esc(value)}">`;
  }
  return `<div class="form-group"><label for="f_${f.n}">${esc(f.l)}</label>${input}</div>`;
}

function openForm(row = null) {
  const cfg = CONFIG[state.tab];
  state.editing = row;
  $("modalTitle").textContent = (row ? "Edit" : "Add") + " – " + cfg.title;
  $("modalFields").innerHTML = cfg.fields.map((f) => fieldHTML(f, row)).join("");
  $("modalError").textContent = "";
  $("modal").showModal();
}

$("addBtn").addEventListener("click", () => openForm());
$("cancelBtn").addEventListener("click", () => $("modal").close());

$("modalForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const cfg = CONFIG[state.tab];
  const body = {};
  cfg.fields.forEach((f) => {
    const el = $("f_" + f.n);
    body[f.n] = f.t === "checkbox" ? el.checked : el.value;
  });
  try {
    if (state.editing) await api(`${cfg.api}/${state.editing.id}`, "PUT", body);
    else await api(cfg.api, "POST", body);
    $("modal").close();
    toast("Saved.", "success");
    refreshAll();
  } catch (err) {
    $("modalError").textContent = err.message;
  }
});

refreshAll();
