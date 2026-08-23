/**
 * Media Tracker Gallery Client JavaScript
 */
(() => {
  "use strict";

  const state = {
    kind: "all",
    status: "",
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

  // DOM Elements
  const dbLine = document.getElementById("dbLine");
  const refreshButton = document.getElementById("refreshButton");
  const jsonLink = document.getElementById("jsonLink");
  const statTotal = document.getElementById("statTotal");
  const statRating = document.getElementById("statRating");
  const statRatedCount = document.getElementById("statRatedCount");
  const statCompleted = document.getElementById("statCompleted");
  const statInProgress = document.getElementById("statInProgress");
  const ratingChart = document.getElementById("ratingChart");
  const kindTabs = document.getElementById("kindTabs");
  const statusTabs = document.getElementById("statusTabs");
  const searchInput = document.getElementById("searchInput");
  const sortSelect = document.getElementById("sortSelect");
  const directionButton = document.getElementById("directionButton");
  const pageSizeSelect = document.getElementById("pageSizeSelect");
  const resultLine = document.getElementById("resultLine");
  const prevButton = document.getElementById("prevButton");
  const nextButton = document.getElementById("nextButton");
  const pageLine = document.getElementById("pageLine");
  const recordsPanel = document.getElementById("recordsPanel");
  const loadingState = document.getElementById("loadingState");
  const errorState = document.getElementById("errorState");
  const emptyState = document.getElementById("emptyState");
  const posterGrid = document.getElementById("posterGrid");
  const detailModal = document.getElementById("detailModal");
  const modalContent = document.getElementById("modalContent");
  const closeModalBtn = document.getElementById("closeModalBtn");

  let searchTimeout = null;

  async function fetchSummary() {
    try {
      const res = await fetch("/api/summary");
      if (!res.ok) throw new Error(`Summary API HTTP ${res.status}`);
      const data = await res.json();
      state.summary = data;
      renderSummary(data);
    } catch (err) {
      console.error("Summary fetch error:", err);
    }
  }

  function renderSummary(data) {
    if (dbLine) {
      dbLine.textContent = `SQLite: ${data.db_path || "media.sqlite"} — Şema v${data.schema_version || 2} — ${data.posters?.total_files || 0} poster yüklü`;
    }
    if (statTotal) statTotal.textContent = (data.counts?.all || 0).toLocaleString("tr-TR");
    if (statRating) {
      statRating.textContent = data.avg_rating ? Number(data.avg_rating).toFixed(1) : "-";
    }
    if (statRatedCount) {
      statRatedCount.textContent = `${(data.rating_count || 0).toLocaleString("tr-TR")} kayıt puanlandı`;
    }
    if (statCompleted) {
      statCompleted.textContent = (data.status_counts?.completed || 0).toLocaleString("tr-TR");
    }
    if (statInProgress) {
      statInProgress.textContent = (data.status_counts?.in_progress || 0).toLocaleString("tr-TR");
    }

    renderRatingChart(data.rating_buckets || []);
    renderKindTabs(data.counts || {});
    renderStatusTabs(data.status_counts || {});
  }

  function renderRatingChart(buckets) {
    if (!ratingChart) return;
    ratingChart.innerHTML = "";
    const counts = buckets.slice(1, 11); // ratings 1 to 10
    const max = Math.max(1, ...counts);

    counts.forEach((count, idx) => {
      const rating = idx + 1;
      const heightPercent = Math.max(8, (count / max) * 100);
      const col = document.createElement("div");
      col.className = "flex-1 flex flex-col items-center gap-1 group relative cursor-pointer";
      col.title = `${rating} Puan: ${count} kayıt`;

      col.innerHTML = `
        <div class="w-full bg-zinc-100 hover:bg-amber-400 transition flex items-end justify-center" style="height: 60px;">
          <div class="w-full bg-zinc-800 group-hover:bg-amber-500 transition-all duration-300" style="height: ${heightPercent}%;"></div>
        </div>
        <span class="mono text-[10px] text-zinc-500 font-semibold">${rating}</span>
      `;
      ratingChart.appendChild(col);
    });
  }

  function renderKindTabs(counts) {
    if (!kindTabs) return;
    kindTabs.innerHTML = "";

    const kinds = ["all", "movie", "anime-movie", "series", "anime-series", "anime"];
    kinds.forEach((k) => {
      const active = state.kind === k;
      const count = counts[k] ?? 0;
      const btn = document.createElement("button");
      btn.className = `flex items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wider transition ${
        active ? "bg-zinc-950 text-white shadow-xs" : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
      }`;
      btn.innerHTML = `
        <span>${KIND_LABELS[k] || k}</span>
        <span class="mono px-1.5 py-0.5 text-[10px] ${active ? "bg-zinc-800 text-zinc-300" : "bg-zinc-200 text-zinc-600"}">${count}</span>
      `;
      btn.addEventListener("click", () => {
        state.kind = k;
        state.offset = 0;
        fetchRecords();
        fetchSummary();
      });
      kindTabs.appendChild(btn);
    });
  }

  function renderStatusTabs(statusCounts) {
    if (!statusTabs) return;
    statusTabs.innerHTML = "";

    const statuses = ["", "completed", "in_progress", "planned", "paused", "dropped"];
    statuses.forEach((st) => {
      const active = state.status === st;
      const count = st === "" ? (state.summary?.counts?.all || 0) : (statusCounts[st] ?? 0);
      const btn = document.createElement("button");
      btn.className = `flex items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wider transition ${
        active ? "bg-zinc-950 text-white shadow-xs" : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
      }`;
      btn.innerHTML = `
        <span>${STATUS_LABELS[st] || st}</span>
        <span class="mono px-1.5 py-0.5 text-[10px] ${active ? "bg-zinc-800 text-zinc-300" : "bg-zinc-200 text-zinc-600"}">${count}</span>
      `;
      btn.addEventListener("click", () => {
        state.status = st;
        state.offset = 0;
        fetchRecords();
      });
      statusTabs.appendChild(btn);
    });
  }

  async function fetchRecords() {
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      kind: state.kind,
      status: state.status,
      q: state.query,
      sort: state.sort,
      dir: state.dir,
      limit: state.limit.toString(),
      offset: state.offset.toString(),
    });

    const url = `/api/records?${params.toString()}`;
    if (jsonLink) jsonLink.href = url;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      state.total = data.total || 0;
      renderRecords(data.records || []);
      updatePagination();
    } catch (err) {
      console.error("Records error:", err);
      setError("Kayıtlar yüklenirken bir hata oluştu: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  function renderRecords(records) {
    if (!posterGrid) return;
    posterGrid.innerHTML = "";

    if (records.length === 0) {
      emptyState.classList.remove("hidden");
      posterGrid.classList.add("hidden");
      resultLine.textContent = "0 kayıt bulundu";
      return;
    }

    emptyState.classList.add("hidden");
    posterGrid.classList.remove("hidden");
    resultLine.textContent = `${state.total.toLocaleString("tr-TR")} kayıt bulundu (Gösterilen: ${state.offset + 1}–${Math.min(
      state.offset + records.length,
      state.total
    )})`;

    records.forEach((rec) => {
      const card = createPosterCard(rec);
      posterGrid.appendChild(card);
    });
  }

  function createPosterCard(rec) {
    const card = document.createElement("div");
    card.className = "poster-card group focus-visible:ring-2 focus-visible:ring-zinc-950";
    card.tabIndex = 0;

    const kindBadge = rec.is_anime
      ? (rec.media_type === "movie" ? "Anime Film" : "Anime Dizi")
      : (rec.media_type === "movie" ? "Film" : "Dizi");

    const statusBadge = STATUS_LABELS[rec.status] || rec.status;
    const statusColor = STATUS_COLORS[rec.status] || "bg-zinc-700 text-white";

    if (rec.poster_url) {
      card.innerHTML = `
        <img src="${rec.poster_url}" alt="${rec.title}" loading="lazy" />
        <div class="poster-overlay">
          <span class="inline-block self-start text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 mb-1 ${statusColor}">${statusBadge}</span>
          <h3 class="text-sm font-bold leading-tight line-clamp-2">${rec.title}</h3>
          <div class="mt-1 flex items-center justify-between text-xs text-zinc-300">
            <span>${rec.release_year || "—"}</span>
            <span class="mono font-semibold text-amber-400">★ ${rec.rating ? rec.rating + "/10" : "—"}</span>
          </div>
        </div>
      `;
    } else {
      // Elegant minimal poster card when image is not present
      const initials = rec.title
        .split(" ")
        .map((w) => w[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();

      card.innerHTML = `
        <div class="w-full h-full p-4 flex flex-col justify-between bg-gradient-to-b from-zinc-900 via-zinc-900 to-zinc-950 text-white select-none">
          <div class="flex items-start justify-between gap-1">
            <span class="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 bg-zinc-800 text-zinc-300">${kindBadge}</span>
            <span class="mono text-xs font-bold text-amber-400">★ ${rec.rating || "—"}</span>
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
          <p class="text-xs text-zinc-300 mt-1 line-clamp-3">${rec.note || "Not eklenmemiş."}</p>
          <div class="mt-2 flex items-center justify-between text-xs text-zinc-400">
            <span>${rec.release_year || "—"}</span>
            <span class="mono font-semibold text-amber-400">★ ${rec.rating ? rec.rating + "/10" : "Puan Yok"}</span>
          </div>
        </div>
      `;
    }

    card.addEventListener("click", () => openDetail(rec.id));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openDetail(rec.id);
      }
    });

    return card;
  }

  async function openDetail(mediaId) {
    if (!detailModal || !modalContent) return;
    modalContent.innerHTML = `<div class="p-8 text-center text-zinc-400 animate-pulse">Kayıt detayları yükleniyor…</div>`;
    detailModal.classList.remove("hidden");
    detailModal.classList.add("flex");

    try {
      const res = await fetch(`/api/records/${mediaId}`);
      if (!res.ok) throw new Error("Detay alınamadı");
      const rec = await res.json();

      const typeName = rec.is_anime
        ? (rec.media_type === "movie" ? "Anime Film" : "Anime Dizi")
        : (rec.media_type === "movie" ? "Film" : "Dizi");

      const statusBadge = STATUS_LABELS[rec.status] || rec.status;
      const statusColor = STATUS_COLORS[rec.status] || "bg-zinc-700 text-white";

      let seasonsHtml = "";
      if (rec.seasons && rec.seasons.length > 0) {
        seasonsHtml = `
          <div class="mt-4 pt-4 border-t border-zinc-800">
            <h4 class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-2">Sezon ve Bölüm Takibi</h4>
            <div class="grid gap-2">
              ${rec.seasons
                .map(
                  (s) => `
                <div class="flex items-center justify-between text-xs bg-zinc-800/60 px-3 py-2">
                  <span>${s.season_number}. Sezon</span>
                  <span class="mono text-zinc-300">${s.watched_episodes} / ${s.episode_count || "?"} bölüm</span>
                </div>
              `
                )
                .join("")}
            </div>
          </div>
        `;
      }

      modalContent.innerHTML = `
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[10px] font-bold uppercase px-2 py-0.5 bg-zinc-800 text-zinc-300">${typeName}</span>
              <span class="text-[10px] font-bold uppercase px-2 py-0.5 ${statusColor}">${statusBadge}</span>
            </div>
            <h2 class="text-xl font-bold text-white">${rec.title}</h2>
          </div>
          <div class="text-right">
            <div class="mono text-2xl font-bold text-amber-400">★ ${rec.rating || "-"}</div>
            <div class="text-[10px] text-zinc-400 uppercase tracking-wider">/ 10 Puan</div>
          </div>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-3 text-xs bg-zinc-800/40 p-3">
          <div>
            <span class="text-zinc-500">Yayın Yılı:</span>
            <span class="font-semibold text-zinc-200 ml-1">${rec.release_year || "Belirtilmemiş"}</span>
          </div>
          <div>
            <span class="text-zinc-500">Kayıt ID:</span>
            <span class="mono text-zinc-200 ml-1">#${rec.id}</span>
          </div>
        </div>

        ${
          rec.note
            ? `<div class="mt-4"><h4 class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1">Not / İnceleme</h4><p class="text-sm text-zinc-300 leading-relaxed bg-zinc-800/30 p-3">${rec.note}</p></div>`
            : ""
        }

        ${seasonsHtml}

        <div class="mt-6 flex items-center justify-between text-[11px] text-zinc-500 pt-3 border-t border-zinc-800">
          <span>Eklenme: ${rec.created_at || "—"}</span>
          <span>Güncelleme: ${rec.updated_at || "—"}</span>
        </div>
      `;
    } catch (err) {
      modalContent.innerHTML = `<div class="p-6 text-center text-red-400">Detay yüklenemedi: ${err.message}</div>`;
    }
  }

  function updatePagination() {
    const currentPage = Math.floor(state.offset / state.limit) + 1;
    const totalPages = Math.max(1, Math.ceil(state.total / state.limit));

    if (pageLine) pageLine.textContent = `${currentPage} / ${totalPages}`;
    if (prevButton) prevButton.disabled = state.offset <= 0;
    if (nextButton) nextButton.disabled = state.offset + state.limit >= state.total;
  }

  function setLoading(loading) {
    if (recordsPanel) recordsPanel.setAttribute("aria-busy", loading ? "true" : "false");
    if (loadingState) loadingState.classList.toggle("hidden", !loading);
  }

  function setError(msg) {
    if (!errorState) return;
    if (msg) {
      errorState.textContent = msg;
      errorState.classList.remove("hidden");
    } else {
      errorState.classList.add("hidden");
    }
  }

  // Setup Event Listeners
  if (refreshButton) {
    refreshButton.addEventListener("click", () => {
      fetchSummary();
      fetchRecords();
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        state.query = e.target.value.trim();
        state.offset = 0;
        fetchRecords();
      }, 300);
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener("change", (e) => {
      state.sort = e.target.value;
      state.offset = 0;
      fetchRecords();
    });
  }

  if (directionButton) {
    directionButton.addEventListener("click", () => {
      state.dir = state.dir === "desc" ? "asc" : "desc";
      directionButton.textContent = state.dir === "desc" ? "Azalan ↓" : "Artan ↑";
      state.offset = 0;
      fetchRecords();
    });
  }

  if (pageSizeSelect) {
    pageSizeSelect.addEventListener("change", (e) => {
      state.limit = parseInt(e.target.value, 10) || 50;
      state.offset = 0;
      fetchRecords();
    });
  }

  if (prevButton) {
    prevButton.addEventListener("click", () => {
      if (state.offset > 0) {
        state.offset = Math.max(0, state.offset - state.limit);
        fetchRecords();
      }
    });
  }

  if (nextButton) {
    nextButton.addEventListener("click", () => {
      if (state.offset + state.limit < state.total) {
        state.offset += state.limit;
        fetchRecords();
      }
    });
  }

  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", () => {
      detailModal.classList.add("hidden");
      detailModal.classList.remove("flex");
    });
  }

  if (detailModal) {
    detailModal.addEventListener("click", (e) => {
      if (e.target === detailModal) {
        detailModal.classList.add("hidden");
        detailModal.classList.remove("flex");
      }
    });
  }

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && detailModal && !detailModal.classList.contains("hidden")) {
      detailModal.classList.add("hidden");
      detailModal.classList.remove("flex");
    }
  });

  // Initial Load
  fetchSummary();
  fetchRecords();
})();
