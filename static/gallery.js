/**
 * Media Tracker Gallery Client JavaScript v4.0
 * All 6 Features: Trailers, Roulette, Stats, CSV Import/Export, Tags, and Dark Mode.
 */
(() => {
  "use strict";

  const state = {
    kind: "all",
    status: "",
    tag: "",
    query: "",
    sort: "updated_at",
    dir: "desc",
    limit: 50,
    offset: 0,
    total: 0,
    summary: null,
  };

  const KIND_LABELS = {
    all: "Tüm Yapımlar",
    movie: "Film",
    "anime-movie": "Anime Film",
    series: "Dizi",
    "anime-series": "Anime Dizi",
    anime: "Tüm Animeler",
  };

  const STATUS_LABELS = {
    "": "Tüm Durumlar",
    planned: "Planlandı",
    in_progress: "İzleniyor",
    completed: "Tamamlandı",
    paused: "Durduruldu",
    dropped: "Bırakıldı",
  };

  const STATUS_COLORS = {
    planned: "bg-zinc-600 text-zinc-100",
    in_progress: "bg-blue-600 text-blue-50",
    completed: "bg-emerald-600 text-emerald-50",
    paused: "bg-amber-600 text-amber-50",
    dropped: "bg-red-600 text-red-50",
  };

  const $ = (id) => document.getElementById(id);
  const dbLine = $("dbLine");
  const refreshButton = $("refreshButton");
  const addButton = $("addButton");
  const rouletteButton = $("rouletteButton");
  const importExportBtn = $("importExportBtn");
  const themeToggle = $("themeToggle");
  const jsonLink = $("jsonLink");

  const statTotal = $("statTotal");
  const statRating = $("statRating");
  const statRatedCount = $("statRatedCount");
  const statCompleted = $("statCompleted");
  const statInProgress = $("statInProgress");
  const statWatchHours = $("statWatchHours");
  const statWatchDays = $("statWatchDays");

  const ratingChart = $("ratingChart");
  const kindTabs = $("kindTabs");
  const statusTabs = $("statusTabs");
  const tagPills = $("tagPills");
  const tagsSection = $("tagsSection");

  const searchInput = $("searchInput");
  const sortSelect = $("sortSelect");
  const directionButton = $("directionButton");
  const pageSizeSelect = $("pageSizeSelect");
  const resultLine = $("resultLine");
  const prevButton = $("prevButton");
  const nextButton = $("nextButton");
  const pageLine = $("pageLine");
  const recordsPanel = $("recordsPanel");
  const loadingState = $("loadingState");
  const errorState = $("errorState");
  const emptyState = $("emptyState");
  const posterGrid = $("posterGrid");

  const detailModal = $("detailModal");
  const modalContent = $("modalContent");
  const addModal = $("addModal");
  const addModalContent = $("addModalContent");
  const trailerModal = $("trailerModal");
  const trailerTitle = $("trailerTitle");
  const trailerIframe = $("trailerIframe");
  const closeTrailerBtn = $("closeTrailerBtn");
  const importExportModal = $("importExportModal");
  const closeImportExportBtn = $("closeImportExportBtn");
  const csvFileInput = $("csvFileInput");
  const uploadCsvBtn = $("uploadCsvBtn");

  let searchTimeout = null;

  // ── Dark / Light Theme ─────────────────────────────────
  function initTheme() {
    const saved = localStorage.getItem("theme");
    const isDark = saved ? saved === "dark" : true; // Default dark
    applyTheme(isDark);
  }

  function applyTheme(isDark) {
    document.documentElement.classList.toggle("dark", isDark);
    if (themeToggle) themeToggle.textContent = isDark ? "🌙" : "☀️";
    localStorage.setItem("theme", isDark ? "dark" : "light");
  }

  themeToggle?.addEventListener("click", () => {
    const isDark = document.documentElement.classList.contains("dark");
    applyTheme(!isDark);
  });

  // ── Toast Notification ─────────────────────────────────
  function toast(message, type = "success") {
    const container = document.getElementById("toastContainer") || createToastContainer();
    const el = document.createElement("div");
    const colors = {
      success: "bg-emerald-900 text-emerald-100 border-emerald-700",
      error: "bg-red-900 text-red-100 border-red-700",
      info: "bg-zinc-800 text-zinc-100 border-zinc-600",
    };
    el.className = `border px-4 py-3 text-sm font-medium shadow-lg transition-all duration-300 ${colors[type] || colors.info}`;
    el.textContent = message;
    el.style.opacity = "0";
    el.style.transform = "translateY(-8px)";
    container.appendChild(el);
    requestAnimationFrame(() => {
      el.style.opacity = "1";
      el.style.transform = "translateY(0)";
    });
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateY(-8px)";
      setTimeout(() => el.remove(), 300);
    }, 3000);
  }

  function createToastContainer() {
    const c = document.createElement("div");
    c.id = "toastContainer";
    c.className = "fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none";
    c.style.maxWidth = "360px";
    document.body.appendChild(c);
    return c;
  }

  // ── API Helpers ────────────────────────────────────────
  async function api(method, path, body = null) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }

  // ── Summary & Stats ────────────────────────────────────
  async function fetchSummary() {
    try {
      const data = await api("GET", "/api/summary");
      state.summary = data;
      renderSummary(data);
    } catch (err) {
      console.error("Summary fetch error:", err);
    }
  }

  function renderSummary(data) {
    if (dbLine) {
      const posters = data.posters?.total_files || 0;
      dbLine.textContent = `SQLite — ${posters} poster yüklü — IMDb & TMDB Türkçe Aktif ✓`;
    }
    if (statTotal) statTotal.textContent = (data.counts?.all || 0).toLocaleString("tr-TR");
    if (statRating) statRating.textContent = data.avg_rating ? Number(data.avg_rating).toFixed(1) : "-";
    if (statRatedCount) statRatedCount.textContent = `${(data.rating_count || 0).toLocaleString("tr-TR")} kayıt puanlandı`;
    if (statCompleted) statCompleted.textContent = (data.status_counts?.completed || 0).toLocaleString("tr-TR");
    if (statInProgress) statInProgress.textContent = (data.status_counts?.in_progress || 0).toLocaleString("tr-TR");

    // Watch time
    const wt = data.stats?.watch_time;
    if (statWatchHours) statWatchHours.textContent = wt?.total_hours || 0;
    if (statWatchDays) statWatchDays.textContent = `${wt?.total_days || 0} güne eşdeğer`;

    renderRatingChart(data.rating_buckets || []);
    renderKindTabs(data.counts || {});
    renderStatusTabs(data.status_counts || {});
    renderTags(data.stats?.tags || []);
  }

  function renderRatingChart(buckets) {
    if (!ratingChart) return;
    ratingChart.innerHTML = "";
    const counts = buckets.slice(1, 11);
    const max = Math.max(1, ...counts);
    counts.forEach((count, idx) => {
      const rating = idx + 1;
      const pct = Math.max(8, (count / max) * 100);
      const col = document.createElement("div");
      col.className = "flex-1 flex flex-col items-center gap-1 group cursor-pointer";
      col.title = `${rating} Puan: ${count} kayıt`;
      col.innerHTML = `
        <div class="w-full bg-zinc-200 dark:bg-zinc-800 hover:bg-amber-400 dark:hover:bg-amber-400 transition flex items-end justify-center" style="height:60px">
          <div class="w-full bg-zinc-800 dark:bg-zinc-200 group-hover:bg-amber-500 transition-all duration-300" style="height:${pct}%"></div>
        </div>
        <span class="mono text-[10px] text-zinc-500 font-semibold">${rating}</span>`;
      ratingChart.appendChild(col);
    });
  }

  function renderKindTabs(counts) {
    if (!kindTabs) return;
    kindTabs.innerHTML = "";
    ["all", "movie", "anime-movie", "series", "anime-series", "anime"].forEach((k) => {
      const active = state.kind === k;
      const btn = document.createElement("button");
      btn.className = `flex items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wider transition ${active ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700"}`;
      btn.innerHTML = `<span>${KIND_LABELS[k]}</span><span class="mono px-1.5 py-0.5 text-[10px] ${active ? "bg-zinc-800 dark:bg-zinc-300 text-zinc-300 dark:text-zinc-900" : "bg-zinc-200 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300"}">${counts[k] ?? 0}</span>`;
      btn.addEventListener("click", () => { state.kind = k; state.offset = 0; fetchRecords(); fetchSummary(); });
      kindTabs.appendChild(btn);
    });
  }

  function renderStatusTabs(statusCounts) {
    if (!statusTabs) return;
    statusTabs.innerHTML = "";
    ["", "completed", "in_progress", "planned", "paused", "dropped"].forEach((st) => {
      const active = state.status === st;
      const count = st === "" ? (state.summary?.counts?.all || 0) : (statusCounts[st] ?? 0);
      const btn = document.createElement("button");
      btn.className = `flex items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wider transition ${active ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700"}`;
      btn.innerHTML = `<span>${STATUS_LABELS[st]}</span><span class="mono px-1.5 py-0.5 text-[10px] ${active ? "bg-zinc-800 dark:bg-zinc-300 text-zinc-300 dark:text-zinc-900" : "bg-zinc-200 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300"}">${count}</span>`;
      btn.addEventListener("click", () => { state.status = st; state.offset = 0; fetchRecords(); });
      statusTabs.appendChild(btn);
    });
  }

  function renderTags(tags) {
    if (!tagPills || !tagsSection) return;
    if (!tags.length) {
      tagsSection.classList.add("hidden");
      return;
    }
    tagsSection.classList.remove("hidden");
    tagPills.innerHTML = "";

    // "Tümü" tag pill
    const allPill = document.createElement("button");
    const isAllActive = state.tag === "";
    allPill.className = `px-2 py-1 text-[10px] font-semibold uppercase tracking-wider transition ${isAllActive ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-900" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200"}`;
    allPill.textContent = "Tümü";
    allPill.addEventListener("click", () => { state.tag = ""; state.offset = 0; fetchRecords(); renderTags(tags); });
    tagPills.appendChild(allPill);

    tags.forEach((t) => {
      const active = state.tag === t;
      const btn = document.createElement("button");
      btn.className = `px-2 py-1 text-[10px] font-semibold uppercase tracking-wider transition ${active ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-900" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200"}`;
      btn.textContent = `#${t}`;
      btn.addEventListener("click", () => {
        state.tag = active ? "" : t;
        state.offset = 0;
        fetchRecords();
        renderTags(tags);
      });
      tagPills.appendChild(btn);
    });
  }

  // ── Records ────────────────────────────────────────────
  async function fetchRecords() {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      kind: state.kind, status: state.status, tag: state.tag,
      q: state.query, sort: state.sort, dir: state.dir,
      limit: state.limit, offset: state.offset
    });
    const url = `/api/records?${params}`;
    if (jsonLink) jsonLink.href = url;
    try {
      const data = await api("GET", url);
      state.total = data.total || 0;
      renderRecords(data.records || []);
      updatePagination();
    } catch (err) {
      setError("Kayıtlar yüklenemedi: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  function renderRecords(records) {
    if (!posterGrid) return;
    posterGrid.innerHTML = "";
    if (!records.length) {
      emptyState?.classList.remove("hidden");
      posterGrid.classList.add("hidden");
      if (resultLine) resultLine.textContent = "0 kayıt";
      return;
    }
    emptyState?.classList.add("hidden");
    posterGrid.classList.remove("hidden");
    if (resultLine) resultLine.textContent = `${state.total.toLocaleString("tr-TR")} kayıt (${state.offset + 1}–${Math.min(state.offset + records.length, state.total)})`;
    records.forEach((rec) => posterGrid.appendChild(createPosterCard(rec)));
  }

  function createPosterCard(rec) {
    const card = document.createElement("div");
    card.className = "poster-card group";
    card.tabIndex = 0;
    const kindBadge = rec.is_anime ? (rec.media_type === "movie" ? "Anime Film" : "Anime Dizi") : (rec.media_type === "movie" ? "Film" : "Dizi");
    const statusBadge = STATUS_LABELS[rec.status] || rec.status;
    const statusColor = STATUS_COLORS[rec.status] || "bg-zinc-700 text-white";
    const posterSrc = rec.poster_url;

    if (posterSrc) {
      card.innerHTML = `
        <img src="${posterSrc}" alt="${rec.title}" loading="lazy" />
        <div class="poster-overlay">
          <span class="inline-block self-start text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 mb-1 ${statusColor}">${statusBadge}</span>
          <h3 class="text-sm font-bold leading-tight line-clamp-2">${rec.title}</h3>
          <div class="mt-1 flex items-center justify-between text-xs text-zinc-300">
            <span>${rec.release_year || "—"}</span>
            <span class="mono font-semibold text-amber-400">★ ${rec.rating ? rec.rating + "/10" : (rec.imdb_rating ? "IMDb " + rec.imdb_rating : (rec.tmdb_rating ? "TMDB " + Number(rec.tmdb_rating).toFixed(1) : "—"))}</span>
          </div>
        </div>`;
    } else {
      const initials = rec.title.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
      card.innerHTML = `
        <div class="w-full h-full p-4 flex flex-col justify-between bg-gradient-to-b from-zinc-900 via-zinc-900 to-zinc-950 text-white select-none">
          <div class="flex items-start justify-between gap-1">
            <span class="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 bg-zinc-800 text-zinc-300">${kindBadge}</span>
            <span class="mono text-xs font-bold text-amber-400">★ ${rec.rating || (rec.imdb_rating ? "IMDb " + rec.imdb_rating : "—")}</span>
          </div>
          <div class="my-auto text-center py-2">
            <div class="mono text-2xl font-bold tracking-widest text-zinc-600 mb-1">${initials}</div>
            <h3 class="text-xs font-bold leading-tight line-clamp-3 px-1 text-zinc-100">${rec.title}</h3>
          </div>
          <div class="flex items-center justify-between text-[11px] text-zinc-400 pt-2 border-t border-zinc-800">
            <span>${rec.release_year || "—"}</span>
            <span class="text-[10px] font-semibold px-1.5 py-0.5 ${statusColor}">${statusBadge}</span>
          </div>
        </div>
        <div class="poster-overlay">
          <span class="inline-block self-start text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 mb-1 ${statusColor}">${statusBadge}</span>
          <h3 class="text-sm font-bold leading-tight line-clamp-2">${rec.title}</h3>
          <p class="text-xs text-zinc-300 mt-1 line-clamp-3">${rec.overview || rec.note || ""}</p>
          <div class="mt-2 flex items-center justify-between text-xs text-zinc-400">
            <span>${rec.release_year || "—"}</span>
            <span class="mono font-semibold text-amber-400">★ ${rec.rating ? rec.rating + "/10" : "—"}</span>
          </div>
        </div>`;
    }
    card.addEventListener("click", () => openDetail(rec.id));
    card.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDetail(rec.id); } });
    return card;
  }

  // ── Detail Modal ───────────────────────────────────────
  async function openDetail(mediaId) {
    if (!detailModal || !modalContent) return;
    modalContent.innerHTML = `<div class="p-8 text-center text-zinc-400 animate-pulse">Yükleniyor…</div>`;
    showModal(detailModal);
    try {
      const rec = await api("GET", `/api/records/${mediaId}`);
      const typeName = rec.is_anime ? (rec.media_type === "movie" ? "Anime Film" : "Anime Dizi") : (rec.media_type === "movie" ? "Film" : "Dizi");
      const statusBadge = STATUS_LABELS[rec.status] || rec.status;
      const statusColor = STATUS_COLORS[rec.status] || "bg-zinc-700 text-white";
      const posterSrc = rec.poster_url;
      const genres = Array.isArray(rec.genres) ? rec.genres : [];
      const tags = Array.isArray(rec.tags) ? rec.tags : [];

      let seasonsHtml = "";
      if (rec.seasons?.length) {
        seasonsHtml = `<div class="mt-4 pt-4 border-t border-zinc-800">
          <h4 class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-2">Sezon Takibi</h4>
          <div class="grid gap-1.5">${rec.seasons.map(s =>
            `<div class="flex items-center justify-between text-xs bg-zinc-800/60 px-3 py-2"><span>${s.season_number}. Sezon</span><span class="mono text-zinc-300">${s.watched_episodes}/${s.episode_count || "?"} bölüm</span></div>`
          ).join("")}</div></div>`;
      }

      modalContent.innerHTML = `
        <div class="flex gap-5">
          ${posterSrc ? `<div class="hidden sm:block shrink-0 w-36"><img src="${posterSrc}" alt="" class="w-full shadow-lg" /></div>` : ""}
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <span class="text-[10px] font-bold uppercase px-2 py-0.5 bg-zinc-800 text-zinc-300">${typeName}</span>
              <span class="text-[10px] font-bold uppercase px-2 py-0.5 ${statusColor}">${statusBadge}</span>
              ${genres.map(g => `<span class="text-[10px] px-1.5 py-0.5 bg-zinc-800/60 text-zinc-400">${g}</span>`).join("")}
            </div>
            <h2 class="text-xl font-bold text-white">${rec.title}</h2>
            ${rec.original_title && rec.original_title !== rec.title ? `<p class="text-xs text-zinc-500 mt-0.5">${rec.original_title}</p>` : ""}
            <div class="mt-3 flex items-center gap-3 text-xs text-zinc-400 flex-wrap">
              <span class="mono text-lg font-bold text-amber-400">★ ${rec.rating || "-"}<span class="text-zinc-600 text-xs"> / 10</span></span>
              ${rec.imdb_rating ? `<span class="bg-amber-400 text-zinc-950 px-1.5 py-0.5 text-[10px] font-bold">IMDb ${Number(rec.imdb_rating).toFixed(1)}</span>` : ""}
              ${rec.tmdb_rating ? `<span class="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 text-[10px] font-bold">TMDB ${Number(rec.tmdb_rating).toFixed(1)}</span>` : ""}
              ${rec.imdb_id ? `<a href="https://www.imdb.com/title/${rec.imdb_id}/" target="_blank" class="text-amber-400 hover:underline text-[11px]">IMDb ↗</a>` : ""}
              <span>${rec.release_year || "—"}</span>
              ${rec.runtime ? `<span>${rec.runtime} dk</span>` : ""}
            </div>
            ${rec.director ? `<div class="mt-2 text-xs text-zinc-400"><span class="text-zinc-500 font-medium">Yönetmen:</span> ${rec.director}</div>` : ""}
            ${rec.cast_members ? `<div class="mt-1 text-xs text-zinc-400"><span class="text-zinc-500 font-medium">Oyuncular:</span> ${rec.cast_members}</div>` : ""}
            <!-- Trailer Button -->
            <div class="mt-3">
              <button id="openTrailerBtn" class="border border-red-600/80 bg-red-600/20 text-red-300 hover:bg-red-600 hover:text-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition">
                ▶ Fragmanı İzle
              </button>
            </div>
          </div>
        </div>
        ${rec.overview ? `<div class="mt-4"><h4 class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1">Özet</h4><p class="text-sm text-zinc-300 leading-relaxed bg-zinc-800/30 p-3">${rec.overview}</p></div>` : ""}
        ${rec.note ? `<div class="mt-3"><h4 class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1">Kişisel Not</h4><p class="text-sm text-zinc-300 bg-zinc-800/30 p-3">${rec.note}</p></div>` : ""}
        <!-- Tags input -->
        <div class="mt-3">
          <label class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1 block">Özel Etiketler (Virgülle ayırın)</label>
          <input id="modalTagsInput" type="text" value="${tags.join(", ")}" placeholder="Örn: Favoriler, Oscar, Nolan, Maraton" class="w-full bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-xs text-zinc-200 outline-none" />
        </div>
        ${seasonsHtml}
        <div class="mt-5 pt-4 border-t border-zinc-800 flex flex-wrap items-center gap-2">
          <select id="modalStatusSelect" class="bg-zinc-800 border border-zinc-700 text-zinc-200 px-2 py-1.5 text-xs">
            ${Object.entries(STATUS_LABELS).filter(([k]) => k).map(([k, v]) => `<option value="${k}" ${rec.status === k ? "selected" : ""}>${v}</option>`).join("")}
          </select>
          <select id="modalRatingSelect" class="bg-zinc-800 border border-zinc-700 text-zinc-200 px-2 py-1.5 text-xs">
            <option value="">Puan yok</option>
            ${[1,2,3,4,5,6,7,8,9,10].map(n => `<option value="${n}" ${rec.rating === n ? "selected" : ""}>★ ${n}</option>`).join("")}
          </select>
          <button id="modalSaveBtn" class="bg-zinc-100 text-zinc-900 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider hover:bg-white transition">Kaydet</button>
          <button id="modalDeleteBtn" class="bg-red-900/60 text-red-200 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider hover:bg-red-800 transition ml-auto">Sil</button>
        </div>
        <div class="mt-3 flex items-center justify-between text-[10px] text-zinc-600">
          <span>ID: #${rec.id} | Eklenme: ${rec.created_at || "—"}</span>
          <span>Güncelleme: ${rec.updated_at || "—"}</span>
        </div>`;

      // Trailer handler
      $("openTrailerBtn")?.addEventListener("click", async () => {
        try {
          const tdata = await api("GET", `/api/records/${rec.id}/trailer`);
          if (trailerTitle) trailerTitle.textContent = `${rec.title} — Fragman`;
          if (trailerIframe) trailerIframe.src = tdata.trailer_url;
          showModal(trailerModal);
        } catch (e) {
          toast("Fragman bulunamadı: " + e.message, "error");
        }
      });

      // Save handler
      $("modalSaveBtn")?.addEventListener("click", async () => {
        const newStatus = $("modalStatusSelect")?.value;
        const ratingVal = $("modalRatingSelect")?.value;
        const tagsVal = $("modalTagsInput")?.value || "";
        const tagsArr = tagsVal.split(",").map(t => t.strip ? t.strip() : t.trim()).filter(Boolean);
        try {
          await api("PUT", `/api/records/${rec.id}`, {
            status: newStatus,
            rating: ratingVal ? parseInt(ratingVal) : null,
            tags: tagsArr,
          });
          toast("Kayıt güncellendi");
          hideModal(detailModal);
          fetchRecords();
          fetchSummary();
        } catch (e) { toast("Güncelleme hatası: " + e.message, "error"); }
      });

      // Delete handler
      $("modalDeleteBtn")?.addEventListener("click", async () => {
        if (!confirm(`"${rec.title}" kaydını silmek istediğinden emin misin?`)) return;
        try {
          await api("DELETE", `/api/records/${rec.id}`);
          toast("Kayıt silindi");
          hideModal(detailModal);
          fetchRecords();
          fetchSummary();
        } catch (e) { toast("Silme hatası: " + e.message, "error"); }
      });
    } catch (err) {
      modalContent.innerHTML = `<div class="p-6 text-center text-red-400">Detay yüklenemedi: ${err.message}</div>`;
    }
  }

  // ── Roulette ("Ne İzlesem?") ───────────────────────────
  rouletteButton?.addEventListener("click", async () => {
    try {
      const params = new URLSearchParams();
      if (state.kind && state.kind !== "all") params.set("kind", state.kind);
      // Pick random
      const rec = await api("GET", `/api/random?${params}`);
      toast(`🎲 Çıkan yapım: "${rec.title}"!`);
      openDetail(rec.id);
    } catch (err) {
      toast("Seçilecek film bulunamadı: " + err.message, "info");
    }
  });

  // ── Add Modal (IMDb + TMDB + Manual) ───────────────────
  function openAddModal() {
    if (!addModal || !addModalContent) return;
    addModalContent.innerHTML = `
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold text-white">Film / Dizi Ekle</h2>
        <button id="closeAddModal" class="text-zinc-400 hover:text-white text-xl font-bold p-1">&times;</button>
      </div>
      <div class="flex gap-1.5 mb-4">
        <button id="tabImdb" class="flex-1 py-2 text-xs font-semibold uppercase tracking-wider bg-zinc-100 text-zinc-900 transition">IMDb ile Ara</button>
        <button id="tabTmdb" class="flex-1 py-2 text-xs font-semibold uppercase tracking-wider bg-zinc-800 text-zinc-400 transition">TMDB ile Ara</button>
        <button id="tabManual" class="flex-1 py-2 text-xs font-semibold uppercase tracking-wider bg-zinc-800 text-zinc-400 transition">Manuel</button>
      </div>
      <div id="imdbPanel">
        <div class="mb-3">
          <input id="imdbSearchInput" type="text" placeholder="IMDb'de film veya dizi ara (örn: The Dark Knight, Fight Club)..." class="w-full bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder:text-zinc-500 outline-none focus:border-zinc-500" autofocus />
        </div>
        <div id="imdbResults" class="max-h-80 overflow-y-auto thin-scrollbar space-y-2"></div>
      </div>
      <div id="tmdbPanel" class="hidden">
        <div class="flex gap-2 mb-3">
          <input id="tmdbSearchInput" type="text" placeholder="TMDB'de Türkçe ara (örn: Yüzüklerin Efendisi, Başlangıç)..." class="flex-1 bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder:text-zinc-500 outline-none focus:border-zinc-500" />
          <select id="tmdbTypeSelect" class="bg-zinc-800 border border-zinc-700 px-2 py-2 text-xs text-zinc-300">
            <option value="multi">Tümü</option>
            <option value="movie">Film</option>
            <option value="series">Dizi</option>
          </select>
        </div>
        <div id="tmdbResults" class="max-h-80 overflow-y-auto thin-scrollbar space-y-2"></div>
      </div>
      <div id="manualPanel" class="hidden">
        <div class="grid gap-3">
          <input id="manualTitle" type="text" placeholder="Başlık *" class="bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder:text-zinc-500 outline-none focus:border-zinc-500" />
          <div class="grid grid-cols-2 gap-2">
            <select id="manualType" class="bg-zinc-800 border border-zinc-700 px-3 py-2 text-xs text-zinc-300">
              <option value="movie">Film</option>
              <option value="series">Dizi</option>
            </select>
            <label class="flex items-center gap-2 text-xs text-zinc-400">
              <input id="manualAnime" type="checkbox" class="accent-amber-400" /> Anime
            </label>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <input id="manualYear" type="number" placeholder="Yıl" class="bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder:text-zinc-500 outline-none" />
            <select id="manualRating" class="bg-zinc-800 border border-zinc-700 px-3 py-2 text-xs text-zinc-300">
              <option value="">Puan yok</option>
              ${[1,2,3,4,5,6,7,8,9,10].map(n => `<option value="${n}">★ ${n}</option>`).join("")}
            </select>
          </div>
          <select id="manualStatus" class="bg-zinc-800 border border-zinc-700 px-3 py-2 text-xs text-zinc-300">
            ${Object.entries(STATUS_LABELS).filter(([k]) => k).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}
          </select>
          <textarea id="manualNote" placeholder="Özet / Kişisel Not (isteğe bağlı)" rows="2" class="bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder:text-zinc-500 outline-none resize-none"></textarea>
          <button id="manualSubmit" class="bg-zinc-100 text-zinc-900 px-4 py-2 text-xs font-semibold uppercase tracking-wider hover:bg-white transition">Kaydet</button>
        </div>
      </div>`;

    showModal(addModal);

    const activateTab = (activeName) => {
      $("imdbPanel").classList.toggle("hidden", activeName !== "imdb");
      $("tmdbPanel").classList.toggle("hidden", activeName !== "tmdb");
      $("manualPanel").classList.toggle("hidden", activeName !== "manual");
      $("tabImdb").className = `flex-1 py-2 text-xs font-semibold uppercase tracking-wider transition ${activeName === "imdb" ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-400"}`;
      $("tabTmdb").className = `flex-1 py-2 text-xs font-semibold uppercase tracking-wider transition ${activeName === "tmdb" ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-400"}`;
      $("tabManual").className = `flex-1 py-2 text-xs font-semibold uppercase tracking-wider transition ${activeName === "manual" ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-400"}`;
    };

    $("tabImdb")?.addEventListener("click", () => activateTab("imdb"));
    $("tabTmdb")?.addEventListener("click", () => activateTab("tmdb"));
    $("tabManual")?.addEventListener("click", () => activateTab("manual"));

    $("closeAddModal")?.addEventListener("click", () => hideModal(addModal));

    let imdbTimeout = null;
    $("imdbSearchInput")?.addEventListener("input", (e) => {
      clearTimeout(imdbTimeout);
      imdbTimeout = setTimeout(() => searchImdb(e.target.value.trim()), 300);
    });

    let tmdbTimeout = null;
    $("tmdbSearchInput")?.addEventListener("input", (e) => {
      clearTimeout(tmdbTimeout);
      tmdbTimeout = setTimeout(() => searchTmdb(e.target.value.trim()), 300);
    });

    $("manualSubmit")?.addEventListener("click", submitManual);
  }

  async function searchImdb(query) {
    const resultsEl = $("imdbResults");
    if (!resultsEl || !query) { if (resultsEl) resultsEl.innerHTML = ""; return; }
    resultsEl.innerHTML = `<div class="text-center text-zinc-500 text-sm py-4 animate-pulse">IMDb'de aranıyor…</div>`;
    try {
      const data = await api("POST", "/api/imdb/search", { query });
      if (!data.results?.length) {
        resultsEl.innerHTML = `<div class="text-center text-zinc-500 text-sm py-4">Sonuç bulunamadı.</div>`;
        return;
      }
      resultsEl.innerHTML = data.results.map((r) => {
        const typeLabel = r.media_type === "series" ? "Dizi" : "Film";
        return `
          <div class="imdb-result flex gap-3 p-3 bg-zinc-800/60 hover:bg-zinc-800 transition border border-zinc-700/50" data-imdb-id="${r.imdb_id}" data-media-type="${r.media_type}" data-poster-url="${r.poster_url || ""}">
            ${r.poster_url ? `<img src="${r.poster_url}" alt="" class="w-12 h-18 object-cover shrink-0" loading="lazy" />` : `<div class="w-12 h-18 bg-zinc-700 shrink-0"></div>`}
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5">
                <span class="text-[9px] font-bold uppercase px-1.5 py-0.5 bg-zinc-700 text-zinc-300">${typeLabel}</span>
                <span class="text-[10px] text-zinc-400">${r.release_year || "—"}</span>
              </div>
              <h4 class="text-sm font-semibold text-white mt-1 truncate">${r.title}</h4>
              ${r.stars ? `<p class="text-[11px] text-zinc-400 mt-0.5 truncate">${r.stars}</p>` : ""}
            </div>
            <div class="flex flex-col gap-1.5 shrink-0 justify-center">
              <button class="import-imdb-btn bg-zinc-100 text-zinc-900 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider hover:bg-white transition" data-anime="false">+ Ekle</button>
              <button class="import-imdb-btn bg-zinc-700 text-zinc-200 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider hover:bg-zinc-600 transition" data-anime="true">+ Anime</button>
            </div>
          </div>`;
      }).join("");

      resultsEl.querySelectorAll(".import-imdb-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const row = btn.closest(".imdb-result");
          const imdbId = row.dataset.imdbId;
          const mediaType = row.dataset.mediaType;
          const posterUrl = row.dataset.posterUrl;
          const isAnime = btn.dataset.anime === "true";
          btn.textContent = "...";
          btn.disabled = true;
          try {
            const result = await api("POST", `/api/imdb/import/${imdbId}`, { media_type: mediaType, is_anime: isAnime, poster_url: posterUrl });
            if (result.already_exists) {
              toast("Bu kayıt zaten mevcut", "info");
            } else {
              toast(`"${result.title || "Kayıt"}" Türkçe özetle eklendi!`);
            }
            hideModal(addModal);
            fetchRecords();
            fetchSummary();
          } catch (err) {
            toast("Import hatası: " + err.message, "error");
            btn.textContent = "Hata";
          }
        });
      });
    } catch (err) {
      resultsEl.innerHTML = `<div class="text-center text-red-400 text-sm py-4">${err.message}</div>`;
    }
  }

  async function searchTmdb(query) {
    const resultsEl = $("tmdbResults");
    if (!resultsEl || !query) { if (resultsEl) resultsEl.innerHTML = ""; return; }
    resultsEl.innerHTML = `<div class="text-center text-zinc-500 text-sm py-4 animate-pulse">TMDB'de aranıyor…</div>`;
    try {
      const mediaType = $("tmdbTypeSelect")?.value || "multi";
      const data = await api("POST", "/api/tmdb/search", { query, media_type: mediaType });
      if (!data.results?.length) {
        resultsEl.innerHTML = `<div class="text-center text-zinc-500 text-sm py-4">Sonuç bulunamadı.</div>`;
        return;
      }
      resultsEl.innerHTML = data.results.map((r) => {
        const typeLabel = r.media_type === "movie" ? "Film" : "Dizi";
        return `
          <div class="tmdb-result flex gap-3 p-3 bg-zinc-800/60 hover:bg-zinc-800 transition border border-zinc-700/50" data-tmdb-id="${r.tmdb_id}" data-media-type="${r.media_type}">
            ${r.poster_preview ? `<img src="${r.poster_preview}" alt="" class="w-12 h-18 object-cover shrink-0" loading="lazy" />` : `<div class="w-12 h-18 bg-zinc-700 shrink-0"></div>`}
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1.5">
                <span class="text-[9px] font-bold uppercase px-1.5 py-0.5 bg-zinc-700 text-zinc-300">${typeLabel}</span>
                ${r.tmdb_rating ? `<span class="text-[10px] text-amber-400">★ ${Number(r.tmdb_rating).toFixed(1)}</span>` : ""}
              </div>
              <h4 class="text-sm font-semibold text-white mt-1 truncate">${r.title}</h4>
              ${r.original_title && r.original_title !== r.title ? `<p class="text-[10px] text-zinc-500 truncate">${r.original_title}</p>` : ""}
              <p class="text-[11px] text-zinc-400 mt-0.5">${r.release_year || "—"}</p>
            </div>
            <div class="flex flex-col gap-1.5 shrink-0 justify-center">
              <button class="import-tmdb-btn bg-zinc-100 text-zinc-900 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider hover:bg-white transition" data-anime="false">+ Ekle</button>
              <button class="import-tmdb-btn bg-zinc-700 text-zinc-200 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider hover:bg-zinc-600 transition" data-anime="true">+ Anime</button>
            </div>
          </div>`;
      }).join("");

      resultsEl.querySelectorAll(".import-tmdb-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const row = btn.closest(".tmdb-result");
          const tmdbId = parseInt(row.dataset.tmdbId);
          const mediaType = row.dataset.mediaType;
          const isAnime = btn.dataset.anime === "true";
          btn.textContent = "...";
          btn.disabled = true;
          try {
            const result = await api("POST", `/api/tmdb/import/${tmdbId}`, { media_type: mediaType, is_anime: isAnime });
            if (result.already_exists) {
              toast("Bu kayıt zaten mevcut", "info");
            } else {
              toast(`"${result.title || "Kayıt"}" eklendi!`);
            }
            hideModal(addModal);
            fetchRecords();
            fetchSummary();
          } catch (err) {
            toast("Import hatası: " + err.message, "error");
            btn.textContent = "Hata";
          }
        });
      });
    } catch (err) {
      resultsEl.innerHTML = `<div class="text-center text-red-400 text-sm py-4">${err.message}</div>`;
    }
  }

  async function submitManual() {
    const title = $("manualTitle")?.value.trim();
    if (!title) { toast("Başlık zorunludur", "error"); return; }
    const body = {
      title,
      media_type: $("manualType")?.value || "movie",
      is_anime: $("manualAnime")?.checked || false,
      release_year: $("manualYear")?.value ? parseInt($("manualYear").value) : null,
      rating: $("manualRating")?.value ? parseInt($("manualRating").value) : null,
      status: $("manualStatus")?.value || "planned",
      note: $("manualNote")?.value.trim() || null,
    };
    try {
      await api("POST", "/api/records", body);
      toast(`"${title}" eklendi!`);
      hideModal(addModal);
      fetchRecords();
      fetchSummary();
    } catch (err) { toast("Ekleme hatası: " + err.message, "error"); }
  }

  // ── Import / Export Modal Handlers ─────────────────────
  importExportBtn?.addEventListener("click", () => showModal(importExportModal));
  closeImportExportBtn?.addEventListener("click", () => hideModal(importExportModal));

  uploadCsvBtn?.addEventListener("click", async () => {
    const file = csvFileInput?.files?.[0];
    if (!file) {
      toast("Lütfen bir .csv dosyası seçin", "error");
      return;
    }
    uploadCsvBtn.textContent = "Yükleniyor…";
    uploadCsvBtn.disabled = true;
    try {
      const text = await file.text();
      const res = await fetch("/api/import/csv", {
        method: "POST",
        headers: { "Content-Type": "text/csv; charset=utf-8" },
        body: text,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Yükleme hatası");
      toast(`${data.imported || 0} film içe aktarıldı (${data.skipped || 0} atlandı)`);
      hideModal(importExportModal);
      fetchRecords();
      fetchSummary();
    } catch (err) {
      toast("CSV yükleme hatası: " + err.message, "error");
    } finally {
      uploadCsvBtn.textContent = "CSV'yi İçe Aktar";
      uploadCsvBtn.disabled = false;
    }
  });

  // ── Trailer Modal Handlers ─────────────────────────────
  closeTrailerBtn?.addEventListener("click", () => {
    if (trailerIframe) trailerIframe.src = "";
    hideModal(trailerModal);
  });

  // ── Modal Helpers ──────────────────────────────────────
  function showModal(el) { el.classList.remove("hidden"); el.classList.add("flex"); }
  function hideModal(el) { el.classList.add("hidden"); el.classList.remove("flex"); }

  function updatePagination() {
    const cur = Math.floor(state.offset / state.limit) + 1;
    const tot = Math.max(1, Math.ceil(state.total / state.limit));
    if (pageLine) pageLine.textContent = `${cur} / ${tot}`;
    if (prevButton) prevButton.disabled = state.offset <= 0;
    if (nextButton) nextButton.disabled = state.offset + state.limit >= state.total;
  }

  function setLoading(v) {
    if (recordsPanel) recordsPanel.setAttribute("aria-busy", v ? "true" : "false");
    if (loadingState) loadingState.classList.toggle("hidden", !v);
  }

  function setError(msg) {
    if (!errorState) return;
    if (msg) { errorState.textContent = msg; errorState.classList.remove("hidden"); }
    else errorState.classList.add("hidden");
  }

  // ── Events ─────────────────────────────────────────────
  refreshButton?.addEventListener("click", () => { fetchSummary(); fetchRecords(); });
  addButton?.addEventListener("click", openAddModal);
  searchInput?.addEventListener("input", (e) => { clearTimeout(searchTimeout); searchTimeout = setTimeout(() => { state.query = e.target.value.trim(); state.offset = 0; fetchRecords(); }, 300); });
  sortSelect?.addEventListener("change", (e) => { state.sort = e.target.value; state.offset = 0; fetchRecords(); });
  directionButton?.addEventListener("click", () => { state.dir = state.dir === "desc" ? "asc" : "desc"; directionButton.textContent = state.dir === "desc" ? "Azalan ↓" : "Artan ↑"; state.offset = 0; fetchRecords(); });
  pageSizeSelect?.addEventListener("change", (e) => { state.limit = parseInt(e.target.value) || 50; state.offset = 0; fetchRecords(); });
  prevButton?.addEventListener("click", () => { if (state.offset > 0) { state.offset = Math.max(0, state.offset - state.limit); fetchRecords(); } });
  nextButton?.addEventListener("click", () => { if (state.offset + state.limit < state.total) { state.offset += state.limit; fetchRecords(); } });

  [detailModal, addModal, trailerModal, importExportModal].forEach((m) => {
    if (!m) return;
    m.addEventListener("click", (e) => {
      if (e.target === m) {
        if (m === trailerModal && trailerIframe) trailerIframe.src = "";
        hideModal(m);
      }
    });
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      [detailModal, addModal, trailerModal, importExportModal].forEach((m) => {
        if (m && !m.classList.contains("hidden")) {
          if (m === trailerModal && trailerIframe) trailerIframe.src = "";
          hideModal(m);
        }
      });
    }
  });

  // ── Init ───────────────────────────────────────────────
  initTheme();
  fetchSummary();
  fetchRecords();
})();
