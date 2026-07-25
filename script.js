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

function pageUrl() {
  return location.origin + location.pathname;
}

function wireSharing() {
  const url = pageUrl();
  const text = "The American Exit Index: 20 countries ranked daily on how easily Americans can actually move there.";
  const enc = encodeURIComponent;

  const x = document.getElementById("share-x");
  if (x) x.href = `https://twitter.com/intent/tweet?text=${enc(text)}&url=${enc(url)}`;
  const reddit = document.getElementById("share-reddit");
  if (reddit) reddit.href = `https://www.reddit.com/submit?url=${enc(url)}&title=${enc(text)}`;
  const wa = document.getElementById("share-wa");
  if (wa) wa.href = `https://wa.me/?text=${enc(text + " " + url)}`;

  const native = document.getElementById("share-native");
  if (native) {
    native.addEventListener("click", async () => {
      if (navigator.share) {
        try { await navigator.share({ title: "The American Exit Index", text, url }); return; }
        catch (e) { /* user cancelled — fall through to copy */ }
      }
      try {
        await navigator.clipboard.writeText(url);
        native.textContent = "Link copied ✓";
        setTimeout(() => { native.textContent = "Share this index"; }, 2000);
      } catch (e) { /* clipboard blocked — no-op */ }
    });
  }

  // Embed snippet
  const embedSrc = pageUrl() + "?embed=1";
  const snippet = `<iframe src="${embedSrc}" width="100%" height="640" style="border:1px solid #1f2a37;border-radius:10px" title="The American Exit Index" loading="lazy"></iframe>`;
  const codeEl = document.getElementById("embed-code");
  if (codeEl) codeEl.textContent = snippet;
  const copyBtn = document.getElementById("copy-embed");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(snippet);
        copyBtn.textContent = "Copied ✓";
        setTimeout(() => { copyBtn.textContent = "Copy"; }, 2000);
      } catch (e) { /* clipboard blocked — no-op */ }
    });
  }
}

async function init() {
  wireSharing();

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
