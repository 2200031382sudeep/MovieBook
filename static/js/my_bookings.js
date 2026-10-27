const list = document.getElementById("list");

async function load() {
  try {
    const { bookings } = await api("/api/bookings");
    if (!bookings.length) {
      list.innerHTML = `<div class="empty">You haven't booked anything yet. <a href="/">Browse movies</a></div>`;
      return;
    }
    const now = new Date();
    list.innerHTML = bookings.map((b) => {
      const upcoming = new Date(b.showtime.start_time) > now;
      const canCancel = b.status === "Confirmed" && upcoming;
      return `
      <div class="card booking-row">
        <div>
          <h3>${esc(b.movie.title)} <span class="badge ${b.status === "Confirmed" ? "on" : "off"}">${esc(b.status)}</span></h3>
          <p class="muted">${esc(b.theater.name)} · ${esc(fmtDateTime(b.showtime.start_time))}</p>
          <p>Seats: <b>${esc(b.seats.join(", "))}</b> · Total: <b>${esc(money(b.total))}</b></p>
          <p class="muted small">Ref: ${esc(b.reference)}</p>
        </div>
        <div class="row-actions">
          <a class="btn btn-small btn-ghost" href="/booking/${b.id}">View ticket</a>
          ${canCancel ? `<button type="button" class="btn btn-small btn-danger" data-cancel="${b.id}">Cancel</button>` : ""}
        </div>
      </div>`;
    }).join("");
  } catch (err) {
    list.innerHTML = `<p class="empty">${esc(err.message)}</p>`;
  }
}

list.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-cancel]");
  if (!btn) return;
  if (!confirm("Cancel this booking? Your seats will be released.")) return;
  try {
    await api(`/api/bookings/${btn.dataset.cancel}/cancel`, "POST");
    toast("Booking cancelled.", "success");
    load();
  } catch (err) {
    toast(err.message, "error");
  }
});

load();
