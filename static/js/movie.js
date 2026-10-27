const app = document.getElementById("app");
const movieId = app.dataset.movieId;

async function loadMovie() {
  try {
    const { movie, showtimes } = await api(`/api/movies/${movieId}`);
    document.title = movie.title + " – MovieBook";

    // Group the showtimes by theater
    const byTheater = {};
    showtimes.forEach((s) => {
      (byTheater[s.theater.id] ||= { theater: s.theater, shows: [] }).shows.push(s);
    });

    const showsHTML = Object.values(byTheater).map(({ theater, shows }) => `
      <div class="card theater-block">
        <h3>${esc(theater.name)}</h3>
        <p class="muted">📍 ${esc(theater.location)}</p>
        <div class="show-list">
          ${shows.map((s) => s.seats_left > 0
            ? `<a class="show-chip" href="/book/${s.id}">
                 <small>${esc(fmtDay(s.start_time))}</small>
                 <b>${esc(fmtTime(s.start_time))}</b>
                 <span>${esc(money(s.price))} · ${s.seats_left} left</span>
               </a>`
            : `<span class="show-chip sold"><small>${esc(fmtDay(s.start_time))}</small><b>${esc(fmtTime(s.start_time))}</b><span>Sold out</span></span>`
          ).join("")}
        </div>
      </div>`).join("");

    app.innerHTML = `
      <section class="movie-hero">
        <div class="container movie-hero-inner">
          <div class="poster big">${posterHTML(movie)}</div>
          <div>
            <h1>${esc(movie.title)}</h1>
            <p class="meta"><span>⭐ ${esc(movie.rating)}</span><span>🕒 ${esc(movie.duration_min)} min</span>
              <span>${esc(movie.genre)}</span><span>${esc(movie.language)}</span></p>
            <p>${esc(movie.description)}</p>
          </div>
        </div>
      </section>
      <section class="container section">
        <h2>Choose a theater and showtime</h2>
        ${showsHTML || '<p class="empty">No upcoming shows for this movie yet.</p>'}
      </section>`;
  } catch (err) {
    app.innerHTML = `<section class="container section"><p class="empty">${esc(err.message)}</p></section>`;
  }
}
loadMovie();
