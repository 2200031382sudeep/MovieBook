const app = document.getElementById("app");
const showtimeId = Number(app.dataset.showtimeId);
const MAX_SEATS = 10;

let data = null;                 // showtime, movie, theater, booked seats
const selected = new Set();      // seats the user has clicked

async function load() {
  try {
    data = await api(`/api/showtimes/${showtimeId}`);
    if (data.started) {
      app.innerHTML = `<p class="empty">This show has already started. <a href="/movie/${data.movie.id}">See other showtimes</a></p>`;
      return;
    }
    draw();
  } catch (err) {
    app.innerHTML = `<p class="empty">${esc(err.message)}</p>`;
  }
}

function draw() {
  const { showtime, movie, theater, booked } = data;
  const rows = [];
  for (let r = 0; r < theater.rows; r++) {
    const letter = String.fromCharCode(65 + r);
    let seats = "";
    for (let n = 1; n <= theater.seats_per_row; n++) {
      const label = letter + n;
      const isBooked = booked.includes(label);
      const cls = isBooked ? "seat booked" : selected.has(label) ? "seat selected" : "seat";
      seats += `<button type="button" class="${cls}" data-seat="${label}" ${isBooked ? "disabled" : ""}
                 aria-label="Seat ${label}${isBooked ? ", booked" : ""}">${n}</button>`;
    }
    rows.push(`<div class="seat-row"><span class="row-label">${letter}</span>${seats}</div>`);
  }

  app.innerHTML = `
    <p><a href="/movie/${movie.id}" class="back-link">← Back to showtimes</a></p>
    <h2>${esc(movie.title)}</h2>
    <p class="muted">${esc(theater.name)} · ${esc(theater.location)} · ${esc(fmtDateTime(showtime.start_time))}</p>

    <div class="booking-layout">
      <div class="card">
        <div class="screen">SCREEN THIS WAY</div>
        <div class="seat-map"><div class="seat-map-inner">${rows.join("")}</div></div>
        <div class="legend">
          <span><i class="seat sample"></i> Available</span>
          <span><i class="seat sample selected"></i> Selected</span>
          <span><i class="seat sample booked"></i> Booked</span>
        </div>
      </div>

      <aside class="card summary">
        <h3>Your booking</h3>
        <p class="muted">Ticket price: <b>${esc(money(showtime.price))}</b> each</p>
        <p>Seats: <b id="seatText">–</b></p>
        <p>Tickets: <b id="seatCount">0</b></p>
        <p class="total">Total: <b id="totalText">₹0</b></p>
        <p class="form-error" id="bookError"></p>
        <button type="button" class="btn btn-block" id="confirmBtn" disabled>Confirm booking</button>
        <p class="muted small">You can pick up to ${MAX_SEATS} seats.</p>
      </aside>
    </div>`;

  app.querySelector(".seat-map").addEventListener("click", onSeatClick);
  document.getElementById("confirmBtn").addEventListener("click", confirmBooking);
  updateSummary();
}

function onSeatClick(e) {
  const btn = e.target.closest("button.seat");
  if (!btn || btn.disabled) return;
  const label = btn.dataset.seat;
  if (selected.has(label)) {
    selected.delete(label);
    btn.classList.remove("selected");
  } else {
    if (selected.size >= MAX_SEATS) { toast(`You can book up to ${MAX_SEATS} seats at a time.`, "error"); return; }
    selected.add(label);
    btn.classList.add("selected");
  }
  updateSummary();
}

function sortedSeats() {
  return [...selected].sort((a, b) => a[0].localeCompare(b[0]) || parseInt(a.slice(1)) - parseInt(b.slice(1)));
}

function updateSummary() {
  const seats = sortedSeats();
  document.getElementById("seatText").textContent = seats.length ? seats.join(", ") : "–";
  document.getElementById("seatCount").textContent = seats.length;
  document.getElementById("totalText").textContent = money(data.showtime.price * seats.length);
  document.getElementById("confirmBtn").disabled = seats.length === 0;
}

async function confirmBooking() {
  const btn = document.getElementById("confirmBtn");
  const errBox = document.getElementById("bookError");
  errBox.textContent = "";
  btn.disabled = true;
  btn.textContent = "Booking…";
  try {
    const { booking } = await api("/api/bookings", "POST", { showtime_id: showtimeId, seats: sortedSeats() });
    window.location.href = `/booking/${booking.id}`;
  } catch (err) {
    if (err.status === 401) { window.location.href = `/login?next=/book/${showtimeId}`; return; }
    selected.clear();
    await load();                                  // refresh which seats are taken
    const box = document.getElementById("bookError");
    if (box) box.textContent = err.message; else toast(err.message, "error");
  }
}

load();
