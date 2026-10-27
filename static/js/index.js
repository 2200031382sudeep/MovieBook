const grid = document.getElementById("movieGrid");
const searchInput = document.getElementById("searchInput");

async function loadMovies(q = "") {
  try {
    const { movies } = await api("/api/movies" + (q ? "?q=" + encodeURIComponent(q) : ""));
    if (!movies.length) {
      grid.innerHTML = `<p class="empty">${q ? "No movies match your search." : "No movies yet. The admin can add them from the Admin portal."}</p>`;
      return;
    }
    grid.innerHTML = movies.map((m) => `
      <a class="movie-card" href="/movie/${m.id}">
        <div class="poster">${posterHTML(m)}</div>
        <div class="movie-info">
          <h3>${esc(m.title)}</h3>
          <p class="muted">${esc(m.genre)}${m.genre && m.language ? " · " : ""}${esc(m.language)}</p>
          <p class="meta"><span>⭐ ${esc(m.rating)}</span><span>🕒 ${esc(m.duration_min)} min</span></p>
        </div>
      </a>`).join("");
  } catch (err) {
    grid.innerHTML = `<p class="empty">${esc(err.message)}</p>`;
  }
}

let timer;
searchInput.addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(() => loadMovies(searchInput.value.trim()), 300);
});
loadMovies();
