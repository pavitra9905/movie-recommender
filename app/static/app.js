const els = {
  form: document.getElementById("finder"),
  title: document.getElementById("title"),
  suggestions: document.getElementById("title-suggestions"),
  chips: document.getElementById("genre-chips"),
  rating: document.getElementById("min-rating"),
  ratingOut: document.getElementById("rating-out"),
  minYear: document.getElementById("min-year"),
  maxYear: document.getElementById("max-year"),
  runtime: document.getElementById("max-runtime"),
  limit: document.getElementById("limit"),
  clear: document.getElementById("clear"),
  summary: document.getElementById("summary"),
  status: document.getElementById("status"),
  results: document.getElementById("results"),
  dialog: document.getElementById("detail"),
  detailBody: document.getElementById("detail-body"),
  detailClose: document.getElementById("detail-close"),
};

let latestRequest = 0;

/* ---------- Helpers ---------- */

function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  node.append(...children.flat().filter((child) => child !== null && child !== undefined && child !== false));
  return node;
}

async function getJSON(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Something went wrong. Try again.");
  return data;
}

function scrollTo(node) {
  const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  node.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
}

/* ---------- Genre chips ---------- */

function setChip(chip, on) {
  chip.setAttribute("aria-pressed", String(on));
}

function toggleChip(event) {
  const chip = event.currentTarget;
  setChip(chip, chip.getAttribute("aria-pressed") !== "true");
}

function selectedGenres() {
  return [...els.chips.querySelectorAll('.chip[aria-pressed="true"]')].map((chip) => chip.dataset.genre);
}

async function loadGenres() {
  try {
    const { genres } = await getJSON("/genres");
    els.chips.replaceChildren(
      ...genres.map((name) =>
        h("button", { class: "chip", type: "button", "aria-pressed": "false", "data-genre": name, onclick: toggleChip }, name)
      )
    );
  } catch (error) {
    els.status.textContent = error.message;
  }
}

/* ---------- Filters <-> URL ---------- */

function updateRatingOutput() {
  const value = Number(els.rating.value);
  els.ratingOut.textContent = value > 0 ? `${value.toFixed(1)}+` : "Any";
}

function buildParams() {
  const params = new URLSearchParams();
  const title = els.title.value.trim();
  if (title) params.set("title", title);
  selectedGenres().forEach((genre) => params.append("genre", genre));
  if (Number(els.rating.value) > 0) params.set("min_rating", els.rating.value);
  if (els.minYear.value) params.set("min_year", els.minYear.value);
  if (els.maxYear.value) params.set("max_year", els.maxYear.value);
  if (els.runtime.value) params.set("max_runtime", els.runtime.value);
  params.set("limit", els.limit.value);
  return params;
}

function applyParams(params) {
  els.title.value = params.get("title") || "";

  const genres = params
    .getAll("genre")
    .flatMap((value) => value.split(","))
    .map((genre) => genre.trim().toLowerCase())
    .filter(Boolean);
  els.chips.querySelectorAll(".chip").forEach((chip) => {
    setChip(chip, genres.includes(chip.dataset.genre.toLowerCase()));
  });

  els.rating.value = params.get("min_rating") || 0;
  updateRatingOutput();
  els.minYear.value = params.get("min_year") || "";
  els.maxYear.value = params.get("max_year") || "";
  els.runtime.value = params.get("max_runtime") || "";
  if (params.get("limit")) els.limit.value = params.get("limit");
}

/* ---------- Rendering ---------- */

function posterEl(movie) {
  const wrap = h("div", { class: "poster-wrap" });
  const fallback = () => h("div", { class: "poster-fallback" }, movie.title);

  if (!movie.poster_url || !movie.poster_url.startsWith("http")) {
    wrap.append(fallback());
    return wrap;
  }

  const image = h("img", { src: movie.poster_url, alt: "", loading: "lazy", referrerpolicy: "no-referrer" });
  image.addEventListener("error", () => image.replaceWith(fallback()));
  wrap.append(image);
  return wrap;
}

function createTile(movie, index) {
  const poster = posterEl(movie);
  if (movie.rating !== null && movie.rating !== undefined) {
    poster.append(h("span", { class: "rating" }, `★ ${Number(movie.rating).toFixed(1)}`));
  }

  return h(
    "button",
    { class: "tile", type: "button", style: `--i:${Math.min(index, 12)}`, onclick: () => openDetail(movie) },
    poster,
    h("div", { class: "tile-title" }, movie.title, movie.year ? h("span", { class: "year" }, String(movie.year)) : null),
    h("div", { class: "tile-meta" }, movie.genres.slice(0, 3).join(", ")),
    movie.similarity > 0 ? h("div", { class: "tile-match" }, `${Math.round(movie.similarity * 100)}% similar`) : null
  );
}

