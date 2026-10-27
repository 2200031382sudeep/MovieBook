const app = document.getElementById("app");
const bookingId = app.dataset.bookingId;

async function load() {
  try {
    const { booking: b } = await api(`/api/bookings/${bookingId}`);
    const cancelled = b.status === "Cancelled";
    app.innerHTML = `
      <div class="ticket">
        <div class="ticket-head ${cancelled ? "cancelled" : ""}">
          <div class="tick">${cancelled ? "✕" : "✓"}</div>
          <h1>${cancelled ? "Booking cancelled" : "Booking confirmed!"}</h1>
          <p>${cancelled ? "These seats have been released." : "Show this reference at the theater."}</p>
          <div class="reference">${esc(b.reference)}</div>
        </div>
        <div class="ticket-body">
          <h2>${esc(b.movie.title)}</h2>
          <dl>
            <dt>Theater</dt><dd>${esc(b.theater.name)}<br><small>${esc(b.theater.location)}</small></dd>
            <dt>Show time</dt><dd>${esc(fmtDateTime(b.showtime.start_time))}</dd>
            <dt>Seats</dt><dd>${esc(b.seats.join(", "))}</dd>
            <dt>Tickets</dt><dd>${b.seats.length} × ${esc(money(b.showtime.price))}</dd>
            <dt>Total paid</dt><dd class="total-price">${esc(money(b.total))}</dd>
            <dt>Booked by</dt><dd>${esc(b.user_name)}</dd>
          </dl>
          <div class="ticket-actions">
            <button type="button" class="btn btn-ghost" onclick="window.print()">Print ticket</button>
            <a class="btn" href="/my-bookings">My bookings</a>
          </div>
        </div>
      </div>`;
  } catch (err) {
    app.innerHTML = `<p class="empty">${esc(err.message)}</p>`;
  }
}
load();
