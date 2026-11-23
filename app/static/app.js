const form = document.getElementById("filters");
const titleInput = document.getElementById("title");
const genreSelect = document.getElementById("genres");
const suggestions = document.getElementById("title-suggestions");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

const NUMERIC_FIELDS = {
  min_rating: "min-rating",
  min_year: "min-year",
  max_year: "max-year",
  max_runtime: "max-runtime",
  limit: "limit",
};

async function getJSON(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong");
  }
  return data;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function placeholder() {
  return el("div", "poster placeholder", "🎬");
}

function createPoster(movie) {
  if (!movie.poster_url || !movie.poster_url.startsWith("http")) {
    return placeholder();
  }
  const image = el("img", "poster");
  image.src = movie.poster_url;
  image.alt = `${movie.title} poster`;
  image.loading = "lazy";
  image.referrerPolicy = "no-referrer";
  image.onerror = () => image.replaceWith(placeholder());
  return image;
}

function createCard(movie) {
  const card = el("article", "card");
  const info = el("div", "info");

  info.append(
    el("h3", "", movie.year ? `${movie.title} (${movie.year})` : movie.title),
    el("div", "meta", movie.genres.join(" · ")),
    el("div", "rating", `★ ${movie.rating ?? "N/A"}`)
  );

  if (movie.director) {
    info.append(el("div", "meta", `Dir. ${movie.director}`));
  }
  if (movie.similarity > 0) {
    info.append(el("div", "match", `${Math.round(movie.similarity * 100)}% match`));
  }

  card.append(createPoster(movie), info);
  return card;
}

function buildParams() {
  const params = new URLSearchParams();

  const title = titleInput.value.trim();
  if (title) params.set("title", title);

  for (const option of genreSelect.selectedOptions) {
    params.append("genre", option.value);
  }

  for (const [param, id] of Object.entries(NUMERIC_FIELDS)) {
    const value = document.getElementById(id).value;
    if (value !== "") params.set(param, value);
  }
  return params;
}

async function loadGenres() {
  try {
    const { genres } = await getJSON("/genres");
    genres.forEach((name) => genreSelect.add(new Option(name, name)));
  } catch (error) {
    statusEl.textContent = error.message;
  }
}

let suggestionTimer;
titleInput.addEventListener("input", () => {
  clearTimeout(suggestionTimer);
  const query = titleInput.value.trim();
  if (query.length < 2) return;

  suggestionTimer = setTimeout(async () => {
    try {
      const { results } = await getJSON(`/movies/search?q=${encodeURIComponent(query)}`);
      suggestions.replaceChildren(...results.map((movie) => new Option(movie.title)));
    } catch {
      // Suggestions are optional, so ignore errors here
    }
  }, 250);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusEl.textContent = "Finding movies...";
  resultsEl.replaceChildren();

  try {
    const data = await getJSON(`/recommend?${buildParams()}`);
    if (data.count === 0) {
      statusEl.textContent = "No movies match those preferences. Try loosening the filters.";
      return;
    }
    statusEl.textContent = `${data.count} recommendations`;
    resultsEl.replaceChildren(...data.results.map(createCard));
  } catch (error) {
    statusEl.textContent = error.message;
  }
});

loadGenres();