// American Exit Index — dashboard
//
// Loads ./data/latest.json (same repo when deployed to GitHub Pages),
// renders the rankings table, wires up region filter + sort.

const DATA_URL = new URL("./data/latest.json", window.location.href).toString();

function scoreClass(n) {
  if (n >= 70) return "score-high";
  if (n >= 40) return "score-mid";
  return "score-low";
}

function deltaCell(d) {
  if (!d || d.composite_change === 0) return '<span class="delta-flat">—</span>';
  if (d.composite_change > 0) {
    return `<span class="delta-up">▲ ${d.composite_change}</span>`;
  }
  return `<span class="delta-down">▼ ${Math.abs(d.composite_change)}</span>`;
}

function renderRow(c) {
  const s = c.scores;
  return `<tr data-region="${c.region}">
    <td class="num">${c.rank}</td>
    <td><strong>${c.name}</strong></td>
    <td>${c.primary_visa || "—"}</td>
    <td class="num"><span class="score-cell ${scoreClass(s.visa_accessibility)}">${s.visa_accessibility}</span></td>
    <td class="num"><span class="score-cell ${scoreClass(s.dollar_purchasing_power)}">${s.dollar_purchasing_power}</span></td>
    <td class="num"><span class="score-cell ${scoreClass(s.speed_to_residency)}">${s.speed_to_residency}</span></td>
    <td class="num"><span class="score-cell ${scoreClass(s.composite)}">${s.composite}</span></td>
    <td>${c.tier}</td>
    <td class="num">${deltaCell(c.delta)}</td>
  </tr>`;
}

function sortRankings(rankings, key) {
  const sorted = [...rankings].sort((a, b) => b.scores[key] - a.scores[key]);
  sorted.forEach((c, i) => { c.rank = i + 1; });
  return sorted;
}

function applyFilters(rankings) {
  const region = document.getElementById("region-filter").value;
  const sortKey = document.getElementById("sort").value;
  const sorted = sortRankings(rankings, sortKey);
  const filtered = region ? sorted.filter(c => c.region === region) : sorted;
  document.getElementById("rankings-body").innerHTML = filtered.map(renderRow).join("");
}

async function init() {
  let data;
  try {
    const resp = await fetch(DATA_URL);
    data = await resp.json();
  } catch (e) {
    document.getElementById("rankings-body").innerHTML =
      `<tr><td colspan="9">Could not load ranking data. ${e.message}</td></tr>`;
    return;
  }

  document.getElementById("updated").textContent = new Date(data.generated_at).toLocaleDateString(
    "en-US", { year: "numeric", month: "long", day: "numeric" }
  );

  const regions = [...new Set(data.rankings.map(c => c.region))].sort();
  const regionSelect = document.getElementById("region-filter");
  regions.forEach(r => {
    const opt = document.createElement("option");
    opt.value = r;
    opt.textContent = r;
    regionSelect.appendChild(opt);
  });

  const rankings = data.rankings;
  document.getElementById("region-filter").addEventListener("change", () => applyFilters(rankings));
  document.getElementById("sort").addEventListener("change", () => applyFilters(rankings));

  applyFilters(rankings);
}

init();
