
const _originalGetElementById = document.getElementById.bind(document);
document.getElementById = function(id) {
    const el = _originalGetElementById(id);
    if (el) return el;
    // Return a dummy element to prevent crashes
    return {
        addEventListener: function(){},
        classList: { add: function(){}, remove: function(){}, toggle: function(){} },
        style: {},
        setAttribute: function(){},
        innerHTML: '',
        innerText: '',
        textContent: '',
        value: ''
    };
};
/**
 * Media Tracker Gallery Client JavaScript v6.0
 * Comprehensive Analytics & 1-Month History, Format Distributions, Rate Metrics, Multi-Source Discovery Roulette.
 */
(() => {
  "use strict";

  const state = {
    view: "gallery", // 'gallery' | 'stats'
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
    rouletteSource: "tmdb",
    currentRouletteItem: null,
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

  // Views & Navigation
  const galleryView = $("galleryView");
  const statsView = $("statsView");
  const navGalleryBtn = $("navGalleryBtn");
  const navStatsBtn = $("navStatsBtn");
  const backToGalleryBtn = $("backToGalleryBtn");
  const statWatchTimeCard = $("statWatchTimeCard");

  // Header & Controls
  const dbLine = $("dbLine");
  const refreshButton = $("refreshButton");
  const addButton = $("addButton");
  const rouletteButton = $("rouletteButton");
  const importExportBtn = $("importExportBtn");
  const themeToggle = $("themeToggle");
  const jsonLink = $("jsonLink");

  // Quick Stats
  const statTotal = $("statTotal");
  const statRating = $("statRating");
  const statRatedCount = $("statRatedCount");
  const statCompleted = $("statCompleted");
  const statInProgress = $("statInProgress");
  const statWatchHours = $("statWatchHours");
  const statWatchDays = $("statWatchDays");

  // Dedicated Analytics Page Elements
  const stat30DaysCount = $("stat30DaysCount");
  const stat30DaysHours = $("stat30DaysHours");
  const stat30DaysGallery = $("stat30DaysGallery");
  const statPageHours = $("statPageHours");
  const statPageDays = $("statPageDays");
  const statCompletionRate = $("statCompletionRate");
  const statCompletionDetail = $("statCompletionDetail");
  const statAvgRuntime = $("statAvgRuntime");
  const statLongestMovie = $("statLongestMovie");
  const statPageAvgRating = $("statPageAvgRating");
  const statRatedPercent = $("statRatedPercent");

  const barMovie = $("barMovie");
  const barSeries = $("barSeries");
  const barAnime = $("barAnime");
  const statMoviePercent = $("statMoviePercent");
  const statMovieCount = $("statMovieCount");
  const statSeriesPercent = $("statSeriesPercent");
  const statSeriesCount = $("statSeriesCount");
  const statAnimePercent = $("statAnimePercent");
  const statAnimeCount = $("statAnimeCount");

  const ratingTiersList = $("ratingTiersList");
  const statsGenresList = $("statsGenresList");
  const statsDirectorsList = $("statsDirectorsList");
  const statsCastList = $("statsCastList");
  const statsDecadesList = $("statsDecadesList");
  const statsTopRatedList = $("statsTopRatedList");

  // Filters & List
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

  // Modals
  const detailModal = $("detailModal");
  const modalContent = $("modalContent");
  const addModal = $("addModal");
  const addModalContent = $("addModalContent");
  const rouletteModal = $("rouletteModal");
  const closeRouletteModal = $("closeRouletteModal");
  const rouletteSourceTmdb = $("rouletteSourceTmdb");
  const rouletteSourceImdb = $("rouletteSourceImdb");
  const rouletteSourceArchive = $("rouletteSourceArchive");
  const rouletteCard = $("rouletteCard");
  const spinAgainBtn = $("spinAgainBtn");
  const rouletteActionBtn = $("rouletteActionBtn");

  const trailerModal = $("trailerModal");
  const trailerTitle = $("trailerTitle");
  const trailerIframe = $("trailerIframe");
  const closeTrailerBtn = $("closeTrailerBtn");
  const importExportModal = $("importExportModal");
  const closeImportExportBtn = $("closeImportExportBtn");
  const csvFileInput = $("csvFileInput");
  const uploadCsvBtn = $("uploadCsvBtn");

  let searchTimeout = null;

  // ── Navigation & Views ─────────────────────────────────
  function switchView(viewName) {
    state.view = viewName;
    const isGallery = viewName === "gallery";
    galleryView?.classList.toggle("hidden", !isGallery);
    statsView?.classList.toggle("hidden", isGallery);

    if (navGalleryBtn) navGalleryBtn.className = `px-3 py-1 text-xs font-bold uppercase tracking-wider transition ${isGallery ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950" : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-white"}`;
    if (navStatsBtn) navStatsBtn.className = `px-3 py-1 text-xs font-bold uppercase tracking-wider transition ${!isGallery ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950" : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-white"}`;

    const mobGal = $("mobileNavGallery");
    const mobStat = $("mobileNavStats");
    if (mobGal) {
      mobGal.className = `flex flex-col items-center justify-center h-full transition active:scale-95 ${isGallery ? "text-zinc-950 dark:text-white font-bold" : "text-zinc-500 dark:text-zinc-400 font-normal"}`;
    }
    if (mobStat) {
      mobStat.className = `flex flex-col items-center justify-center h-full transition active:scale-95 ${!isGallery ? "text-zinc-950 dark:text-white font-bold" : "text-zinc-500 dark:text-zinc-400 font-normal"}`;
    }

    if (!isGallery) {
      renderStatsPage();
      window.location.hash = "analytics";
    } else {
      window.location.hash = "";
    }
  }

  const copyReportBtn = $("copyReportBtn");

  navGalleryBtn?.addEventListener("click", () => switchView("gallery"));
  navStatsBtn?.addEventListener("click", () => switchView("stats"));
  backToGalleryBtn?.addEventListener("click", () => switchView("gallery"));
  statWatchTimeCard?.addEventListener("click", () => switchView("stats"));

  copyReportBtn?.addEventListener("click", () => {
    const data = state.summary;
    if (!data) return;
    const stats = data.stats || {};
    const wt = stats.watch_time || {};
    const l30 = stats.last_30_days || {};
    const topG = (stats.top_genres || []).slice(0, 3).map(g => `${g.name} (%${g.percent})`).join(", ");

    const text = `🎬 **Media Tracker — İzleme Raporum**\n` +
      `📅 **Son 30 Gün (1 Ay):** ${l30.count || 0} yapım, ${l30.hours || 0} saat\n` +
      `⏱️ **Toplam Süre:** ${wt.total_hours || 0} saat (${wt.total_days || 0} gün)\n` +
      `⭐ **Ortalama Puan:** ${data.avg_rating ? Number(data.avg_rating).toFixed(1) : "-"} / 10\n` +
      `🎭 **En Çok İzlenen Türler:** ${topG || "Yok"}\n` +
      `📊 **Tamamlama Oranı:** %${stats.rates?.completion_rate || 0}\n\n` +
      `#MediaTracker #Sinema #FilmArsivi`;

    navigator.clipboard.writeText(text).then(() => {
      toast("📋 İzleme raporu panoya kopyalandı!");
    }).catch(() => {
      toast("Kopyalama başarısız oldu", "error");
    });
  });

  // ── Dark / Light Theme ─────────────────────────────────
  function initTheme() {
    const saved = localStorage.getItem("theme");
    const isDark = saved ? saved === "dark" : true;
    applyTheme(isDark);
  }

  function applyTheme(isDark) {
    document.documentElement.classList.toggle("dark", isDark);
    if (themeToggle) themeToggle.textContent = isDark ? "🌙" : "☀️";
    const mobTheme = $("mobileThemeToggle");
    if (mobTheme) mobTheme.textContent = isDark ? "🌙" : "☀️";
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

  function highlightMatch(text, query) {
    if (!text) return "";
    if (!query || !query.trim()) return text;
    const q = query.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(${q})`, "gi");
    return text.replace(regex, `<mark class="bg-amber-400/40 text-amber-200 px-0.5 rounded-xs">$1</mark>`);
  }

  // ── Summary & Stats ────────────────────────────────────
  async function fetchSummary() {
    try {
      const data = await api("GET", "/api/summary");
      state.summary = data;
      renderSummary(data);
      if (state.view === "stats") renderStatsPage();
    } catch (err) {
      console.error("Summary fetch error:", err);
    }
  }

  function renderSummary(data) {
    if (dbLine) {
      const posters = data.posters?.total_files || 0;
      dbLine.textContent = `SQLite — ${posters} poster yüklü — IMDb & TMDB Türkçe Aktif ✓`;
    }
    const footerStatsLine = $("footerStatsLine");
    if (footerStatsLine) {
      const totalCount = data.counts?.all || 0;
      const hours = data.stats?.watch_time?.total_hours || 0;
      const avg = data.avg_rating ? Number(data.avg_rating).toFixed(1) : "-";
      footerStatsLine.textContent = `${totalCount} Yapım • ${hours} Saat İzleme • ★ ${avg} Ortalama Puan`;
    }
    if (statTotal) statTotal.textContent = (data.counts?.all || 0).toLocaleString("tr-TR");
    if (statRating) statRating.textContent = data.avg_rating ? Number(data.avg_rating).toFixed(1) : "-";
    if (statRatedCount) statRatedCount.textContent = `${(data.rating_count || 0).toLocaleString("tr-TR")} kayıt puanlandı`;
    if (statCompleted) statCompleted.textContent = (data.status_counts?.completed || 0).toLocaleString("tr-TR");
    if (statInProgress) statInProgress.textContent = (data.status_counts?.in_progress || 0).toLocaleString("tr-TR");

    // Watch time in header
    const wt = data.stats?.watch_time;
    if (statWatchHours) statWatchHours.textContent = wt?.total_hours || 0;
    if (statWatchDays) statWatchDays.textContent = `${wt?.total_days || 0} güne eşdeğer`;

    renderRatingChart(data.rating_buckets || []);
    renderKindTabs(data.counts || {});
    renderStatusTabs(data.status_counts || {});
    renderTags(data.stats?.tags || []);

  }

  // ── Render Full Analytics Page ─────────────────────────
  function renderStatsPage() {
    const data = state.summary;
    if (!data) return;
    const stats = data.stats || {};
    const wt = stats.watch_time || {};
    const last30 = stats.last_30_days || {};
    const rates = stats.rates || {};
    const runtime = stats.runtime_analysis || {};
    const tiers = stats.rating_tiers || {};

    // 1. Last 30 Days (1 Month)
    if (stat30DaysCount) stat30DaysCount.textContent = `${last30.count || 0} yapım`;
    if (stat30DaysHours) stat30DaysHours.textContent = `${last30.hours || 0} saat`;
    if (stat30DaysGallery) {
      const items = last30.items || [];
      if (!items.length) {
        stat30DaysGallery.innerHTML = `<p class="text-xs text-zinc-500 py-2">Son 30 gün içinde tamamlanan yapım bulunamadı.</p>`;
      } else {
        stat30DaysGallery.innerHTML = items.map(it => {
          const posterSrc = it.poster_path ? (it.poster_path.startsWith("/") ? `/static/posters/${it.id}.jpg` : it.poster_path) : null;
          return `
            <div class="shrink-0 w-24 poster-card cursor-pointer" onclick="window.__openDetail(${it.id})" title="${it.title}">
              ${posterSrc ? `<img src="${posterSrc}" alt="${it.title}" loading="lazy" class="w-full h-full object-cover" />` : `<div class="w-full h-full bg-zinc-800 p-2 text-[10px] text-white flex items-center justify-center text-center">${it.title}</div>`}
              <div class="poster-overlay">
                <p class="text-[10px] font-bold truncate">${it.title}</p>
                <span class="mono text-[9px] text-amber-400 font-bold">★ ${it.rating || it.imdb_rating || "—"}</span>
              </div>
            </div>`;
        }).join("");
      }
    }

    // 1b. Monthly Goal Tracker
    const goalTarget = 10;
    const goalDone = last30.count || 0;
    const goalPct = Math.min(100, Math.round((goalDone / goalTarget) * 100));
    const goalDoneEl = $("monthlyGoalDone");
    const goalBadgeEl = $("monthlyGoalBadge");
    const goalBarEl = $("monthlyGoalBar");
    if (goalDoneEl) goalDoneEl.textContent = goalDone;
    if (goalBadgeEl) goalBadgeEl.textContent = `%${goalPct}`;
    if (goalBarEl) goalBarEl.style.width = `${goalPct}%`;

    // 2. Overview Metrics & Rates
    if (statPageHours) statPageHours.textContent = wt.total_hours || 0;
    if (statPageDays) statPageDays.textContent = `${wt.total_days || 0} güne eşdeğer`;
    if (statCompletionRate) statCompletionRate.textContent = `${rates.completion_rate || 0}%`;
    if (statCompletionDetail) statCompletionDetail.textContent = `${rates.completed_records || 0}/${rates.total_records || 0} yapım tamamlandı`;
    if (statAvgRuntime) statAvgRuntime.textContent = runtime.avg_movie_runtime || 115;
    if (statLongestMovie) {
      statLongestMovie.textContent = runtime.longest_movie ? `En uzun: ${runtime.longest_movie.title} (${runtime.longest_movie.runtime} dk)` : "—";
    }
    if (statPageAvgRating) statPageAvgRating.textContent = data.avg_rating ? Number(data.avg_rating).toFixed(1) : "-";
    if (statRatedPercent) {
      const ratedPct = rates.total_records > 0 ? Math.round((data.rating_count / rates.total_records) * 100) : 0;
      statRatedPercent.textContent = `%${ratedPct} (${data.rating_count || 0} yapım) puanlandı`;
    }

    // 2.5. Sinema İzleme Günlüğü (Watch Diary)
    const statsDiaryList = $("statsDiaryList");
    const diary = stats.diary || [];
    if (statsDiaryList) {
      if (!diary.length) {
        statsDiaryList.innerHTML = `<p class="text-xs text-zinc-500 py-2">Henüz tamamlanan veya izleme tarihi girilen yapım yok.</p>`;
      } else {
        statsDiaryList.innerHTML = diary.map(d => {
          const posterSrc = d.poster_path ? (d.poster_path.startsWith("/") ? `/static/posters/${d.id}.jpg` : d.poster_path) : null;
          const rewatchBadge = d.times_watched && d.times_watched > 1 ? `<span class="text-[9px] font-bold px-1 py-0.2 bg-zinc-800 text-purple-300 ml-1">🔁 ${d.times_watched}x</span>` : "";
          return `
            <div class="flex items-center justify-between p-2.5 bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800/80 transition cursor-pointer" onclick="window.__openDetail(${d.id})">
              <div class="flex items-center gap-3 min-w-0">
                ${posterSrc ? `<img src="${posterSrc}" alt="" class="w-7 aspect-[2/3] object-cover shrink-0 shadow-xs" />` : `<div class="w-7 aspect-[2/3] bg-zinc-800 shrink-0"></div>`}
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5">
                    <p class="font-bold text-zinc-900 dark:text-zinc-100 text-xs truncate">${d.title}</p>
                    <span class="text-[10px] text-zinc-500 shrink-0">(${d.release_year || "—"})</span>
                    ${rewatchBadge}
                  </div>
                  <p class="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5 truncate">${d.director ? `Yön: ${d.director}` : (d.media_type === "movie" ? "Film" : "Dizi")}</p>
                </div>
              </div>
              <div class="flex items-center gap-3 shrink-0 ml-2">
                <span class="mono text-xs font-bold text-amber-400">★ ${d.rating || d.imdb_rating || "—"}</span>
                <span class="mono text-[10px] text-zinc-400 dark:text-zinc-500">${d.watched_at || "Kayıtlı"}</span>
              </div>
            </div>`;
        }).join("");
      }
    }

    // 3. Format Distributions
    if (barMovie) barMovie.style.width = `${rates.movie_percent || 0}%`;
    if (barSeries) barSeries.style.width = `${rates.series_percent || 0}%`;
    if (barAnime) barAnime.style.width = `${rates.anime_percent || 0}%`;
    if (statMoviePercent) statMoviePercent.textContent = `${rates.movie_percent || 0}%`;
    if (statMovieCount) statMovieCount.textContent = `${rates.movie_count || 0} adet`;
    if (statSeriesPercent) statSeriesPercent.textContent = `${rates.series_percent || 0}%`;
    if (statSeriesCount) statSeriesCount.textContent = `${rates.series_count || 0} adet`;
    if (statAnimePercent) statAnimePercent.textContent = `${rates.anime_percent || 0}%`;
    if (statAnimeCount) statAnimeCount.textContent = `${rates.anime_count || 0} adet`;

    // 4. Rating Tiers
    if (ratingTiersList) {
      const tierData = [
        { label: "🌟 Başyapıt (9–10 Puan)", color: "bg-amber-400", count: tiers.masterpiece?.count || 0, pct: tiers.masterpiece?.percent || 0 },
        { label: "💎 Çok Başarılı (7–8 Puan)", color: "bg-emerald-500", count: tiers.great?.count || 0, pct: tiers.great?.percent || 0 },
        { label: "⚖️ Ortalama (5–6 Puan)", color: "bg-blue-500", count: tiers.average?.count || 0, pct: tiers.average?.percent || 0 },
        { label: "📉 Düşük (1–4 Puan)", color: "bg-red-500", count: tiers.low?.count || 0, pct: tiers.low?.percent || 0 },
      ];
      ratingTiersList.innerHTML = tierData.map(t => `
        <div>
          <div class="flex justify-between text-xs font-semibold mb-1">
            <span class="text-zinc-800 dark:text-zinc-200">${t.label}</span>
            <span class="mono text-zinc-500">${t.count} yapım (%${t.pct})</span>
          </div>
          <div class="h-2 w-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
            <div class="h-full ${t.color} transition-all duration-500" style="width:${t.pct}%"></div>
          </div>
        </div>
      `).join("");
    }

    // 4.5. 12-Month Watch Activity Matrix
    const statsMonthlyMatrix = $("statsMonthlyMatrix");
    const monthlyData = stats.monthly_activity || [];
    if (statsMonthlyMatrix && monthlyData.length) {
      const maxCount = Math.max(1, ...monthlyData.map(m => m.count));
      statsMonthlyMatrix.innerHTML = monthlyData.map(m => {
        const heightPct = m.count ? Math.max(15, Math.round((m.count / maxCount) * 100)) : 4;
        const barColor = m.count ? "bg-indigo-500" : "bg-zinc-800";
        return `
          <div class="flex flex-col items-center justify-end h-28 p-2 bg-zinc-900 border border-zinc-800 text-center group relative cursor-pointer" title="${m.month_name}: ${m.count} yapım (${m.hours} saat)">
            <div class="w-full flex-1 flex items-end justify-center mb-1">
              <div class="w-full ${barColor} transition-all duration-500 group-hover:bg-indigo-400" style="height:${heightPct}%"></div>
            </div>
            <span class="mono text-[10px] font-bold ${m.count ? 'text-indigo-400' : 'text-zinc-600'}">${m.count}</span>
            <span class="text-[9px] font-bold uppercase text-zinc-400">${m.month_name}</span>
          </div>
        `;
      }).join("");
    }

    // 5. Genres Breakdown with exact percentages
    const genres = stats.top_genres || [];
    if (statsGenresList) {
      if (!genres.length) {
        statsGenresList.innerHTML = `<p class="text-xs text-zinc-500">Henüz tür verisi yok.</p>`;
      } else {
        statsGenresList.innerHTML = genres.map(g => `
          <div>
            <div class="flex justify-between text-xs font-semibold mb-1">
              <span class="text-zinc-800 dark:text-zinc-200">${g.name}</span>
              <span class="mono text-zinc-500">${g.count} yapım (%${g.percent || 0})</span>
            </div>
            <div class="h-2 w-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
              <div class="h-full bg-purple-500 transition-all duration-500" style="width:${Math.max(5, g.percent || 0)}%"></div>
            </div>
          </div>
        `).join("");
      }
    }

    // 6. Directors
    const directors = stats.top_directors || [];
    if (statsDirectorsList) {
      if (!directors.length) {
        statsDirectorsList.innerHTML = `<p class="text-xs text-zinc-500">Henüz yönetmen verisi yok.</p>`;
      } else {
        const maxD = Math.max(1, ...directors.map(d => d.count));
        statsDirectorsList.innerHTML = directors.map(d => {
          const pct = Math.round((d.count / maxD) * 100);
          return `
            <div>
              <div class="flex justify-between text-xs font-semibold mb-1">
                <span class="text-zinc-800 dark:text-zinc-200">${d.name}</span>
                <span class="mono text-zinc-500">${d.count} film</span>
              </div>
              <div class="h-2 w-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
                <div class="h-full bg-emerald-500 transition-all duration-500" style="width:${pct}%"></div>
              </div>
            </div>`;
        }).join("");
      }
    }

    // 7. Top Cast
    const cast = stats.top_cast || [];
    if (statsCastList) {
      if (!cast.length) {
        statsCastList.innerHTML = `<p class="text-xs text-zinc-500">Henüz oyuncu verisi yok.</p>`;
      } else {
        statsCastList.innerHTML = cast.map(c => `
          <div class="flex items-center justify-between p-2 bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-800 text-xs">
            <span class="font-medium text-zinc-800 dark:text-zinc-200 truncate">${c.name}</span>
            <span class="mono font-bold text-amber-500 ml-2">${c.count} yapım</span>
          </div>
        `).join("");
      }
    }

    // 8. Decades Breakdown
    const decades = stats.decades || [];
    if (statsDecadesList) {
      if (!decades.length) {
        statsDecadesList.innerHTML = `<p class="text-xs text-zinc-500">Henüz yıl verisi yok.</p>`;
      } else {
        const maxDec = Math.max(1, ...decades.map(d => d.count));
        statsDecadesList.innerHTML = decades.map(d => {
          const pct = Math.round((d.count / maxDec) * 100);
          return `
            <div>
              <div class="flex justify-between text-xs font-semibold mb-1">
                <span class="text-zinc-800 dark:text-zinc-200">${d.decade}</span>
                <span class="mono text-zinc-500">${d.count} yapım</span>
              </div>
              <div class="h-2 w-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
                <div class="h-full bg-blue-500 transition-all duration-500" style="width:${pct}%"></div>
              </div>
            </div>`;
        }).join("");
      }
    }

    // 9. Top Rated Favorites (Masterpieces)
    const topRated = stats.top_rated || [];
    if (statsTopRatedList) {
      if (!topRated.length) {
        statsTopRatedList.innerHTML = `<p class="text-xs text-zinc-500 col-span-full">Henüz 8+ puanlı favori film yok.</p>`;
      } else {
        statsTopRatedList.innerHTML = topRated.map(r => {
          const posterSrc = r.poster_path ? (r.poster_path.startsWith("/") ? `/static/posters/${r.id}.jpg` : r.poster_path) : null;
          return `
            <div class="poster-card cursor-pointer" onclick="window.__openDetail(${r.id})">
              ${posterSrc ? `<img src="${posterSrc}" alt="${r.title}" loading="lazy" />` : `<div class="w-full h-full bg-zinc-800 p-2 text-[10px] text-white flex items-center justify-center text-center">${r.title}</div>`}
              <div class="poster-overlay">
                <p class="text-xs font-bold truncate">${r.title}</p>
                <span class="mono text-[10px] font-bold text-amber-400">★ ${r.rating || r.imdb_rating}</span>
              </div>
            </div>`;
        }).join("");
      }
    }

    // 9.5. Milestone Badges Calculation
    const badgesGrid = $("statsBadgesGrid");
    const unlockedCountEl = $("unlockedBadgesCount");
    const totalMedia = data.counts?.all || 0;
    const watchHours = stats.watch_time?.total_hours || 0;
    const hasSciFi = (stats.top_genres || []).some(g => g.name.toLowerCase().includes("bilim") || g.name.toLowerCase().includes("kurgu"));
    const isMaster = Number(data.avg_rating || 0) >= 8.5;
    const hasDiary = (stats.diary || []).length >= 1;

    const BADGES = [
      { icon: "🎬", name: "Sinema Tutkunu", desc: "5+ yapım arşivle", unlocked: totalMedia >= 5 },
      { icon: "⏱️", name: "Zaman Bükücü", desc: "10+ saat izleme süresi", unlocked: watchHours >= 10 },
      { icon: "🧠", name: "Zihin Açıcı", desc: "Bilim Kurgu izle", unlocked: hasSciFi },
      { icon: "💎", name: "Mükemmeliyetçi", desc: "8.5+ ortalama puan", unlocked: isMaster },
      { icon: "📅", name: "Günlük Yazarı", desc: "İzleme tarihi kaydet", unlocked: hasDiary },
    ];

    const unlockedNum = BADGES.filter(b => b.unlocked).length;
    if (unlockedCountEl) unlockedCountEl.textContent = `${unlockedNum} / ${BADGES.length} Açıldı`;

    if (badgesGrid) {
      badgesGrid.innerHTML = BADGES.map(b => `
        <div class="p-3 border text-center transition ${b.unlocked ? "bg-amber-950/20 border-amber-500/40 text-white" : "bg-zinc-800/20 border-zinc-800 text-zinc-600 opacity-50"}">
          <div class="text-2xl mb-1">${b.icon}</div>
          <p class="font-bold text-xs ${b.unlocked ? "text-amber-400" : "text-zinc-500"}">${b.name}</p>
          <p class="text-[10px] text-zinc-400 mt-0.5">${b.desc}</p>
          <span class="inline-block mt-2 text-[9px] font-bold uppercase px-1.5 py-0.2 ${b.unlocked ? "bg-amber-500/20 text-amber-300" : "bg-zinc-800 text-zinc-500"}">${b.unlocked ? "KAZANILDI ✓" : "KİLİTLİ 🔒"}</span>
        </div>
      `).join("");
    }

    // 10. System & Storage Diagnostics
    const sysIntegrity = $("sysIntegrity");
    const sysDbSize = $("sysDbSize");
    const sysPosterSize = $("sysPosterSize");
    const sysSchema = $("sysSchema");
    if (sysIntegrity) sysIntegrity.textContent = (data.sqlite_integrity || "ok").toUpperCase() + " ✓";
    if (sysDbSize) sysDbSize.textContent = `${data.db_size_kb || 0} KB`;
    if (sysPosterSize) sysPosterSize.textContent = `${data.posters?.size_mb || 0} MB (${data.posters?.total_files || 0} afiş)`;
    if (sysSchema) sysSchema.textContent = `v${data.schema_version || 6}`;
  }

  // Optimize DB Button Listener
  $("optimizeDbBtn")?.addEventListener("click", async () => {
    const btn = $("optimizeDbBtn");
    btn.textContent = "Temizleniyor…";
    btn.disabled = true;
    try {
      const res = await api("POST", "/api/system/optimize");
      toast("🧹 " + (res.message || "Veritabanı optimize edildi"));
      fetchSummary();
    } catch (e) {
      toast("Optimizasyon hatası: " + e.message, "error");
    } finally {
      btn.textContent = "🧹 Optimize Et";
      btn.disabled = false;
    }
  });

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
    if (state.favorite) params.set("favorite", "1");
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

  // Layout Mode (grid vs table) & Grid Density
  state.layoutMode = "grid";
  state.gridDensity = localStorage.getItem("grid_density") || "normal";

  const viewGridBtn = $("viewGridBtn");
  const viewTableBtn = $("viewTableBtn");
  const posterGridWrap = $("posterGridWrap");
  const recordsTableWrap = $("recordsTableWrap");
  const recordsTableBody = $("recordsTableBody");

  const DENSITY_CLASSES = {
    compact: "grid grid-cols-3 gap-2 p-3 sm:grid-cols-4 sm:gap-3 lg:grid-cols-6 xl:grid-cols-7 2xl:grid-cols-8",
    normal: "grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 sm:gap-4 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6",
    large: "grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-4",
  };

  function setGridDensity(density) {
    state.gridDensity = density;
    localStorage.setItem("grid_density", density);
    if (posterGrid) {
      posterGrid.className = DENSITY_CLASSES[density] || DENSITY_CLASSES.normal;
    }
    document.querySelectorAll(".density-btn").forEach(b => {
      const active = b.dataset.density === density;
      b.className = `density-btn px-1.5 py-0.5 text-[10px] font-bold transition ${active ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950" : "text-zinc-600 dark:text-zinc-400 hover:text-white"}`;
    });
  }

  document.querySelectorAll(".density-btn").forEach(btn => {
    btn.addEventListener("click", () => setGridDensity(btn.dataset.density));
  });

  function setViewMode(mode) {
    state.layoutMode = mode;
    const isGrid = mode === "grid";
    posterGridWrap?.classList.toggle("hidden", !isGrid);
    recordsTableWrap?.classList.toggle("hidden", isGrid);

    if (viewGridBtn) viewGridBtn.className = `px-2 py-0.5 text-[11px] font-bold uppercase transition ${isGrid ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950" : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-white"}`;
    if (viewTableBtn) viewTableBtn.className = `px-2 py-0.5 text-[11px] font-bold uppercase transition ${!isGrid ? "bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950" : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-white"}`;

    fetchRecords();
  }

  viewGridBtn?.addEventListener("click", () => setViewMode("grid"));
  viewTableBtn?.addEventListener("click", () => setViewMode("table"));
  setGridDensity(state.gridDensity);

  function renderRecords(records) {
    if (resultLine) {
      resultLine.textContent = records.length
        ? `${state.total.toLocaleString("tr-TR")} kayıt (${state.offset + 1}–${Math.min(state.offset + records.length, state.total)})`
        : "0 kayıt";
    }

    // Render Up Next Banner (If viewing planned or if planned items exist)
    const upNextSec = $("upNextSection");
    const upNextCard = $("upNextCard");
    const plannedItem = records.find(r => r.status === "planned");
    if (upNextSec && upNextCard) {
      if (plannedItem && (state.status === "planned" || state.status === "")) {
        upNextSec.classList.remove("hidden");
        const posterSrc = plannedItem.poster_url;
        upNextCard.innerHTML = `
          ${posterSrc ? `<img src="${posterSrc}" alt="" class="w-14 aspect-[2/3] object-cover shrink-0 shadow-lg cursor-pointer" onclick="window.__openDetail(${plannedItem.id})" />` : `<div class="w-14 aspect-[2/3] bg-zinc-800 shrink-0"></div>`}
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <h3 class="font-bold text-white text-sm truncate cursor-pointer hover:underline" onclick="window.__openDetail(${plannedItem.id})">${plannedItem.title}</h3>
              <span class="text-xs text-zinc-400 font-mono">(${plannedItem.release_year || "—"})</span>
              ${plannedItem.imdb_rating ? `<span class="bg-amber-400 text-zinc-950 px-1 text-[10px] font-bold">IMDb ${Number(plannedItem.imdb_rating).toFixed(1)}</span>` : ""}
            </div>
            <p class="text-xs text-zinc-400 mt-0.5 line-clamp-1">${plannedItem.overview || (plannedItem.director ? `Yönetmen: ${plannedItem.director}` : "İzleme listende sıradaki film.")}</p>
            <div class="flex items-center gap-2 mt-2">
              <button id="upNextCompleteBtn" class="bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 text-[10px] font-bold uppercase transition">✓ Şimdi İzledim</button>
              <button class="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-2.5 py-1 text-[10px] font-bold uppercase transition" onclick="window.__openDetail(${plannedItem.id})">Detay ↗</button>
            </div>
          </div>
        `;

        upNextCard.querySelector("#upNextCompleteBtn")?.addEventListener("click", async () => {
          try {
            await api("PUT", `/api/records/${plannedItem.id}`, { status: "completed", watched_at: new Date().toISOString().split("T")[0] });
            toast(`"${plannedItem.title}" izlendi olarak işaretlendi! ✓`);
            fetchRecords();
            fetchSummary();
          } catch (e) {
            toast("Hata: " + e.message, "error");
          }
        });
      } else {
        upNextSec.classList.add("hidden");
      }
    }

    // Render Active Filters Bar
    const activeFiltersBar = $("activeFiltersBar");
    const activeFilterTags = $("activeFilterTags");
    if (activeFiltersBar && activeFilterTags) {
      const tagsList = [];
      if (state.query) tagsList.push({ label: `Arama: "${state.query}"`, clear: () => { state.query = ""; if (searchInput) searchInput.value = ""; } });
      if (state.favorite) tagsList.push({ label: "❤️ Favoriler", clear: () => { state.favorite = false; } });
      if (state.min_rating) tagsList.push({ label: `★ ${state.min_rating}+ Puan`, clear: () => { state.min_rating = null; } });
      if (state.status) tagsList.push({ label: `Durum: ${STATUS_LABELS[state.status] || state.status}`, clear: () => { state.status = ""; } });
      if (state.kind !== "all") tagsList.push({ label: `Tür: ${KIND_LABELS[state.kind] || state.kind}`, clear: () => { state.kind = "all"; } });
      if (state.min_year || state.max_year) tagsList.push({ label: `Dönem: ${state.min_year || '...'}–${state.max_year || '...'}`, clear: () => { state.min_year = ""; state.max_year = ""; } });
      if (state.tag) tagsList.push({ label: `#${state.tag}`, clear: () => { state.tag = ""; } });

      if (tagsList.length > 0) {
        activeFiltersBar.classList.remove("hidden");
        activeFilterTags.innerHTML = tagsList.map((t, idx) => `
          <span class="inline-flex items-center gap-1 px-2 py-0.5 bg-zinc-200 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 text-[10px] font-semibold">
            ${t.label}
            <button class="remove-active-tag hover:text-red-400 font-bold ml-0.5" data-tag-idx="${idx}">&times;</button>
          </span>
        `).join("");

        activeFilterTags.querySelectorAll(".remove-active-tag").forEach(btn => {
          btn.addEventListener("click", () => {
            const idx = parseInt(btn.dataset.tagIdx);
            tagsList[idx]?.clear();
            state.offset = 0;
            fetchRecords();
            fetchSummary();
          });
        });
      } else {
        activeFiltersBar.classList.add("hidden");
      }
    }

    if (!records.length) {
      emptyState?.classList.remove("hidden");
      posterGridWrap?.classList.add("hidden");
      recordsTableWrap?.classList.add("hidden");
      return;
    }
    emptyState?.classList.add("hidden");

    if (state.layoutMode === "table") {
      posterGridWrap?.classList.add("hidden");
      recordsTableWrap?.classList.remove("hidden");
      if (recordsTableBody) {
        recordsTableBody.innerHTML = records.map(rec => {
          const posterSrc = rec.poster_url;
          const statusBadge = STATUS_LABELS[rec.status] || rec.status;
          const statusColor = STATUS_COLORS[rec.status] || "bg-zinc-700 text-white";
          const genres = Array.isArray(rec.genres) ? rec.genres : [];
          return `
            <tr class="hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition cursor-pointer" onclick="window.__openDetail(${rec.id})">
              <td class="p-2.5 text-center">
                ${posterSrc ? `<img src="${posterSrc}" alt="" class="w-8 aspect-[2/3] object-cover mx-auto shadow-sm" />` : `<div class="w-8 aspect-[2/3] bg-zinc-800 text-[7px] text-zinc-400 flex items-center justify-center mx-auto">Afiş</div>`}
              </td>
              <td class="p-2.5">
                <p class="font-bold text-zinc-900 dark:text-zinc-100 text-sm">${rec.title}</p>
                <div class="flex items-center gap-1.5 mt-0.5 flex-wrap">
                  <span class="text-[10px] uppercase font-bold text-zinc-500">${rec.media_type === "movie" ? "Film" : "Dizi"}</span>
                  ${genres.slice(0, 3).map(g => `<span class="text-[9px] px-1 py-0.2 bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">${g}</span>`).join("")}
                </div>
              </td>
              <td class="p-2.5 mono font-semibold text-zinc-600 dark:text-zinc-400">${rec.release_year || "—"}</td>
              <td class="p-2.5">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="mono font-bold text-amber-500">★ ${rec.rating || "-"}</span>
                  ${rec.imdb_rating ? `<span class="text-[10px] font-bold px-1 bg-amber-400 text-zinc-950">IMDb ${Number(rec.imdb_rating).toFixed(1)}</span>` : ""}
                </div>
              </td>
              <td class="p-2.5">
                <span class="text-[10px] font-bold uppercase px-2 py-0.5 ${statusColor}">${statusBadge}</span>
              </td>
              <td class="p-2.5 text-zinc-500 font-mono">${rec.runtime ? `${rec.runtime} dk` : "—"}</td>
              <td class="p-2.5 text-right" onclick="event.stopPropagation()">
                <div class="flex items-center justify-end gap-1">
                  <button class="table-complete-btn p-1 text-xs bg-zinc-100 dark:bg-zinc-800 hover:bg-emerald-600 hover:text-white transition" title="Durumu Değiştir" data-id="${rec.id}" data-status="${rec.status}">
                    ${rec.status === 'completed' ? '✓' : '👁️'}
                  </button>
                  <button class="table-delete-btn p-1 text-xs bg-zinc-100 dark:bg-zinc-800 hover:bg-red-600 hover:text-white transition" title="Arşivden Sil" data-id="${rec.id}" data-title="${rec.title}">
                    🗑️
                  </button>
                  <button class="table-detail-btn px-2 py-1 text-[11px] font-semibold bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition" onclick="window.__openDetail(${rec.id})">
                    Detay
                  </button>
                </div>
              </td>
            </tr>`;
        }).join("");

        // Table complete button listeners
        recordsTableBody.querySelectorAll(".table-complete-btn").forEach(btn => {
          btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const id = parseInt(btn.dataset.id);
            const curStatus = btn.dataset.status;
            const newStatus = curStatus === "completed" ? "planned" : "completed";
            try {
              await api("PUT", `/api/records/${id}`, { status: newStatus });
              toast(newStatus === "completed" ? "İzlendi olarak işaretlendi ✓" : "İzlenecekler listesine alındı");
              fetchRecords();
              fetchSummary();
            } catch (err) {
              toast("Hata: " + err.message, "error");
            }
          });
        });

        // Table delete button listeners
        recordsTableBody.querySelectorAll(".table-delete-btn").forEach(btn => {
          btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const id = parseInt(btn.dataset.id);
            const title = btn.dataset.title;
            if (confirm(`"${title}" kaydını silmek istediğinden emin misin?`)) {
              try {
                await api("DELETE", `/api/records/${id}`);
                toast(`"${title}" silindi 🗑️`);
                fetchRecords();
                fetchSummary();
              } catch (err) {
                toast("Silme hatası: " + err.message, "error");
              }
            }
          });
        });
      }
    } else {
      recordsTableWrap?.classList.add("hidden");
      posterGridWrap?.classList.remove("hidden");
      if (posterGrid) {
        posterGrid.innerHTML = "";
        records.forEach((rec) => posterGrid.appendChild(createPosterCard(rec)));
      }
    }
  }

  function createPosterCard(rec) {
    const card = document.createElement("div");
    card.className = "poster-card group";
    card.tabIndex = 0;
    const kindBadge = rec.is_anime ? (rec.media_type === "movie" ? "Anime Film" : "Anime Dizi") : (rec.media_type === "movie" ? "Film" : "Dizi");
    const statusBadge = STATUS_LABELS[rec.status] || rec.status;
    const statusColor = STATUS_COLORS[rec.status] || "bg-zinc-700 text-white";
    const posterSrc = rec.poster_url;

    const isFav = Boolean(rec.is_favorite);
    const favHeart = isFav ? "❤️" : "🤍";
    const isMasterpiece = (rec.rating && rec.rating >= 9) || (rec.imdb_rating && Number(rec.imdb_rating) >= 8.6);

    if (posterSrc) {
      card.innerHTML = `
        <img src="${posterSrc}" alt="${rec.title}" loading="lazy" />
        <!-- Quick Action Hover Bar -->
        <div class="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition duration-200 z-10">
          <button class="quick-rate-btn p-1.5 bg-zinc-900/90 hover:bg-amber-600 text-white rounded text-xs transition shadow-md" title="Hızlı Puan Ver">
            ⭐
          </button>
          <button class="quick-fav-btn p-1.5 bg-zinc-900/90 hover:bg-red-950 text-white rounded text-xs transition shadow-md" title="${isFav ? 'Favorilerden çıkar' : 'Favorilere ekle'}">
            ${favHeart}
          </button>
          <button class="quick-complete-btn p-1.5 bg-zinc-900/90 hover:bg-emerald-600 text-white rounded text-xs transition shadow-md" title="${rec.status === 'completed' ? 'Zaten izlendi' : 'İzlendi olarak işaretle'}">
            ${rec.status === 'completed' ? '✓' : '👁️'}
          </button>
          <button class="quick-delete-btn p-1.5 bg-zinc-900/90 hover:bg-red-600 text-white rounded text-xs transition shadow-md" title="Arşivden Sil">
            🗑️
          </button>
          <button class="quick-trailer-btn p-1.5 bg-zinc-900/90 hover:bg-red-600 text-white rounded text-xs transition shadow-md" title="Fragmanı Aç">
            ▶
          </button>
        </div>
        <div class="absolute top-2 left-2 z-10 flex flex-col gap-1">
          <div class="flex items-center gap-1">
            ${isFav ? `<span class="text-xs drop-shadow-md">❤️</span>` : ""}
            ${rec.note ? `<span class="text-xs drop-shadow-md cursor-help" title="Kişisel Not: ${rec.note}">💬</span>` : ""}
          </div>
          ${isMasterpiece ? `<span class="text-[8px] font-black uppercase px-1 py-0.2 bg-amber-400 text-zinc-950 shadow-md self-start">★ BAŞYAPIT</span>` : ""}
        </div>
        <div class="poster-overlay">
          <span class="inline-block self-start text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 mb-1 ${statusColor}">${statusBadge}</span>
          <h3 class="text-sm font-bold leading-tight line-clamp-2">${highlightMatch(rec.title, state.query)}</h3>
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
            <h3 class="text-xs font-bold leading-tight line-clamp-3 px-1 text-zinc-100">${highlightMatch(rec.title, state.query)}</h3>
          </div>
          <div class="flex items-center justify-between text-[11px] text-zinc-400 pt-2 border-t border-zinc-800">
            <span>${rec.release_year || "—"}</span>
            <span class="text-[10px] font-semibold px-1.5 py-0.5 ${statusColor}">${statusBadge}</span>
          </div>
        </div>
        <!-- Quick Action Hover Bar -->
        <div class="absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition duration-200 z-10">
          <button class="quick-rate-btn p-1.5 bg-zinc-900/90 hover:bg-amber-600 text-white rounded text-xs transition shadow-md" title="Hızlı Puan Ver">
            ⭐
          </button>
          <button class="quick-fav-btn p-1.5 bg-zinc-900/90 hover:bg-red-950 text-white rounded text-xs transition shadow-md" title="${isFav ? 'Favorilerden çıkar' : 'Favorilere ekle'}">
            ${favHeart}
          </button>
          <button class="quick-complete-btn p-1.5 bg-zinc-900/90 hover:bg-emerald-600 text-white rounded text-xs transition shadow-md" title="${rec.status === 'completed' ? 'Zaten izlendi' : 'İzlendi olarak işaretle'}">
            ${rec.status === 'completed' ? '✓' : '👁️'}
          </button>
          <button class="quick-delete-btn p-1.5 bg-zinc-900/90 hover:bg-red-600 text-white rounded text-xs transition shadow-md" title="Arşivden Sil">
            🗑️
          </button>
          <button class="quick-trailer-btn p-1.5 bg-zinc-900/90 hover:bg-red-600 text-white rounded text-xs transition shadow-md" title="Fragmanı Aç">
            ▶
          </button>
        </div>
        <div class="absolute top-2 left-2 z-10 flex flex-col gap-1">
          <div class="flex items-center gap-1">
            ${isFav ? `<span class="text-xs drop-shadow-md">❤️</span>` : ""}
            ${rec.note ? `<span class="text-xs drop-shadow-md cursor-help" title="Kişisel Not: ${rec.note}">💬</span>` : ""}
          </div>
          ${isMasterpiece ? `<span class="text-[8px] font-black uppercase px-1 py-0.2 bg-amber-400 text-zinc-950 shadow-md self-start">★ BAŞYAPIT</span>` : ""}
        </div>
        <div class="poster-overlay">
          <span class="inline-block self-start text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 mb-1 ${statusColor}">${statusBadge}</span>
          <h3 class="text-sm font-bold leading-tight line-clamp-2">${highlightMatch(rec.title, state.query)}</h3>
          <p class="text-xs text-zinc-300 mt-1 line-clamp-3">${rec.overview || rec.note || ""}</p>
          <div class="mt-2 flex items-center justify-between text-xs text-zinc-400">
            <span>${rec.release_year || "—"}</span>
            <span class="mono font-semibold text-amber-400">★ ${rec.rating ? rec.rating + "/10" : "—"}</span>
          </div>
        </div>`;
    }

    // Quick Rate Listener
    card.querySelector(".quick-rate-btn")?.addEventListener("click", async (e) => {
      e.stopPropagation();
      const current = rec.rating || 10;
      const promptVal = prompt(`"${rec.title}" için 1-10 arası puan girin:`, current);
      if (promptVal !== null) {
        const num = parseInt(promptVal);
        if (!isNaN(num) && num >= 1 && num <= 10) {
          try {
            await api("PUT", `/api/records/${rec.id}`, { rating: num, status: "completed" });
            toast(`"${rec.title}" puanı ${num}/10 olarak güncellendi! ★`);
            fetchRecords();
            fetchSummary();
          } catch (err) {
            toast("Puanlama hatası: " + err.message, "error");
          }
        }
      }
    });

    // Quick Action Listeners
    card.querySelector(".quick-fav-btn")?.addEventListener("click", async (e) => {
      e.stopPropagation();
      const newFav = isFav ? 0 : 1;
      try {
        await api("PUT", `/api/records/${rec.id}`, { is_favorite: newFav });
        toast(newFav ? `"${rec.title}" favorilere eklendi ❤️` : `"${rec.title}" favorilerden çıkarıldı`);
        fetchRecords();
        fetchSummary();
      } catch (err) {
        toast("Hata: " + err.message, "error");
      }
    });

    // Quick Action Listeners
    card.querySelector(".quick-complete-btn")?.addEventListener("click", async (e) => {
      e.stopPropagation();
      const newStatus = rec.status === "completed" ? "planned" : "completed";
      try {
        await api("PUT", `/api/records/${rec.id}`, { status: newStatus });
        toast(`"${rec.title}" ${newStatus === 'completed' ? 'izlendi olarak işaretlendi ✓' : 'izlenecekler listesine alındı'}`);
        fetchRecords();
        fetchSummary();
      } catch (err) {
        toast("Hata: " + err.message, "error");
      }
    });

    // Quick Delete Listener
    card.querySelector(".quick-delete-btn")?.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (confirm(`"${rec.title}" kaydını arşivden silmek istediğinden emin misin?`)) {
        try {
          await api("DELETE", `/api/records/${rec.id}`);
          toast(`"${rec.title}" arşivden silindi 🗑️`);
          fetchRecords();
          fetchSummary();
        } catch (err) {
          toast("Silme hatası: " + err.message, "error");
        }
      }
    });

    card.querySelector(".quick-trailer-btn")?.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        const tdata = await api("GET", `/api/records/${rec.id}/trailer`);
        if (trailerTitle) trailerTitle.textContent = `${rec.title} — Fragman`;
        if (trailerIframe) trailerIframe.src = tdata.trailer_url;
        showModal(trailerModal);
      } catch (err) {
        toast("Fragman bulunamadı: " + err.message, "error");
      }
    });
    card.addEventListener("click", () => openDetail(rec.id));
    card.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDetail(rec.id); } });
    return card;
  }

  // ── Person Filmography Modal ──────────────────────────
  async function openPersonFilmography(name) {
    const pModal = $("personModal");
    const pName = $("personName");
    const pDept = $("personDept");
    const pAvatar = $("personAvatar");
    const pGrid = $("personMoviesGrid");
    if (!pModal) return;

    if (pName) pName.textContent = name;
    if (pDept) pDept.textContent = "Yükleniyor…";
    if (pAvatar) pAvatar.innerHTML = `<span class="animate-pulse">…</span>`;
    if (pGrid) pGrid.innerHTML = `<div class="p-6 text-center text-zinc-400 animate-pulse col-span-full">Filmografi yükleniyor…</div>`;
    showModal(pModal);

    try {
      const data = await api("GET", `/api/person/movies?name=${encodeURIComponent(name)}`);
      const p = data.person || {};
      const movies = data.movies || [];

      if (pName) pName.textContent = p.name || name;
      if (pDept) pDept.textContent = p.known_for_department === "Directing" ? "Yönetmen" : "Oyuncu / Sanatçı";
      if (pAvatar) {
        pAvatar.innerHTML = p.profile_url
          ? `<img src="${p.profile_url}" class="w-full h-full object-cover" />`
          : `<span class="text-sm font-bold text-zinc-400">${name[0]}</span>`;
      }

      if (pGrid) {
        if (!movies.length) {
          pGrid.innerHTML = `<p class="text-xs text-zinc-500 col-span-full py-4 text-center">Bu sanatçı için ek yapım bulunamadı.</p>`;
        } else {
          pGrid.innerHTML = movies.map(m => {
            const poster = m.poster_preview || (m.poster_path ? `https://image.tmdb.org/t/p/w200${m.poster_path}` : "");
            return `
              <div class="bg-zinc-800/60 border border-zinc-700/60 p-2 flex flex-col justify-between">
                ${poster ? `<img src="${poster}" class="w-full aspect-[2/3] object-cover mb-1.5" />` : `<div class="w-full aspect-[2/3] bg-zinc-700 mb-1.5 flex items-center justify-center text-[10px]">Afiş Yok</div>`}
                <p class="text-xs font-bold text-white truncate" title="${m.title}">${m.title}</p>
                <div class="flex items-center justify-between text-[10px] text-zinc-400 mt-1 mb-2">
                  <span>${m.release_year || "—"}</span>
                  ${m.tmdb_rating ? `<span class="mono text-amber-400 font-bold">★ ${Number(m.tmdb_rating).toFixed(1)}</span>` : ""}
                </div>
                <button class="add-person-movie-btn bg-zinc-700 hover:bg-emerald-700 text-white text-[10px] font-bold uppercase py-1 transition" data-tmdb-id="${m.tmdb_id}" data-media-type="${m.media_type || "movie"}">+ Arşive Ekle</button>
              </div>`;
          }).join("");

          pGrid.querySelectorAll(".add-person-movie-btn").forEach(btn => {
            btn.addEventListener("click", async () => {
              const tid = btn.dataset.tmdbId;
              const mtype = btn.dataset.mediaType;
              btn.textContent = "...";
              btn.disabled = true;
              try {
                const res = await api("POST", `/api/tmdb/import/${tid}`, { media_type: mtype });
                toast(`"${res.title || "Yapım"}" arşive eklendi!`);
                btn.textContent = "✓ Eklendi";
                fetchRecords();
                fetchSummary();
              } catch (e) {
                toast("Ekleme hatası: " + e.message, "error");
                btn.textContent = "Hata";
              }
            });
          });
        }
      }
    } catch (err) {
      if (pGrid) pGrid.innerHTML = `<div class="p-4 text-center text-red-400 text-xs col-span-full">Hata: ${err.message}</div>`;
    }
  }

  window.__openDetail = (id) => openDetail(id);

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
        <div class="flex flex-col sm:flex-row gap-3 sm:gap-5">
          ${posterSrc ? `<div class="shrink-0 flex sm:block items-center justify-center"><img src="${posterSrc}" alt="${rec.title}" class="w-24 sm:w-36 aspect-[2/3] object-cover shadow-lg border border-zinc-700" /></div>` : ""}
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-1.5 sm:gap-2 mb-1 flex-wrap">
              <span class="text-[10px] font-bold uppercase px-2 py-0.5 bg-zinc-800 text-zinc-300">${typeName}</span>
              <span class="text-[10px] font-bold uppercase px-2 py-0.5 ${statusColor}">${statusBadge}</span>
              ${genres.map(g => `<span class="text-[10px] px-1.5 py-0.5 bg-zinc-800/60 text-zinc-400">${g}</span>`).join("")}
            </div>
            <h2 class="text-lg sm:text-xl font-bold text-white leading-tight">${rec.title}</h2>
            ${rec.original_title && rec.original_title !== rec.title ? `<p class="text-xs text-zinc-500 mt-0.5">${rec.original_title}</p>` : ""}
            <div class="mt-2.5 flex items-center gap-2 sm:gap-3 text-xs text-zinc-400 flex-wrap">
              <span class="mono text-base sm:text-lg font-bold text-amber-400">★ ${rec.rating || "-"}<span class="text-zinc-600 text-xs"> / 10</span></span>
              ${rec.imdb_rating ? `<span class="bg-amber-400 text-zinc-950 px-1.5 py-0.5 text-[10px] font-bold">IMDb ${Number(rec.imdb_rating).toFixed(1)}</span>` : ""}
              ${rec.tmdb_rating ? `<span class="bg-zinc-800 text-zinc-300 px-1.5 py-0.5 text-[10px] font-bold">TMDB ${Number(rec.tmdb_rating).toFixed(1)}</span>` : ""}
              ${rec.imdb_id ? `<a href="https://www.imdb.com/title/${rec.imdb_id}/" target="_blank" class="text-amber-400 hover:underline text-[11px]">IMDb ↗</a>` : ""}
              <span>${rec.release_year || "—"}</span>
              ${rec.runtime ? `<span>${rec.runtime} dk</span>` : ""}
            </div>
            ${rec.director ? `<div class="mt-2 text-xs text-zinc-400"><span class="text-zinc-500 font-medium">Yönetmen:</span> ${rec.director.split(",").map(d => `<button class="person-filter-btn text-amber-400 hover:underline hover:text-amber-300 font-semibold mr-1" data-person="${d.trim()}">${d.trim()}</button>`).join(", ")}</div>` : ""}
            ${rec.cast_members ? `<div class="mt-1 text-xs text-zinc-400"><span class="text-zinc-500 font-medium">Oyuncular:</span> ${rec.cast_members.split(",").map(c => `<button class="person-filter-btn text-zinc-300 hover:underline hover:text-white mr-1" data-person="${c.trim()}">${c.trim()}</button>`).join(", ")}</div>` : ""}
            <!-- Trailer, Ticket & Soundtrack Buttons -->
            <div class="mt-3 grid grid-cols-2 sm:flex items-center gap-1.5 sm:gap-2 flex-wrap">
              <button id="openTrailerBtn" class="border border-red-600/80 bg-red-600/20 text-red-300 hover:bg-red-600 hover:text-white px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wider transition text-center">
                ▶ Fragman
              </button>
              <button id="openTicketBtn" class="border border-amber-500/80 bg-amber-500/20 text-amber-300 hover:bg-amber-500 hover:text-zinc-950 px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wider transition text-center">
                🎟️ Bilet
              </button>
              <a href="https://open.spotify.com/search/${encodeURIComponent(rec.title + ' soundtrack')}" target="_blank" class="border border-emerald-500/80 bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500 hover:text-zinc-950 px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wider transition inline-flex items-center justify-center gap-1">
                🎵 Spotify ↗
              </a>
              <a href="https://music.youtube.com/search?q=${encodeURIComponent(rec.title + ' soundtrack')}" target="_blank" class="border border-red-500/80 bg-red-500/20 text-red-300 hover:bg-red-500 hover:text-white px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wider transition inline-flex items-center justify-center gap-1">
                🔴 YT Music ↗
              </a>
            </div>
          </div>
        </div>
        ${rec.overview ? `<div class="mt-3 sm:mt-4"><h4 class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1">Özet</h4><p class="text-xs sm:text-sm text-zinc-300 leading-relaxed bg-zinc-800/30 p-2.5 sm:p-3">${rec.overview}</p></div>` : ""}
        <!-- Tags input -->
        <div class="mt-3">
          <label class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1 block">Özel Etiketler (Virgülle ayırın)</label>
          <input id="modalTagsInput" type="text" value="${tags.join(", ")}" placeholder="Örn: Favoriler, Oscar, Nolan, Maraton" class="w-full bg-zinc-800 border border-zinc-700 px-3 py-2 text-xs text-zinc-200 outline-none focus:border-zinc-500" />
        </div>

        <!-- Note / Quote Input -->
        <div class="mt-3">
          <label class="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-1 block">💬 Unutulmaz Replik / Kişisel Not</label>
          <textarea id="modalNoteInput" rows="2" placeholder="Örn: “Sevgi, zaman ve mekânı aşan tek şeydir.” — Brand" class="w-full bg-zinc-800 border border-zinc-700 px-3 py-2 text-xs text-zinc-200 outline-none focus:border-zinc-500">${rec.note || ""}</textarea>
        </div>
        
        <!-- Star Rating Widget -->
        <div class="mt-3 bg-zinc-800/40 p-3 border border-zinc-800">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-bold uppercase tracking-wider text-zinc-400">Puan Ver</span>
            <span id="starRatingLabel" class="mono text-xs font-bold text-amber-400">${rec.rating ? `★ ${rec.rating} / 10` : "Puanlanmadı"}</span>
          </div>
          <div id="starRatingContainer" class="flex gap-1 overflow-x-auto pb-1 thin-scrollbar">
            ${[1,2,3,4,5,6,7,8,9,10].map(n => `
              <button type="button" class="star-btn flex-1 min-w-[28px] h-9 sm:h-8 text-sm sm:text-base font-bold transition flex items-center justify-center ${rec.rating && rec.rating >= n ? "text-amber-400 bg-amber-950/40 border border-amber-600/50" : "text-zinc-600 bg-zinc-800/60 hover:text-amber-300"}" data-rating="${n}">★</button>
            `).join("")}
          </div>
        </div>

        <!-- Watch Date & Times Watched -->
        <div class="mt-3 grid grid-cols-2 gap-2">
          <div>
            <label class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 mb-1 block">İzleme Tarihi</label>
            <input id="modalWatchedAtInput" type="date" value="${rec.watched_at || ""}" class="w-full bg-zinc-800 border border-zinc-700 px-2 py-1.5 text-xs text-zinc-200 outline-none focus:border-zinc-500" />
          </div>
          <div class="flex flex-col justify-end">
            <button id="modalRewatchBtn" type="button" class="bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 px-2 py-1.5 text-xs font-semibold uppercase tracking-wider transition text-center" title="İzleme sayısını artır">
              🔁 ${rec.times_watched && rec.times_watched > 1 ? `${rec.times_watched}. Kez İzledim` : "Tekrar İzle (+1)"}
            </button>
          </div>
        </div>

        ${seasonsHtml}
        <div class="mt-5 pt-4 border-t border-zinc-800 flex items-center gap-2">
          <select id="modalStatusSelect" class="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-200 px-3 py-2 text-xs">
            ${Object.entries(STATUS_LABELS).filter(([k]) => k).map(([k, v]) => `<option value="${k}" ${rec.status === k ? "selected" : ""}>${v}</option>`).join("")}
          </select>
          <button id="modalSaveBtn" class="bg-zinc-100 text-zinc-900 px-4 py-2 text-xs font-bold uppercase tracking-wider hover:bg-white transition">Kaydet</button>
          <button id="modalDeleteBtn" class="bg-red-900/60 text-red-200 px-3 py-2 text-xs font-bold uppercase tracking-wider hover:bg-red-800 transition ml-auto">Sil</button>
        </div>
        <div class="mt-3 flex items-center justify-between text-[10px] text-zinc-600">
          <span>ID: #${rec.id} | Eklenme: ${rec.created_at || "—"}</span>
          <span>Güncelleme: ${rec.updated_at || "—"}</span>
        </div>`;
      
      // Person filter & filmography click handlers
      modalContent.querySelectorAll(".person-filter-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const person = btn.dataset.person;
          openPersonFilmography(person);
        });
      });

      // Load Similar Movies async
      (async () => {
        const sec = $("modalSimilarSection");
        const list = $("modalSimilarList");
        if (!sec || !list) return;
        try {
          const simData = await api("GET", `/api/records/${rec.id}/similar`);
          if (simData.results && simData.results.length > 0) {
            sec.classList.remove("hidden");
            list.innerHTML = simData.results.map(s => {
              const poster = s.poster_preview || (s.poster_path ? `https://image.tmdb.org/t/p/w200${s.poster_path}` : "");
              return `
                <div class="p-2 bg-zinc-800/60 border border-zinc-700/60 flex flex-col justify-between">
                  ${poster ? `<img src="${poster}" alt="${s.title}" class="w-full aspect-[2/3] object-cover mb-1.5" />` : `<div class="w-full aspect-[2/3] bg-zinc-700 mb-1.5 flex items-center justify-center text-[10px]">Afiş Yok</div>`}
                  <p class="text-[11px] font-bold truncate text-white" title="${s.title}">${s.title}</p>
                  <div class="flex items-center justify-between text-[10px] text-zinc-400 mt-1 mb-2">
                    <span>${s.release_year || "—"}</span>
                    ${s.tmdb_rating ? `<span class="mono text-amber-400">★ ${Number(s.tmdb_rating).toFixed(1)}</span>` : ""}
                  </div>
                  <button class="add-similar-btn bg-zinc-700 hover:bg-emerald-700 text-white text-[10px] font-bold uppercase py-1 transition" data-tmdb-id="${s.tmdb_id}" data-media-type="${s.media_type || "movie"}">+ Ekle</button>
                </div>`;
            }).join("");

            list.querySelectorAll(".add-similar-btn").forEach(sbtn => {
              sbtn.addEventListener("click", async () => {
                const tid = sbtn.dataset.tmdbId;
                const mtype = sbtn.dataset.mediaType;
                sbtn.textContent = "...";
                sbtn.disabled = true;
                try {
                  const res = await api("POST", `/api/tmdb/import/${tid}`, { media_type: mtype });
                  toast(`"${res.title || "Yapım"}" eklendi!`);
                  sbtn.textContent = "✓ Eklendi";
                  fetchRecords();
                  fetchSummary();
                } catch (e) {
                  toast("Ekleme hatası: " + e.message, "error");
                  sbtn.textContent = "Hata";
                }
              });
            });
          }
        } catch (e) {
          // Ignore similar lookup failure
        }
      })();

      let selectedRating = rec.rating || null;
      let timesWatched = rec.times_watched || 1;

      // Star rating click handlers
      const starBtns = modalContent.querySelectorAll(".star-btn");
      const starLabel = $("starRatingLabel");
      starBtns.forEach(sbtn => {
        const val = parseInt(sbtn.dataset.rating);
        sbtn.addEventListener("click", () => {
          if (selectedRating === val) {
            selectedRating = null; // toggle off
          } else {
            selectedRating = val;
          }
          if (starLabel) starLabel.textContent = selectedRating ? `★ ${selectedRating} / 10` : "Puanlanmadı";
          starBtns.forEach(b => {
            const bval = parseInt(b.dataset.rating);
            if (selectedRating && bval <= selectedRating) {
              b.className = "star-btn flex-1 py-1 text-sm font-bold transition text-center text-amber-400 bg-amber-950/40 border border-amber-600/50";
            } else {
              b.className = "star-btn flex-1 py-1 text-sm font-bold transition text-center text-zinc-600 bg-zinc-800/60 hover:text-amber-300";
            }
          });
        });
      });

      // Rewatch counter button
      const rewatchBtn = $("modalRewatchBtn");
      rewatchBtn?.addEventListener("click", () => {
        timesWatched += 1;
        rewatchBtn.textContent = `🔁 ${timesWatched}. Kez İzledim`;
        toast(`İzleme sayısı artırıldı (${timesWatched})`);
      });

      $("openTicketBtn")?.addEventListener("click", () => {
        const ticketModal = $("ticketModal");
        if (!ticketModal) return;
        $("ticketTitle").textContent = rec.title;
        $("ticketSubtitle").textContent = `${rec.release_year || "—"} • ${Array.isArray(rec.genres) ? rec.genres.join(", ") : "Sinema"}`;
        $("ticketRating").textContent = rec.rating ? `★ ${rec.rating} / 10` : (rec.imdb_rating ? `IMDb ${rec.imdb_rating}` : "★ Puanlanmadı");
        $("ticketDate").textContent = rec.watched_at || new Date().toLocaleDateString("tr-TR");
        $("ticketDirector").textContent = rec.director || "Bilinmiyor";
        $("ticketFormat").textContent = rec.media_type === "movie" ? (rec.is_anime ? "Anime Film" : "Film") : "Dizi";
        $("ticketNo").textContent = `№ MT-${rec.id.toString().padStart(4, "0")}`;
        showModal(ticketModal);
      });

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

      $("modalSaveBtn")?.addEventListener("click", async () => {
        const newStatus = $("modalStatusSelect")?.value;
        const tagsVal = $("modalTagsInput")?.value || "";
        const noteVal = $("modalNoteInput")?.value || null;
        const watchedAtVal = $("modalWatchedAtInput")?.value || null;
        const tagsArr = tagsVal.split(",").map(t => t.trim()).filter(Boolean);
        try {
          await api("PUT", `/api/records/${rec.id}`, {
            status: newStatus,
            rating: selectedRating,
            note: noteVal,
            watched_at: watchedAtVal,
            times_watched: timesWatched,
            tags: tagsArr,
          });
          toast("Kayıt güncellendi");
          hideModal(detailModal);
          fetchRecords();
          fetchSummary();
        } catch (e) { toast("Güncelleme hatası: " + e.message, "error"); }
      });

      let deleteArmed = false;
      const deleteBtn = $("modalDeleteBtn");
      deleteBtn?.addEventListener("click", async (e) => {
        e.preventDefault();
        if (!deleteArmed) {
          deleteArmed = true;
          deleteBtn.textContent = "⚠️ Emin misin? (Tıkla ve Sil)";
          deleteBtn.className = "bg-red-600 text-white px-3 py-1.5 text-xs font-bold uppercase tracking-wider hover:bg-red-700 transition ml-auto animate-pulse";
          setTimeout(() => {
            if (deleteArmed && deleteBtn) {
              deleteArmed = false;
              deleteBtn.textContent = "Sil";
              deleteBtn.className = "bg-red-900/60 text-red-200 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider hover:bg-red-800 transition ml-auto";
            }
          }, 5000);
          return;
        }

        try {
          deleteBtn.disabled = true;
          deleteBtn.textContent = "Siliniyor…";
          await api("DELETE", `/api/records/${rec.id}`);
          toast(`"${rec.title}" arşivden başarıyla silindi! 🗑️`);
          hideModal(detailModal);
          fetchRecords();
          fetchSummary();
        } catch (e) {
          toast("Silme hatası: " + e.message, "error");
          deleteArmed = false;
          if (deleteBtn) {
            deleteBtn.disabled = false;
            deleteBtn.textContent = "Sil";
          }
        }
      });
    } catch (err) {
      modalContent.innerHTML = `<div class="p-6 text-center text-red-400">Detay yüklenemedi: ${err.message}</div>`;
    }
  }

  // ── Multi-Source Roulette ("Ne İzlesem?") ─────────────
  rouletteButton?.addEventListener("click", () => {
    showModal(rouletteModal);
    spinRoulette(state.rouletteSource);
  });
  closeRouletteModal?.addEventListener("click", () => hideModal(rouletteModal));

  function setRouletteSourceTab(src) {
    state.rouletteSource = src;
    rouletteSourceTmdb.className = `flex-1 py-1.5 text-[11px] font-bold uppercase tracking-wider transition ${src === "tmdb" ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-400"}`;
    rouletteSourceImdb.className = `flex-1 py-1.5 text-[11px] font-bold uppercase tracking-wider transition ${src === "imdb" ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-400"}`;
    rouletteSourceArchive.className = `flex-1 py-1.5 text-[11px] font-bold uppercase tracking-wider transition ${src === "archive" ? "bg-zinc-100 text-zinc-900" : "bg-zinc-800 text-zinc-400"}`;
    spinRoulette(src);
  }

  rouletteSourceTmdb?.addEventListener("click", () => setRouletteSourceTab("tmdb"));
  rouletteSourceImdb?.addEventListener("click", () => setRouletteSourceTab("imdb"));
  rouletteSourceArchive?.addEventListener("click", () => setRouletteSourceTab("archive"));
  spinAgainBtn?.addEventListener("click", () => spinRoulette(state.rouletteSource));

  async function spinRoulette(source) {
    if (!rouletteCard) return;
    rouletteCard.innerHTML = `<div class="text-center text-zinc-400 py-10 animate-pulse">🎲 Çark dönüyor, öneri çekiliyor…</div>`;
    rouletteActionBtn.disabled = true;

    try {
      const data = await api("GET", `/api/discover/random?source=${source}`);
      const item = data.item;
      state.currentRouletteItem = item;
      const isArchive = data.source === "archive";

      const title = item.title || item.name || "Untitled";
      const year = item.release_year || (item.release_date ? item.release_date.slice(0, 4) : "—");
      const poster = item.poster_preview || item.poster_url || (item.poster_path ? `https://image.tmdb.org/t/p/w300${item.poster_path}` : null);
      const rating = item.rating || item.imdb_rating || item.tmdb_rating;
      const overview = item.overview || item.note || "";

      rouletteCard.innerHTML = `
        <div class="flex gap-4 w-full text-left">
          ${poster ? `<img src="${poster}" alt="${title}" class="w-28 shrink-0 object-cover shadow-lg border border-zinc-700" />` : `<div class="w-28 bg-zinc-800 shrink-0 flex items-center justify-center text-zinc-500 text-xs">Afiş Yok</div>`}
          <div class="flex-1 min-w-0 flex flex-col justify-between">
            <div>
              <div class="flex items-center gap-2 mb-1">
                <span class="text-[9px] font-bold uppercase px-1.5 py-0.5 bg-purple-900/60 text-purple-200 border border-purple-700/50">${data.source.toUpperCase()}</span>
                <span class="text-xs text-zinc-400">${year}</span>
                ${rating ? `<span class="mono text-xs font-bold text-amber-400 ml-auto">★ ${Number(rating).toFixed(1)}</span>` : ""}
              </div>
              <h4 class="text-base font-bold text-white leading-snug">${title}</h4>
              <p class="text-xs text-zinc-300 mt-2 line-clamp-4 leading-relaxed">${overview || "Açıklama mevcut değil."}</p>
            </div>
          </div>
        </div>`;

      rouletteActionBtn.disabled = false;
      if (isArchive) {
        rouletteActionBtn.textContent = "Detayı Aç ↗";
        rouletteActionBtn.className = "flex-1 bg-zinc-100 hover:bg-white text-zinc-900 py-2 text-xs font-semibold uppercase tracking-wider transition";
      } else {
        rouletteActionBtn.textContent = "+ Arşive Ekle";
        rouletteActionBtn.className = "flex-1 bg-emerald-700 hover:bg-emerald-600 text-white py-2 text-xs font-semibold uppercase tracking-wider transition";
      }
    } catch (err) {
      rouletteCard.innerHTML = `<div class="text-center text-red-400 py-10">${err.message}</div>`;
      rouletteActionBtn.disabled = true;
    }
  }

  rouletteActionBtn?.addEventListener("click", async () => {
    const item = state.currentRouletteItem;
    if (!item) return;
    if (state.rouletteSource === "archive") {
      hideModal(rouletteModal);
      openDetail(item.id);
    } else if (state.rouletteSource === "tmdb" && item.tmdb_id) {
      rouletteActionBtn.textContent = "Ekleniyor…";
      rouletteActionBtn.disabled = true;
      try {
        const res = await api("POST", `/api/tmdb/import/${item.tmdb_id}`, { media_type: item.media_type || "movie" });
        toast(`"${res.title || item.title}" arşive eklendi!`);
        hideModal(rouletteModal);
        fetchRecords();
        fetchSummary();
      } catch (e) { toast("Ekleme hatası: " + e.message, "error"); }
    } else if (state.rouletteSource === "imdb" && item.imdb_id) {
      rouletteActionBtn.textContent = "Ekleniyor…";
      rouletteActionBtn.disabled = true;
      try {
        const res = await api("POST", `/api/imdb/import/${item.imdb_id}`, { media_type: item.media_type || "movie", poster_url: item.poster_url });
        toast(`"${res.title || item.title}" arşive eklendi!`);
        hideModal(rouletteModal);
        fetchRecords();
        fetchSummary();
      } catch (e) { toast("Ekleme hatası: " + e.message, "error"); }
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
          <input id="imdbSearchInput" type="text" placeholder="IMDb'de film veya dizi ara (örn: The Dark Knight, Fight Club)..." class="w-full bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder:text-zinc-500 outline-none focus:border-zinc-500" />
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
          <input id="manualTags" type="text" placeholder="Etiketler (Örn: Bilim Kurgu, Favoriler)" class="bg-zinc-800 border border-zinc-700 px-3 py-2 text-xs text-zinc-200 outline-none" />
          <textarea id="manualNote" placeholder="Özet / Kişisel Not (isteğe bağlı)" rows="2" class="bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder:text-zinc-500 outline-none resize-none"></textarea>
          <button id="manualSubmit" class="bg-zinc-100 text-zinc-900 px-4 py-2 text-xs font-semibold uppercase tracking-wider hover:bg-white transition">Kaydet</button>
        </div>
      </div>`;

    showModal(addModal);
    setTimeout(() => $("imdbSearchInput")?.focus(), 60);

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
              toast(`"${result.title || "Kayıt"}" otomatik etiketlerle eklendi!`);
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
              toast(`"${result.title || "Kayıt"}" otomatik etiketlerle eklendi!`);
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
    const tagsVal = $("manualTags")?.value.trim() || "";
    const tagsArr = tagsVal ? tagsVal.split(",").map(t => t.trim()).filter(Boolean) : null;
    const body = {
      title,
      media_type: $("manualType")?.value || "movie",
      is_anime: $("manualAnime")?.checked || false,
      release_year: $("manualYear")?.value ? parseInt($("manualYear").value) : null,
      rating: $("manualRating")?.value ? parseInt($("manualRating").value) : null,
      status: $("manualStatus")?.value || "planned",
      tags: tagsArr,
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

  // ── Events & Live Autocomplete Search ─────────────────
  const searchDropdown = $("searchDropdown");

  refreshButton?.addEventListener("click", () => { fetchSummary(); fetchRecords(); });
  $("clearAllFiltersBtn")?.addEventListener("click", () => {
    state.query = "";
    if (searchInput) searchInput.value = "";
    state.favorite = false;
    state.min_rating = null;
    state.status = "";
    state.kind = "all";
    state.min_year = "";
    state.max_year = "";
    state.tag = "";
    state.offset = 0;
    toast("Tüm filtreler sıfırlandı");
    fetchRecords();
    fetchSummary();
  });
  addButton?.addEventListener("click", openAddModal);

  searchInput?.addEventListener("input", (e) => {
    const q = e.target.value.trim();
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
      state.query = q;
      state.offset = 0;
      fetchRecords();

      // Live Dropdown preview for quick jumps
      if (q.length >= 2 && searchDropdown) {
        try {
          const res = await api("GET", `/api/records?q=${encodeURIComponent(q)}&limit=4`);
          if (res.records && res.records.length > 0) {
            searchDropdown.classList.remove("hidden");
            searchDropdown.innerHTML = res.records.map(r => {
              const poster = r.poster_url;
              return `
                <div class="search-drop-item flex items-center gap-3 p-2.5 hover:bg-zinc-800 cursor-pointer transition" data-id="${r.id}">
                  ${poster ? `<img src="${poster}" class="w-8 aspect-[2/3] object-cover shrink-0" />` : `<div class="w-8 aspect-[2/3] bg-zinc-800 shrink-0 text-[8px] flex items-center justify-center text-zinc-400">Afiş</div>`}
                  <div class="min-w-0 flex-1">
                    <p class="text-xs font-bold text-white truncate">${r.title}</p>
                    <div class="flex items-center gap-2 text-[10px] text-zinc-400">
                      <span>${r.release_year || "—"}</span>
                      <span class="mono text-amber-400">★ ${r.rating || (r.imdb_rating ? "IMDb " + r.imdb_rating : "—")}</span>
                      <span class="text-zinc-500">${r.media_type === "movie" ? "Film" : "Dizi"}</span>
                    </div>
                  </div>
                </div>`;
            }).join("");

            searchDropdown.querySelectorAll(".search-drop-item").forEach(item => {
              item.addEventListener("click", () => {
                const id = parseInt(item.dataset.id);
                searchDropdown.classList.add("hidden");
                openDetail(id);
              });
            });
          } else {
            searchDropdown.classList.add("hidden");
          }
        } catch {
          searchDropdown.classList.add("hidden");
        }
      } else {
        searchDropdown?.classList.add("hidden");
      }
    }, 250);
  });

  document.addEventListener("click", (e) => {
    if (searchDropdown && !searchDropdown.contains(e.target) && e.target !== searchInput) {
      searchDropdown.classList.add("hidden");
    }
  });

  sortSelect?.addEventListener("change", (e) => { state.sort = e.target.value; state.offset = 0; fetchRecords(); });
  directionButton?.addEventListener("click", () => { state.dir = state.dir === "desc" ? "asc" : "desc"; directionButton.textContent = state.dir === "desc" ? "Azalan ↓" : "Artan ↑"; state.offset = 0; fetchRecords(); });
  pageSizeSelect?.addEventListener("change", (e) => { state.limit = parseInt(e.target.value) || 50; state.offset = 0; fetchRecords(); });
  prevButton?.addEventListener("click", () => { if (state.offset > 0) { state.offset = Math.max(0, state.offset - state.limit); fetchRecords(); } });
  nextButton?.addEventListener("click", () => { if (state.offset + state.limit < state.total) { state.offset += state.limit; fetchRecords(); } });

  // ── Quick Filter Chips ────────────────────────────────
  document.querySelectorAll(".quick-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".quick-filter-btn").forEach(b => {
        b.className = "quick-filter-btn shrink-0 h-7 px-3 text-xs font-medium bg-zinc-100 dark:bg-zinc-800/80 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition border border-zinc-200 dark:border-zinc-700/60";
      });
      btn.className = "quick-filter-btn shrink-0 h-7 px-3 text-xs font-semibold bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950 transition border border-transparent";

      const f = btn.dataset.filter;
      state.offset = 0;
      state.favorite = false;
      if (f === "all") {
        state.kind = "all"; state.status = ""; state.sort = "updated_at"; state.query = "";
      } else if (f === "favorites") {
        state.favorite = true;
      } else if (f === "top_rated") {
        state.sort = "rating"; state.dir = "desc";
      } else if (f === "planned") {
        state.status = "planned";
      } else if (f === "completed") {
        state.status = "completed";
      } else if (f === "movies") {
        state.kind = "movie";
      } else if (f === "series") {
        state.kind = "series";
      }
      fetchRecords();
    });
  });

  // ── Mood / Vibe Filter Buttons ────────────────────────
  document.querySelectorAll(".mood-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const mood = btn.dataset.mood;
      if (searchInput) searchInput.value = mood;
      state.query = mood;
      state.offset = 0;
      toast(`🍿 "${btn.textContent.trim()}" modu seçildi`);
      fetchRecords();
    });
  });

  // ── Decade Filter Buttons ─────────────────────────────
  document.querySelectorAll(".decade-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".decade-filter-btn").forEach(b => {
        b.className = "decade-filter-btn shrink-0 h-7 px-2.5 text-xs font-medium bg-zinc-100 dark:bg-zinc-800/60 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700/60 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition";
      });
      btn.className = "decade-filter-btn shrink-0 h-7 px-2.5 text-xs font-semibold bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950 border border-transparent transition";

      const d = btn.dataset.decade;
      state.offset = 0;
      if (d === "2020s") {
        state.min_year = 2020; state.max_year = 2029;
      } else if (d === "2010s") {
        state.min_year = 2010; state.max_year = 2019;
      } else if (d === "2000s") {
        state.min_year = 2000; state.max_year = 2009;
      } else if (d === "1990s") {
        state.min_year = 1990; state.max_year = 1999;
      } else if (d === "classics") {
        state.min_year = ""; state.max_year = 1989;
      } else {
        state.min_year = ""; state.max_year = "";
      }
      toast(`🎞️ "${btn.textContent.trim()}" dönemi seçildi`);
      fetchRecords();
    });
  });

  // ── Rating Filter Buttons ─────────────────────────────
  document.querySelectorAll(".rating-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".rating-filter-btn").forEach(b => {
        b.className = "rating-filter-btn shrink-0 h-7 px-2.5 text-xs font-medium bg-zinc-100 dark:bg-zinc-800/60 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700/60 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition";
      });
      btn.className = "rating-filter-btn shrink-0 h-7 px-2.5 text-xs font-semibold bg-zinc-950 dark:bg-zinc-100 text-white dark:text-zinc-950 border border-transparent transition";

      const r = parseInt(btn.dataset.ratingFilter);
      state.offset = 0;
      state.min_rating = r;
      state.sort = "rating";
      state.dir = "desc";
      toast(`⭐ "${btn.textContent.trim()}" filtresi uygulandı`);
      fetchRecords();
    });
  });

  // ── Keyboard Shortcuts (Ctrl+K or /) ──────────────────
  window.addEventListener("keydown", (e) => {
    if ((e.key === "/" || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")) && document.activeElement !== searchInput && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
      e.preventDefault();
      if (state.view !== "gallery") switchView("gallery");
      searchInput?.focus();
      searchInput?.select();
    }
  });

  const ticketModal = $("ticketModal");
  const closeTicketBtn = $("closeTicketBtn");
  const copyTicketTextBtn = $("copyTicketTextBtn");

  closeTicketBtn?.addEventListener("click", () => hideModal(ticketModal));
  copyTicketTextBtn?.addEventListener("click", () => {
    const title = $("ticketTitle")?.textContent;
    const rating = $("ticketRating")?.textContent;
    const date = $("ticketDate")?.textContent;
    const dir = $("ticketDirector")?.textContent;
    const num = $("ticketNo")?.textContent;

    const text = `🎟️ **SİNEMA BİLETİ (${num})**\n` +
      `🎬 **Film:** ${title}\n` +
      `👤 **Yönetmen:** ${dir}\n` +
      `⭐ **Puan:** ${rating}\n` +
      `📅 **İzleme Tarihi:** ${date}\n` +
      `🍿 *Media Tracker Kişisel Arşivi*`;

    navigator.clipboard.writeText(text).then(() => {
      toast("🎟️ Sinema bileti metni kopyalandı!");
    }).catch(() => {
      toast("Kopyalama başarısız oldu", "error");
    });
  });

  // ── Marathon Planner ──────────────────────────────────
  const marathonModal = $("marathonModal");
  const marathonButton = $("marathonButton");
  const closeMarathonBtn = $("closeMarathonBtn");
  const marathonResult = $("marathonResult");
  const marathonRerollBtn = $("marathonRerollBtn");
  let marathonSelectedHours = 2;

  marathonButton?.addEventListener("click", () => {
    showModal(marathonModal);
    generateMarathon(marathonSelectedHours);
  });
  closeMarathonBtn?.addEventListener("click", () => hideModal(marathonModal));

  document.querySelectorAll(".marathon-time-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".marathon-time-btn").forEach(b => {
        b.className = "marathon-time-btn flex-1 py-2 text-xs font-bold uppercase bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition";
      });
      btn.className = "marathon-time-btn flex-1 py-2 text-xs font-bold uppercase bg-amber-500 text-zinc-950 transition";
      marathonSelectedHours = parseInt(btn.dataset.hours) || 2;
      generateMarathon(marathonSelectedHours);
    });
  });

  marathonRerollBtn?.addEventListener("click", () => generateMarathon(marathonSelectedHours));

  async function generateMarathon(targetHours) {
    if (!marathonResult) return;
    marathonResult.innerHTML = `<div class="p-4 text-center text-zinc-400 animate-pulse text-xs">Arşivden maraton seansı hesaplanıyor…</div>`;
    try {
      const data = await api("GET", "/api/records?limit=100");
      const pool = (data.records || []).filter(r => r.media_type === "movie" && r.runtime);
      if (!pool.length) {
        marathonResult.innerHTML = `<p class="text-xs text-zinc-400 text-center py-4">Süresi kayıtlı film bulunamadı. Lütfen birkaç film ekleyin.</p>`;
        return;
      }

      // Shuffle pool
      const shuffled = [...pool].sort(() => Math.random() - 0.5);
      const targetMins = targetHours * 60;
      let currentMins = 0;
      const selected = [];

      for (const m of shuffled) {
        const rt = m.runtime || 100;
        if (currentMins + rt <= targetMins + 35) {
          selected.push(m);
          currentMins += rt;
          if (currentMins >= targetMins - 20) break;
        }
      }

      if (!selected.length && pool.length) {
        selected.push(pool[0]);
        currentMins = pool[0].runtime || 100;
      }

      // Calculate timeline schedule
      let now = new Date();
      let scheduleHtml = `<div class="mb-3 flex items-center justify-between pb-2 border-b border-zinc-800 text-xs"><span class="font-bold text-amber-400">Toplam Süre: ${currentMins} dakika (~${Math.round(currentMins/60*10)/10} saat)</span><span class="mono text-zinc-400">${selected.length} Film</span></div>`;
      scheduleHtml += `<div class="space-y-2.5">`;

      selected.forEach((m, idx) => {
        const startStr = now.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
        now.setMinutes(now.getMinutes() + (m.runtime || 100));
        const endStr = now.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
        const poster = m.poster_url;

        scheduleHtml += `
          <div class="flex items-center gap-3 p-2 bg-zinc-900 border border-zinc-800">
            <span class="mono text-xs font-bold text-amber-400 shrink-0 w-24">${startStr} – ${endStr}</span>
            ${poster ? `<img src="${poster}" class="w-8 aspect-[2/3] object-cover shrink-0" />` : `<div class="w-8 aspect-[2/3] bg-zinc-800 shrink-0"></div>`}
            <div class="min-w-0 flex-1">
              <p class="font-bold text-zinc-100 text-xs truncate">${m.title}</p>
              <p class="text-[10px] text-zinc-400">${m.runtime} dk • ★ ${m.rating || m.imdb_rating || "—"}</p>
            </div>
            <button class="text-xs text-zinc-400 hover:text-white px-2 py-1 bg-zinc-800" onclick="window.__openDetail(${m.id})">Detay ↗</button>
          </div>
        `;

        if (idx < selected.length - 1) {
          now.setMinutes(now.getMinutes() + 15); // 15 min break
          const breakEnd = now.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
          scheduleHtml += `
            <div class="flex items-center justify-center gap-2 py-1 text-[10px] font-mono text-zinc-500">
              <span>☕ 15 dk Mola (Bitiş: ${breakEnd})</span>
            </div>`;
        }
      });

      scheduleHtml += `</div>`;
      marathonResult.innerHTML = scheduleHtml;
    } catch (e) {
      marathonResult.innerHTML = `<div class="text-red-400 text-xs">Hata: ${e.message}</div>`;
    }
  }

  // ── Search Clear Button ──────────────────────────────
  const searchClearBtn = $("searchClearBtn");
  if (searchInput && searchClearBtn) {
    searchInput.addEventListener("input", () => {
      searchClearBtn.classList.toggle("hidden", !searchInput.value.trim());
    });
    searchClearBtn.addEventListener("click", () => {
      searchInput.value = "";
      state.query = "";
      state.offset = 0;
      searchClearBtn.classList.add("hidden");
      if (searchDropdown) searchDropdown.classList.add("hidden");
      fetchRecords();
    });
  }

  // ── Fullscreen Ambient Cinema Mode ─────────────────────
  const ambientModal = $("ambientModal");
  const ambientBtn = $("ambientBtn");
  const closeAmbientBtn = $("closeAmbientBtn");
  const ambientPoster = $("ambientPoster");
  const ambientGlow = $("ambientGlow");
  const ambientTitle = $("ambientTitle");
  const ambientYear = $("ambientYear");
  const ambientRating = $("ambientRating");
  const ambientType = $("ambientType");
  const ambientOverview = $("ambientOverview");
  const ambientIndex = $("ambientIndex");
  const ambientTrailerBtn = $("ambientTrailerBtn");
  const ambientOstLink = $("ambientOstLink");
  const ambientDetailBtn = $("ambientDetailBtn");
  const ambientPrevBtn = $("ambientPrevBtn");
  const ambientNextBtn = $("ambientNextBtn");

  let ambientRecords = [];
  let ambientCurIdx = 0;

  async function openAmbientMode(startIdx = 0) {
    if (!ambientModal) return;
    try {
      const data = await api("GET", "/api/records?limit=100");
      ambientRecords = data.records || [];
      if (!ambientRecords.length) {
        toast("Ambiyans modu için arşivde kayıt bulunamadı", "error");
        return;
      }
      ambientCurIdx = startIdx >= 0 && startIdx < ambientRecords.length ? startIdx : 0;
      renderAmbientCard(ambientCurIdx);
      showModal(ambientModal);
    } catch (e) {
      toast("Ambiyans modu başlatılamadı: " + e.message, "error");
    }
  }

  function renderAmbientCard(idx) {
    if (!ambientRecords.length || idx < 0 || idx >= ambientRecords.length) return;
    ambientCurIdx = idx;
    const rec = ambientRecords[idx];
    const poster = rec.poster_url;

    if (ambientPoster) {
      ambientPoster.src = poster || "";
      ambientPoster.classList.toggle("hidden", !poster);
    }
    if (ambientGlow) {
      ambientGlow.style.backgroundImage = poster ? `url('${poster}')` : "none";
    }
    if (ambientTitle) ambientTitle.textContent = rec.title;
    if (ambientYear) ambientYear.textContent = rec.release_year || "—";
    if (ambientRating) ambientRating.textContent = rec.rating ? `★ ${rec.rating}/10` : (rec.imdb_rating ? `IMDb ${Number(rec.imdb_rating).toFixed(1)}` : "★ Puanlanmadı");
    if (ambientType) ambientType.textContent = rec.media_type === "movie" ? (rec.is_anime ? "Anime Film" : "Film") : "Dizi";
    if (ambientOverview) ambientOverview.textContent = rec.overview || rec.note || "Bu yapım için henüz özet girilmedi.";
    if (ambientIndex) ambientIndex.textContent = `${idx + 1} / ${ambientRecords.length}`;

    if (ambientOstLink) {
      ambientOstLink.href = `https://open.spotify.com/search/${encodeURIComponent(rec.title + " soundtrack")}`;
    }

    if (ambientTrailerBtn) {
      ambientTrailerBtn.onclick = async () => {
        try {
          const tdata = await api("GET", `/api/records/${rec.id}/trailer`);
          if (trailerTitle) trailerTitle.textContent = `${rec.title} — Fragman`;
          if (trailerIframe) trailerIframe.src = tdata.trailer_url;
          showModal(trailerModal);
        } catch (e) {
          toast("Fragman bulunamadı: " + e.message, "error");
        }
      };
    }

    if (ambientDetailBtn) {
      ambientDetailBtn.onclick = () => {
        hideModal(ambientModal);
        openDetail(rec.id);
      };
    }
  }

  ambientBtn?.addEventListener("click", () => openAmbientMode(0));
  closeAmbientBtn?.addEventListener("click", () => hideModal(ambientModal));
  ambientPrevBtn?.addEventListener("click", () => {
    if (ambientCurIdx > 0) renderAmbientCard(ambientCurIdx - 1);
    else renderAmbientCard(ambientRecords.length - 1);
  });
  ambientNextBtn?.addEventListener("click", () => {
    if (ambientCurIdx < ambientRecords.length - 1) renderAmbientCard(ambientCurIdx + 1);
    else renderAmbientCard(0);
  });

  // ── Compare Movies Modal ──────────────────────────────
  const compareModal = $("compareModal");
  const compareBtn = $("compareBtn");
  const closeCompareBtn = $("closeCompareBtn");
  const compareSelect1 = $("compareSelect1");
  const compareSelect2 = $("compareSelect2");
  const compareSide1 = $("compareSide1");
  const compareSide2 = $("compareSide2");

  let allArchiveRecords = [];

  async function openCompareModal(id1 = null, id2 = null) {
    if (!compareModal) return;
    try {
      const data = await api("GET", "/api/records?limit=200");
      allArchiveRecords = data.records || [];
      if (allArchiveRecords.length < 2) {
        toast("Karşılaştırma için arşivde en az 2 kayıt olmalıdır", "error");
        return;
      }

      // Populate selects
      const optionsHtml = allArchiveRecords.map(r => `<option value="${r.id}">${r.title} (${r.release_year || '—'})</option>`).join("");
      if (compareSelect1) compareSelect1.innerHTML = optionsHtml;
      if (compareSelect2) compareSelect2.innerHTML = optionsHtml;

      if (id1 && compareSelect1) compareSelect1.value = id1;
      else if (compareSelect1) compareSelect1.value = allArchiveRecords[0].id;

      if (id2 && compareSelect2) compareSelect2.value = id2;
      else if (compareSelect2 && allArchiveRecords.length > 1) compareSelect2.value = allArchiveRecords[1].id;

      renderComparison();
      showModal(compareModal);
    } catch (e) {
      toast("Karşılaştırma açılamadı: " + e.message, "error");
    }
  }

  async function renderComparison() {
    if (!compareSelect1 || !compareSelect2) return;
    const id1 = parseInt(compareSelect1.value);
    const id2 = parseInt(compareSelect2.value);
    if (!id1 || !id2) return;

    try {
      const [r1, r2] = await Promise.all([
        api("GET", `/api/records/${id1}`),
        api("GET", `/api/records/${id2}`)
      ]);

      const renderSide = (r) => {
        const poster = r.poster_url;
        const genres = Array.isArray(r.genres) ? r.genres : [];
        return `
          <div class="space-y-3">
            <div class="w-full aspect-[2/3] max-w-[200px] mx-auto overflow-hidden bg-zinc-800 shadow-lg">
              ${poster ? `<img src="${poster}" class="w-full h-full object-cover" />` : `<div class="w-full h-full flex items-center justify-center text-zinc-500 text-xs">Afiş Yok</div>`}
            </div>
            <div class="text-center">
              <h3 class="font-bold text-base text-white leading-snug">${r.title}</h3>
              <p class="text-xs text-zinc-400 mt-0.5">${r.release_year || '—'} • ${r.media_type === 'movie' ? 'Film' : 'Dizi'}</p>
            </div>
            <div class="space-y-1.5 text-xs bg-zinc-950/60 p-3 border border-zinc-800">
              <div class="flex justify-between"><span class="text-zinc-400">Puan:</span> <b class="text-amber-400 mono">★ ${r.rating || '—'}/10</b></div>
              <div class="flex justify-between"><span class="text-zinc-400">IMDb Puanı:</span> <b class="text-yellow-400 mono">${r.imdb_rating ? Number(r.imdb_rating).toFixed(1) : '—'}</b></div>
              <div class="flex justify-between"><span class="text-zinc-400">TMDB Puanı:</span> <b class="text-cyan-400 mono">${r.tmdb_rating ? Number(r.tmdb_rating).toFixed(1) : '—'}</b></div>
              <div class="flex justify-between"><span class="text-zinc-400">Süre:</span> <span class="mono">${r.runtime ? `${r.runtime} dk` : '—'}</span></div>
              <div class="flex justify-between"><span class="text-zinc-400">Yönetmen:</span> <span class="font-medium">${r.director || '—'}</span></div>
              <div class="flex justify-between"><span class="text-zinc-400">Durum:</span> <span class="uppercase text-[10px] font-bold">${r.status === 'completed' ? 'İzlendi ✓' : 'Planlandı ⏳'}</span></div>
            </div>
            <div>
              <span class="text-[10px] uppercase font-bold text-zinc-400 block mb-1">Türler:</span>
              <div class="flex flex-wrap gap-1">
                ${genres.map(g => `<span class="text-[9px] px-1.5 py-0.5 bg-zinc-800 text-zinc-300">${g}</span>`).join("") || '<span class="text-zinc-500 text-xs">—</span>'}
              </div>
            </div>
            <p class="text-xs text-zinc-400 line-clamp-4 leading-relaxed">${r.overview || r.note || 'Özet girilmedi.'}</p>
            <button class="w-full bg-zinc-800 hover:bg-zinc-700 text-zinc-200 py-1.5 text-xs font-semibold uppercase tracking-wider transition" onclick="window.__openDetail(${r.id})">Detay Sayfası ↗</button>
          </div>
        `;
      };

      if (compareSide1) compareSide1.innerHTML = renderSide(r1);
      if (compareSide2) compareSide2.innerHTML = renderSide(r2);
    } catch (e) {
      toast("Karşılaştırma verisi çekilemedi: " + e.message, "error");
    }
  }

  compareBtn?.addEventListener("click", () => openCompareModal());
  closeCompareBtn?.addEventListener("click", () => hideModal(compareModal));
  compareSelect1?.addEventListener("change", renderComparison);
  compareSelect2?.addEventListener("change", renderComparison);

  // ── Shortcuts Modal & Global Hotkeys ───────────────────
  const shortcutsModal = $("shortcutsModal");
  const shortcutsBtn = $("shortcutsBtn");
  const closeShortcutsBtn = $("closeShortcutsBtn");

  shortcutsBtn?.addEventListener("click", () => showModal(shortcutsModal));
  closeShortcutsBtn?.addEventListener("click", () => hideModal(shortcutsModal));

  window.addEventListener("keydown", (e) => {
    const isInput = document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA" || document.activeElement?.tagName === "SELECT";
    
    // Quick search shortcut (Ctrl+K or /)
    if ((e.key === "/" || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")) && !isInput) {
      e.preventDefault();
      if (state.view !== "gallery") switchView("gallery");
      searchInput?.focus();
      searchInput?.select();
      return;
    }

    // Ambient arrow keys
    if (!ambientModal?.classList.contains("hidden")) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        ambientPrevBtn?.click();
        return;
      }
      if (e.key === "ArrowRight") {
        e.preventDefault();
        ambientNextBtn?.click();
        return;
      }
    }

    if (isInput) return;

    if (e.key === "?" || (e.shiftKey && e.key === "/")) {
      e.preventDefault();
      showModal(shortcutsModal);
    } else if (e.key.toLowerCase() === "g") {
      switchView("gallery");
    } else if (e.key.toLowerCase() === "a") {
      switchView("stats");
    } else if (e.key.toLowerCase() === "n") {
      openAddModal();
    } else if (e.key.toLowerCase() === "r") {
      openRouletteModal();
    } else if (e.key.toLowerCase() === "m") {
      showModal(marathonModal);
      generateMarathon(marathonSelectedHours);
    } else if (e.key.toLowerCase() === "f") {
      if (ambientModal?.classList.contains("hidden")) openAmbientMode(0);
      else hideModal(ambientModal);
    } else if (e.key.toLowerCase() === "c") {
      openCompareModal();
    } else if (e.key.toLowerCase() === "t") {
      toggleTheme();
    } else if (e.key === "1") {
      setGridDensity("compact");
    } else if (e.key === "2") {
      setGridDensity("normal");
    } else if (e.key === "3") {
      setGridDensity("large");
    }
  });

  const personModal = $("personModal");
  const closePersonBtn = $("closePersonBtn");
  closePersonBtn?.addEventListener("click", () => hideModal(personModal));

  // ── Mobile Controls & Bottom Navigation Listeners ─────
  const mobileNavGallery = $("mobileNavGallery");
  const mobileNavSearch = $("mobileNavSearch");
  const mobileNavAdd = $("mobileNavAdd");
  const mobileHeaderAddBtn = $("mobileHeaderAddBtn");
  const mobileNavStats = $("mobileNavStats");
  const mobileNavTools = $("mobileNavTools");
  const openMobileToolsTopBtn = $("openMobileToolsTopBtn");
  const mobileToolsModal = $("mobileToolsModal");
  const closeMobileToolsBtn = $("closeMobileToolsBtn");
  const mobileRefreshBtn = $("mobileRefreshBtn");
  const mobileThemeToggle = $("mobileThemeToggle");
  const mobileFilterToggleBtn = $("mobileFilterToggleBtn");
  const mobileFilterToggleIcon = $("mobileFilterToggleIcon");
  const sidebarAside = $("sidebarAside");

  mobileNavGallery?.addEventListener("click", () => {
    switchView("gallery");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  mobileNavSearch?.addEventListener("click", () => {
    switchView("gallery");
    if (sidebarAside && sidebarAside.classList.contains("mobile-hidden")) {
      sidebarAside.classList.remove("mobile-hidden");
      if (mobileFilterToggleIcon) mobileFilterToggleIcon.textContent = "▲ Gizle";
    }
    const searchInput = $("searchInput");
    if (searchInput) {
      searchInput.focus();
      searchInput.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

  mobileNavAdd?.addEventListener("click", openAddModal);
  mobileHeaderAddBtn?.addEventListener("click", openAddModal);

  mobileNavStats?.addEventListener("click", () => {
    switchView("stats");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  const openMobileTools = () => {
    if (mobileToolsModal) showModal(mobileToolsModal);
  };
  mobileNavTools?.addEventListener("click", openMobileTools);
  openMobileToolsTopBtn?.addEventListener("click", openMobileTools);
  closeMobileToolsBtn?.addEventListener("click", () => {
    if (mobileToolsModal) hideModal(mobileToolsModal);
  });

  // Mobile tools sheet items
  $("mobileToolRoulette")?.addEventListener("click", () => {
    if (mobileToolsModal) hideModal(mobileToolsModal);
    openRouletteModal();
  });
  $("mobileToolMarathon")?.addEventListener("click", () => {
    if (mobileToolsModal) hideModal(mobileToolsModal);
    showModal(marathonModal);
    generateMarathon(marathonSelectedHours);
  });
  $("mobileToolAmbient")?.addEventListener("click", () => {
    if (mobileToolsModal) hideModal(mobileToolsModal);
    openAmbientMode(0);
  });
  $("mobileToolCompare")?.addEventListener("click", () => {
    if (mobileToolsModal) hideModal(mobileToolsModal);
    openCompareModal();
  });
  $("mobileToolImportExport")?.addEventListener("click", () => {
    if (mobileToolsModal) hideModal(mobileToolsModal);
    openImportExportModal();
  });
  $("mobileToolShortcuts")?.addEventListener("click", () => {
    if (mobileToolsModal) hideModal(mobileToolsModal);
    showModal(shortcutsModal);
  });

  mobileRefreshBtn?.addEventListener("click", () => {
    fetchRecords();
    fetchSummary();
    toast("Arşiv verileri güncellendi");
  });

  mobileThemeToggle?.addEventListener("click", () => {
    const isDark = document.documentElement.classList.contains("dark");
    applyTheme(!isDark);
  });

  mobileFilterToggleBtn?.addEventListener("click", () => {
    if (!sidebarAside) return;
    const isHidden = sidebarAside.classList.contains("mobile-hidden");
    sidebarAside.classList.toggle("mobile-hidden", !isHidden);
    if (mobileFilterToggleIcon) {
      mobileFilterToggleIcon.textContent = isHidden ? "▲ Gizle" : "▼ Göster";
    }
  });

  const allModals = [detailModal, addModal, rouletteModal, trailerModal, importExportModal, ticketModal, personModal, marathonModal, shortcutsModal, ambientModal, compareModal, mobileToolsModal];

  allModals.forEach((m) => {
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
      allModals.forEach((m) => {
        if (m && !m.classList.contains("hidden")) {
          if (m === trailerModal && trailerIframe) trailerIframe.src = "";
          hideModal(m);
        }
      });
    }
  });

  // Check initial hash/path
  if (window.location.hash === "#analytics" || window.location.pathname === "/stats" || window.location.pathname === "/analytics") {
    switchView("stats");
  }

  // ── Init ───────────────────────────────────────────────
  initTheme();
  fetchSummary();
  fetchRecords();
})();