function buildSummary(reference) {
  if (!reference) {
    return h("h2", {}, "Top picks for your preferences");
  }

  const heading = reference.year ? `${reference.title} (${reference.year})` : reference.title;
  return h(
    "div",
    { class: "reference" },
    posterEl(reference),
    h(
      "div",
      {},
      h("p", { class: "muted" }, "Because you liked"),
      h("h2", {}, heading),
      h("p", { class: "muted" }, reference.genres.join(", ")),
      h("button", { class: "ghost", type: "button", onclick: () => openDetail(reference) }, "View details")
    )
  );
}

function showLoading() {
  const count = Math.min(Number(els.limit.value) || 12, 12);
  els.summary.hidden = true;
  els.status.textContent = "Finding movies...";
  els.results.classList.remove("reveal");
  els.results.replaceChildren(
    ...Array.from({ length: count }, () => h("div", { class: "skeleton", "aria-hidden": "true" }))
  );
}

function showMessage(text) {
  els.summary.hidden = true;
  els.results.replaceChildren();
  els.status.textContent = text;
}

function render(data) {
  if (data.count === 0) {
    showMessage("No movies match those filters. Try a lower minimum rating, a wider year range, or fewer genres.");
    return;
  }

  els.summary.replaceChildren(buildSummary(data.reference));
  els.summary.hidden = false;
  els.status.textContent = `${data.count} ${data.count === 1 ? "recommendation" : "recommendations"}`;
  els.results.replaceChildren(...data.results.map(createTile));
  els.results.classList.add("reveal");
}

/* ---------- Detail dialog ---------- */

function openDetail(movie) {
  const facts = [];
  if (movie.year) facts.push(String(movie.year));
  if (movie.runtime_minutes) facts.push(`${movie.runtime_minutes} min`);
  if (movie.rating !== null && movie.rating !== undefined) facts.push(`${Number(movie.rating).toFixed(1)} on IMDb`);

  els.detailBody.replaceChildren(
    posterEl(movie),
    h(
      "div",
      { class: "detail-info" },
      h("h2", { id: "detail-title" }, movie.title),
      h("p", { class: "facts" }, facts.join(", ")),
      h("div", { class: "tags" }, movie.genres.map((genre) => h("span", { class: "tag" }, genre))),
      movie.plot ? h("p", { class: "plot" }, movie.plot) : null,
      movie.director ? h("p", { class: "credit" }, h("strong", {}, "Director "), movie.director) : null,
      movie.actors ? h("p", { class: "credit" }, h("strong", {}, "Cast "), movie.actors) : null,
      h("button", { class: "primary", type: "button", onclick: () => findLike(movie) }, "Find movies like this")
    )
  );
  els.dialog.showModal();
}

function findLike(movie) {
  els.title.value = movie.title;
  els.dialog.close();
  runSearch(true);
}

els.detailClose.addEventListener("click", () => els.dialog.close());
els.dialog.addEventListener("click", (event) => {
  if (event.target === els.dialog) els.dialog.close();
});

/* ---------- Search ---------- */

async function runSearch(scroll = true) {
  const requestId = ++latestRequest;
  const params = buildParams();
  showLoading();

  try {
    const data = await getJSON(`/recommend?${params}`);
    if (requestId !== latestRequest) return;
    history.replaceState(null, "", `?${params}`);
    render(data);
  } catch (error) {
    if (requestId !== latestRequest) return;
    showMessage(error.message);
  }

  if (scroll) scrollTo(els.summary.hidden ? els.status : els.summary);
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch(true);
});

els.rating.addEventListener("input", updateRatingOutput);

els.clear.addEventListener("click", () => {
  els.form.reset();
  els.chips.querySelectorAll(".chip").forEach((chip) => setChip(chip, false));
  updateRatingOutput();
  els.summary.hidden = true;
  els.results.replaceChildren();
  els.status.textContent = "";
  history.replaceState(null, "", location.pathname);
  els.title.focus();
});

/* ---------- Title suggestions ---------- */

let suggestionTimer;
els.title.addEventListener("input", () => {
  clearTimeout(suggestionTimer);
  const query = els.title.value.trim();
  if (query.length < 2) return;

  suggestionTimer = setTimeout(async () => {
    try {
      const { results } = await getJSON(`/movies/search?q=${encodeURIComponent(query)}`);
      els.suggestions.replaceChildren(...results.map((movie) => new Option(movie.title)));
    } catch {
      // Suggestions are optional, so ignore errors here
    }
  }, 250);
});

async function showCatalogSize() {
  try {
    const { total_movies } = await getJSON("/movies/count");
    document.getElementById("catalog-size").textContent =
      `${total_movies.toLocaleString()} movies in the catalogue.`;
  } catch {
    // The count is optional, so ignore errors here
  }
}

/* ---------- Start ---------- */

async function init() {
  await loadGenres();
  const params = new URLSearchParams(location.search);
  applyParams(params);
  if ([...params.keys()].some((key) => key !== "limit")) runSearch(false);
}


async function init() {
  showCatalogSize();
  await loadGenres();
  const params = new URLSearchParams(location.search);
  applyParams(params);
  if ([...params.keys()].some((key) => key !== "limit")) runSearch(false);
}

init();