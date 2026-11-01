import os
import json
import time
import urllib.parse
from collections import Counter
from datetime import datetime
import requests
from flask import Flask, render_template_string, jsonify, request, Response, redirect
from google.cloud import bigquery

app = Flask(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT", "secret-compass-181513")
DATASET_NAME = os.getenv("BQ_DATASET", "spotify")

# Cache query results in memory to make dashboard snappy
CACHE_TTL = 600  # 10 minutes
_cached_data = None
_cache_time = 0

# Cache for audio preview & Apple Music lookups
_preview_cache = {}


def fetch_album_data():
    global _cached_data, _cache_time
    now = time.time()
    if _cached_data is not None and (now - _cache_time) < CACHE_TTL:
        return _cached_data

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
    SELECT
      coalesce(album_name, 'Unknown Album') as album_name,
      coalesce(album_artist_name, 'Unknown Artist') as album_artist_name,
      added_at,
      album_release_date,
      album_type,
      album_label,
      coalesce(album_tracks_total, 0) as album_tracks_total,
      album_image_url,
      coalesce(album_genres, '') as album_genres,
      coalesce(album_track_plays, 0) as album_track_plays,
      coalesce(album_plays, 0.0) as album_plays,
      coalesce(album_url, 'https://open.spotify.com') as album_url
    FROM
      `{PROJECT_ID}.{DATASET_NAME}.all_albums_features`
    ORDER BY
      album_plays DESC, added_at DESC
    """
    df = client.query(query).to_dataframe()

    # Preprocess dates and years
    df["release_year"] = df["album_release_date"].apply(
        lambda x: str(x)[:4] if x and str(x)[:4].isdigit() else "Unknown"
    )

    albums = df.to_dict(orient="records")

    # Compute genre frequencies for filter dropdown
    genre_counter = Counter()
    for g_str in df["album_genres"]:
        if g_str:
            for g in g_str.split(", "):
                g_clean = g.strip().lower()
                if g_clean:
                    genre_counter[g_clean] += 1

    top_genres = [g for g, count in genre_counter.most_common(40)]

    # Compute summary KPIs
    total_albums = len(albums)
    played_albums = sum(1 for a in albums if a["album_track_plays"] > 0)
    unplayed_albums = total_albums - played_albums
    total_plays = sum(a["album_track_plays"] for a in albums)
    top_album = albums[0] if albums else None

    _cached_data = {
        "albums": albums,
        "top_genres": top_genres,
        "kpis": {
            "total_albums": total_albums,
            "played_albums": played_albums,
            "unplayed_albums": unplayed_albums,
            "pct_explored": round((played_albums / total_albums * 100), 1) if total_albums else 0,
            "total_plays": total_plays,
            "top_album": top_album["album_name"] if top_album else "N/A",
            "top_album_plays": int(top_album["album_plays"]) if top_album else 0,
        }
    }
    _cache_time = now
    return _cached_data


# ==============================================================================
# BRAND ICONS: 3 Distinct Turntable + Spotify Concepts
# ==============================================================================
ICON_A_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
  <defs>
    <style>
      @keyframes spin33 {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
      .spin-record {
        transform-origin: 48px 52px;
        animation: spin33 1.8s linear infinite;
      }
    </style>
  </defs>
  <!-- Spinning Vinyl Platter (33 RPM = 1.80s per revolution) -->
  <g class="spin-record">
    <!-- Vinyl Platter Base / Dark Rim -->
    <circle cx="48" cy="52" r="46" fill="#0C0F12" stroke="#1DB954" stroke-width="3"/>
    <!-- Spotify Green Core Platter -->
    <circle cx="48" cy="52" r="40" fill="#1DB954"/>
    <!-- Spotify Soundwaves in Bold Black -->
    <path d="M30 40c9-2.5 19-1.5 27 3" stroke="#0C0F12" stroke-width="5" stroke-linecap="round"/>
    <path d="M33 49c8-1.8 16-1 22 2.5" stroke="#0C0F12" stroke-width="4.2" stroke-linecap="round"/>
    <path d="M36 58c6-1.2 12-0.5 17 2" stroke="#0C0F12" stroke-width="3.5" stroke-linecap="round"/>
    <!-- Center Spindle -->
    <circle cx="48" cy="52" r="5" fill="#0C0F12"/>
  </g>
  <!-- Stationary Tonearm & Pivot (Does NOT rotate) -->
  <circle cx="86" cy="14" r="9" fill="#181D22" stroke="#9CA3AF" stroke-width="3"/>
  <circle cx="86" cy="14" r="4" fill="#1DB954"/>
  <!-- Metallic Tonearm Rod in Bright White -->
  <path d="M83 19 L66 62 L52 68" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
  <!-- Cartridge / Headshell Needle -->
  <rect x="43" y="63" width="11" height="8" rx="2" fill="#0C0F12" stroke="#1DB954" stroke-width="1.5" transform="rotate(-22 48 67)"/>
</svg>"""

ICON_B_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
  <circle cx="50" cy="50" r="45" fill="#12161A" stroke="#28323C" stroke-width="3"/>
  <circle cx="43" cy="51" r="33" fill="#0C0F12" stroke="#1F2937" stroke-width="1.5"/>
  <circle cx="43" cy="51" r="25" fill="#1DB954"/>
  <path d="M33 44c5.5-1.5 12-1 16 1.8" stroke="#0C0F12" stroke-width="3.2" stroke-linecap="round"/>
  <path d="M35 50c4.5-1 9-0.5 13 1.5" stroke="#0C0F12" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M37 55c3-0.5 6.5-0.2 9 1.2" stroke="#0C0F12" stroke-width="2" stroke-linecap="round"/>
  <circle cx="43" cy="51" r="2.5" fill="#0C0F12"/>
  <circle cx="78" cy="23" r="6" fill="#374151" stroke="#9CA3AF" stroke-width="2"/>
  <path d="M76 27 L64 61 L54 65" stroke="#F3F4F6" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="48" y="61" width="7" height="5" rx="1" fill="#1DB954" transform="rotate(-20 51.5 63.5)"/>
</svg>"""

ICON_C_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
  <rect x="6" y="6" width="88" height="88" rx="22" fill="#0C0F12" stroke="#1DB954" stroke-width="3"/>
  <circle cx="42" cy="52" r="28" fill="#181D22"/>
  <circle cx="42" cy="52" r="20" fill="#1DB954"/>
  <path d="M34 47c4-1 8.5-0.7 11.5 1.2" stroke="#0C0F12" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M36 51c3-0.8 6.5-0.4 9 1" stroke="#0C0F12" stroke-width="2" stroke-linecap="round"/>
  <circle cx="42" cy="52" r="2.5" fill="#0C0F12"/>
  <circle cx="80" cy="22" r="6" fill="#1DB954"/>
  <path d="M78 26 C 78 52, 65 64, 52 64" stroke="#E5E7EB" stroke-width="3.5" stroke-linecap="round"/>
  <rect x="45" y="60" width="8" height="6" rx="1.5" fill="#1DB954" transform="rotate(-10 49 63)"/>
</svg>"""


# ==============================================================================
# TAB 1: LIBRARY EXPLORER
# ==============================================================================
EXPLORER_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve - Spotify Album Dashboard</title>
    <!-- SpinSleeve Full-Bleed Turntable Tab Icon -->
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' fill='none'%3E%3Ccircle cx='48' cy='52' r='46' fill='%230C0F12' stroke='%231DB954' stroke-width='3'/%3E%3Ccircle cx='48' cy='52' r='40' fill='%231DB954'/%3E%3Cpath d='M30 40c9-2.5 19-1.5 27 3' stroke='%230C0F12' stroke-width='5' stroke-linecap='round'/%3E%3Cpath d='M33 49c8-1.8 16-1 22 2.5' stroke='%230C0F12' stroke-width='4.2' stroke-linecap='round'/%3E%3Cpath d='M36 58c6-1.2 12-0.5 17 2' stroke='%230C0F12' stroke-width='3.5' stroke-linecap='round'/%3E%3Ccircle cx='48' cy='52' r='5' fill='%230C0F12'/%3E%3Ccircle cx='86' cy='14' r='9' fill='%23181D22' stroke='%239CA3AF' stroke-width='3'/%3E%3Ccircle cx='86' cy='14' r='4' fill='%231DB954'/%3E%3Cpath d='M83 19 L66 62 L52 68' stroke='%23FFFFFF' stroke-width='4.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3Crect x='43' y='63' width='11' height='8' rx='2' fill='%230C0F12' stroke='%231DB954' stroke-width='1.5' transform='rotate(-22 48 67)'/%3E%3C/svg%3E">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
        .card-bg { background-color: #181d22; }
        .card-bg:hover { background-color: #21272e; }
        .badge-fav { background: linear-gradient(135deg, #1DB954 0%, #15803d 100%); }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">

    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-4 border-b border-gray-800 gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 flex-shrink-0">
                        {{ brand_icon | safe }}
                    </div>
                    <h1 class="text-3xl font-extrabold tracking-tight text-white">SpinSleeve</h1>
                </div>
                <p class="text-xs text-gray-400 mt-1">Personal catalog & smart playlist explorer</p>
            </div>

            <!-- Header Quick Actions & Audio Preview Controls -->
            <div class="flex flex-wrap items-center gap-2.5">
                <!-- Hover Audio Mute/Unmute Toggle -->
                <button id="audioToggleBtn" onclick="toggleHoverAudio()"
                        class="text-xs font-semibold px-3 py-2 rounded-lg border border-gray-700 bg-gray-800/80 text-gray-300 hover:text-white flex items-center gap-1.5 transition"
                        title="Toggle 30-second audio snippet on album hover">
                    <span id="audioIcon">🔊</span> <span id="audioText">Hover Audio: ON</span>
                </button>

                <button onclick="resetFilters()" class="text-xs text-gray-400 hover:text-white bg-gray-800/80 hover:bg-gray-700 px-3 py-2 rounded-lg border border-gray-700 transition">
                    Reset
                </button>
                <a href="https://open.spotify.com" target="_blank" class="text-xs font-semibold text-black bg-[#1DB954] hover:bg-[#1ed760] px-3.5 py-2 rounded-lg transition shadow-sm">
                    Open Spotify
                </a>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="flex items-center gap-2 mb-6 border-b border-gray-800 pb-3">
            <a href="/" class="px-4 py-2 rounded-lg text-xs font-bold transition bg-[#1DB954]/15 text-[#1DB954] border border-[#1DB954]/30 flex items-center gap-2">
                <span>📚</span> Library Explorer
            </a>
            <a href="/recommend" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📻</span> Crate Digger
                <span class="bg-[#1DB954]/20 text-[#1DB954] text-[9px] font-bold px-1.5 py-0.5 rounded-full">RECOMMENDER</span>
            </a>
        </nav>

        <!-- KPI Metrics Ribbon (Updates Dynamically) -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="card-bg p-4 rounded-xl border border-gray-800 shadow-sm">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Filtered Albums</p>
                <p id="kpiTotalAlbums" class="text-2xl font-black mt-1 text-white">{{ kpis.total_albums }}</p>
            </div>
            <div class="card-bg p-4 rounded-xl border border-gray-800 shadow-sm">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Library Explored</p>
                <p id="kpiPctExplored" class="text-2xl font-black mt-1 text-[#1DB954]">{{ kpis.pct_explored }}%</p>
                <p id="kpiPlayedSubtext" class="text-[11px] text-gray-500 mt-0.5">{{ kpis.played_albums }} played / {{ kpis.unplayed_albums }} unplayed</p>
            </div>
            <div class="card-bg p-4 rounded-xl border border-gray-800 shadow-sm">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Total Album Plays</p>
                <p id="kpiTotalPlays" class="text-2xl font-black mt-1 text-white">{{ kpis.total_plays }}</p>
            </div>
            <div class="card-bg p-4 rounded-xl border border-gray-800 shadow-sm">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Top Album in Selection</p>
                <p id="kpiTopAlbum" class="text-base font-bold mt-1 text-white truncate" title="{{ kpis.top_album }}">{{ kpis.top_album }}</p>
                <p id="kpiTopAlbumPlays" class="text-[11px] text-[#1DB954] mt-0.5">{{ kpis.top_album_plays }} album plays</p>
            </div>
        </div>

        <!-- Filter Controls Toolbar -->
        <div class="card-bg p-4 rounded-xl border border-gray-800 mb-6 shadow-sm">
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 items-center">
                <!-- Search -->
                <div class="relative lg:col-span-2">
                    <input type="text" id="searchInput" placeholder="Search album or artist..."
                           class="w-full bg-[#11151a] border border-gray-700/80 rounded-lg px-3.5 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#1DB954] transition"
                           oninput="onFilterChange()">
                </div>

                <!-- Genre Selector -->
                <div>
                    <select id="genreFilter" class="w-full bg-[#11151a] border border-gray-700/80 rounded-lg p-2 text-sm text-gray-200 focus:outline-none focus:border-[#1DB954] transition" onchange="onFilterChange()">
                        <option value="">All Genres</option>
                        {% for g in top_genres %}
                        <option value="{{ g }}">{{ g|title }}</option>
                        {% endfor %}
                    </select>
                </div>

                <!-- Status Filter -->
                <div>
                    <select id="statusFilter" class="w-full bg-[#11151a] border border-gray-700/80 rounded-lg p-2 text-sm text-gray-200 focus:outline-none focus:border-[#1DB954] transition" onchange="onFilterChange()">
                        <option value="all">All Albums</option>
                        <option value="favorites">Favorites Only (Played)</option>
                        <option value="unplayed">Unplayed (Discover)</option>
                    </select>
                </div>

                <!-- Sort Order -->
                <div>
                    <select id="sortFilter" class="w-full bg-[#11151a] border border-gray-700/80 rounded-lg p-2 text-sm text-gray-200 focus:outline-none focus:border-[#1DB954] transition" onchange="onFilterChange()">
                        <option value="most_played">Sort: Most Played</option>
                        <option value="recently_added">Sort: Recently Added</option>
                        <option value="release_new">Sort: Release Year (Newest)</option>
                        <option value="release_old">Sort: Release Year (Oldest)</option>
                        <option value="alpha">Sort: Album (A-Z)</option>
                    </select>
                </div>
            </div>

            <!-- Active Results Bar -->
            <div class="flex items-center justify-between mt-3.5 pt-3 border-t border-gray-800 text-xs text-gray-400">
                <span>Showing <strong id="visibleCount" class="text-white">0</strong> of <strong class="text-white">{{ kpis.total_albums }}</strong> albums</span>
                <span id="filterDescription" class="italic text-gray-500">Hover over any album to preview 30s audio</span>
            </div>
        </div>

        <!-- Album Grid -->
        <div id="albumGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            <!-- Populated via JavaScript -->
        </div>

        <!-- Load More Container -->
        <div class="mt-8 text-center" id="loadMoreContainer">
            <button id="loadMoreBtn" onclick="loadMore()" class="bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 px-6 py-2.5 rounded-xl text-sm font-semibold transition">
                Load More Albums
            </button>
        </div>
    </div>

    <!-- Floating Audio Preview Banner -->
    <div id="previewToast" class="fixed bottom-5 right-5 z-50 bg-[#161a1f]/95 backdrop-blur-md border border-[#1DB954]/50 shadow-2xl rounded-2xl p-4 flex items-center gap-4 transition-all duration-300 transform translate-y-28 opacity-0 pointer-events-none max-w-sm">
        <div class="w-9 h-9 rounded-full bg-[#1DB954]/20 flex items-center justify-center flex-shrink-0 border border-[#1DB954]/40">
            <span class="text-sm animate-pulse">🎵</span>
        </div>
        <div class="flex-grow min-w-0">
            <p class="text-xs font-bold text-white truncate" id="toastTrack">Previewing Track</p>
            <p class="text-[11px] text-gray-400 truncate" id="toastArtist">Artist • Album</p>
        </div>
        <div class="flex items-center gap-1.5 flex-shrink-0">
            <a id="toastAppleLink" href="#" target="_blank" class="text-[10px] bg-[#FA233B]/20 text-[#FA233B] hover:bg-[#FA233B] hover:text-white px-2 py-1 rounded font-bold border border-[#FA233B]/30 transition" title="Open in Apple Music">
                🍎 Apple
            </a>
            <button onclick="stopPreview()" class="text-gray-400 hover:text-white p-1 text-sm font-bold">✕</button>
        </div>
    </div>

    <script>
        const ALL_ALBUMS = {{ albums | tojson }};
        let filteredAlbums = [...ALL_ALBUMS];
        let displayLimit = 48;
        const PAGE_STEP = 48;

        // Hover Audio Preview Controller
        let hoverTimer = null;
        let activeAudio = new Audio();
        let currentHoverKey = null;
        let isAudioEnabled = true;
        const previewUrlCache = new Map();

        activeAudio.volume = 0.75;
        activeAudio.addEventListener('ended', () => hidePreviewToast());

        function toggleHoverAudio() {
            isAudioEnabled = !isAudioEnabled;
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                btnText.innerText = 'Hover Audio: ON';
                btnIcon.innerText = '🔊';
            } else {
                stopPreview();
                btnText.innerText = 'Hover Audio: MUTED';
                btnIcon.innerText = '🔇';
            }
        }

        function onCardHover(artist, album, spotifyUrl, cardEl) {
            if (!isAudioEnabled) return;
            const key = `${artist.toLowerCase()}::${album.toLowerCase()}`;
            currentHoverKey = key;

            if (hoverTimer) clearTimeout(hoverTimer);

            // 350ms debounce
            hoverTimer = setTimeout(async () => {
                if (currentHoverKey !== key) return;

                let data = previewUrlCache.get(key);
                if (!data) {
                    try {
                        const res = await fetch(`/api/preview?artist=${encodeURIComponent(artist)}&album=${encodeURIComponent(album)}`);
                        data = await res.json();
                        previewUrlCache.set(key, data);
                    } catch (e) {
                        return;
                    }
                }

                if (currentHoverKey !== key) return;

                if (data && data.preview_url) {
                    activeAudio.src = data.preview_url;
                    activeAudio.play().then(() => {
                        showPreviewToast(artist, album, data.track_name || 'Preview Snippet', data.apple_music_url, spotifyUrl);
                        const pulse = cardEl.querySelector('.audio-pulse');
                        if (pulse) pulse.classList.remove('hidden');
                    }).catch(e => {});
                }
            }, 350);
        }

        function onCardLeave(cardEl) {
            if (hoverTimer) clearTimeout(hoverTimer);
            currentHoverKey = null;
            stopPreview();
            if (cardEl) {
                const pulse = cardEl.querySelector('.audio-pulse');
                if (pulse) pulse.classList.add('hidden');
            }
        }

        function stopPreview() {
            activeAudio.pause();
            activeAudio.currentTime = 0;
            hidePreviewToast();
            document.querySelectorAll('.audio-pulse').forEach(el => el.classList.add('hidden'));
        }

        function showPreviewToast(artist, album, track, appleUrl, spotifyUrl) {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            document.getElementById('toastTrack').innerText = track;
            document.getElementById('toastArtist').innerText = `${artist} • ${album}`;
            const amLink = document.getElementById('toastAppleLink');
            if (amLink && appleUrl) amLink.href = appleUrl;

            toast.classList.remove('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.add('translate-y-0', 'opacity-100');
        }

        function hidePreviewToast() {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            toast.classList.add('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.remove('translate-y-0', 'opacity-100');
        }

        function renderGrid() {
            const grid = document.getElementById("albumGrid");
            const visible = filteredAlbums.slice(0, displayLimit);
            document.getElementById("visibleCount").innerText = filteredAlbums.length;

            if (filteredAlbums.length === 0) {
                grid.innerHTML = `
                    <div class="col-span-full py-16 text-center text-gray-500">
                        <p class="text-base font-medium">No albums match your active filters.</p>
                        <button onclick="resetFilters()" class="mt-3 text-xs text-[#1DB954] underline hover:text-[#1ed760]">Reset filters</button>
                    </div>
                `;
                document.getElementById("loadMoreContainer").style.display = "none";
                return;
            }

            let html = "";
            for (let a of visible) {
                const img = a.album_image_url || "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80";
                const plays = a.album_plays > 0 ? `${a.album_plays} plays` : 'Unplayed';
                const playsBadge = a.album_plays > 0 
                    ? `<span class="badge-fav text-[10px] font-bold text-white px-2 py-0.5 rounded-full shadow-sm">🔥 ${plays}</span>`
                    : `<span class="bg-gray-800 text-gray-400 text-[10px] px-2 py-0.5 rounded-full">New</span>`;

                const genres = a.album_genres ? a.album_genres.split(", ").slice(0, 2).join(" • ") : "";
                const safeArtist = (a.album_artist_name || "").replace(/'/g, "\\'");
                const safeAlbum = (a.album_name || "").replace(/'/g, "\\'");
                const appleOpenUrl = `/open/apple?artist=${encodeURIComponent(a.album_artist_name)}&album=${encodeURIComponent(a.album_name)}`;

                html += `
                    <div class="card-bg group block rounded-xl p-3 border border-gray-800/80 hover:border-gray-700 transition duration-200 shadow-sm hover:shadow-lg flex flex-col justify-between relative cursor-pointer"
                         onmouseenter="onCardHover('${safeArtist}', '${safeAlbum}', '${a.album_url}', this)"
                         onmouseleave="onCardLeave(this)"
                         onclick="window.open('${a.album_url}', '_blank')">
                        <div>
                            <!-- Album Cover -->
                            <div class="relative w-full aspect-square rounded-lg overflow-hidden bg-gray-900 mb-2.5">
                                <img src="${img}" alt="${a.album_name}" loading="lazy"
                                     class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                                
                                <!-- Floating Play Badge overlay -->
                                <div class="absolute top-2 right-2">
                                    ${playsBadge}
                                </div>

                                <!-- Audio Playing Badge Indicator -->
                                <div class="audio-pulse hidden absolute bottom-2 left-2 bg-black/85 backdrop-blur-md px-2 py-1 rounded-full text-[10px] font-bold text-[#1DB954] border border-[#1DB954]/50 shadow-md flex items-center gap-1 z-20">
                                    <span>🎵</span> <span class="animate-pulse">Previewing</span>
                                </div>

                                <!-- Hover Play Button -->
                                <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                    <div class="w-11 h-11 rounded-full bg-[#1DB954] flex items-center justify-center shadow-lg transform group-hover:scale-110 transition duration-200">
                                        <svg class="w-5 h-5 text-black fill-current ml-0.5" viewBox="0 0 24 24">
                                            <path d="M8 5v14l11-7z"/>
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            <!-- Album Title & Artist -->
                            <h3 class="font-bold text-xs text-white truncate group-hover:text-[#1DB954] transition" title="${a.album_name}">
                                ${a.album_name}
                            </h3>
                            <p class="text-[11px] text-gray-400 truncate mt-0.5" title="${a.album_artist_name}">
                                ${a.album_artist_name}
                            </p>
                        </div>

                        <!-- Footer tags & Apple Music Link -->
                        <div class="mt-2.5 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[10px] text-gray-500">
                            <span>${a.release_year}</span>
                            <div class="flex items-center gap-1.5">
                                <a href="${appleOpenUrl}" target="_blank" rel="noopener noreferrer"
                                   onclick="event.stopPropagation()"
                                   class="text-[10px] font-semibold text-[#FA233B] bg-[#FA233B]/10 hover:bg-[#FA233B] hover:text-white border border-[#FA233B]/30 px-1.5 py-0.5 rounded transition flex items-center gap-1"
                                   title="Play on Apple Music">
                                    🍎 Apple
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }

            grid.innerHTML = html;

            const loadMoreBtn = document.getElementById("loadMoreContainer");
            loadMoreBtn.style.display = displayLimit < filteredAlbums.length ? "block" : "none";
        }

        function onFilterChange() {
            const query = document.getElementById("searchInput").value.toLowerCase().trim();
            const genre = document.getElementById("genreFilter").value.toLowerCase();
            const status = document.getElementById("statusFilter").value;
            const sort = document.getElementById("sortFilter").value;

            filteredAlbums = ALL_ALBUMS.filter(a => {
                if (query) {
                    const matchName = a.album_name && a.album_name.toLowerCase().includes(query);
                    const matchArtist = a.album_artist_name && a.album_artist_name.toLowerCase().includes(query);
                    if (!matchName && !matchArtist) return false;
                }

                if (genre) {
                    if (!a.album_genres || !a.album_genres.toLowerCase().includes(genre)) {
                        return false;
                    }
                }

                if (status === "favorites" && a.album_track_plays === 0) return false;
                if (status === "unplayed" && a.album_track_plays > 0) return false;

                return true;
            });

            filteredAlbums.sort((a, b) => {
                if (sort === "most_played") {
                    return (b.album_plays || 0) - (a.album_plays || 0);
                } else if (sort === "recently_added") {
                    return (b.added_at || "").localeCompare(a.added_at || "");
                } else if (sort === "release_new") {
                    return (b.album_release_date || "").localeCompare(a.album_release_date || "");
                } else if (sort === "release_old") {
                    return (a.album_release_date || "").localeCompare(b.album_release_date || "");
                } else if (sort === "alpha") {
                    return (a.album_name || "").localeCompare(b.album_name || "");
                }
                return 0;
            });

            displayLimit = PAGE_STEP;
            updateKpis(filteredAlbums);
            renderGrid();
        }

        function updateKpis(albums) {
            const count = albums.length;
            document.getElementById("kpiTotalAlbums").innerText = count.toLocaleString();

            if (count === 0) {
                document.getElementById("kpiPctExplored").innerText = "0%";
                document.getElementById("kpiPlayedSubtext").innerText = "0 played / 0 unplayed";
                document.getElementById("kpiTotalPlays").innerText = "0";
                document.getElementById("kpiTopAlbum").innerText = "None";
                document.getElementById("kpiTopAlbum").title = "None";
                document.getElementById("kpiTopAlbumPlays").innerText = "0 album plays";
                return;
            }

            const played = albums.filter(a => (a.album_track_plays || 0) > 0).length;
            const unplayed = count - played;
            const pct = ((played / count) * 100).toFixed(1);
            document.getElementById("kpiPctExplored").innerText = `${pct}%`;
            document.getElementById("kpiPlayedSubtext").innerText = `${played} played / ${unplayed} unplayed`;

            const totalPlays = albums.reduce((sum, a) => sum + (a.album_track_plays || 0), 0);
            document.getElementById("kpiTotalPlays").innerText = totalPlays.toLocaleString();

            let top = albums[0];
            for (let a of albums) {
                if ((a.album_plays || 0) > (top.album_plays || 0)) {
                    top = a;
                }
            }

            if (top && (top.album_plays || 0) > 0) {
                document.getElementById("kpiTopAlbum").innerText = top.album_name;
                document.getElementById("kpiTopAlbum").title = top.album_name;
                document.getElementById("kpiTopAlbumPlays").innerText = `${top.album_plays} album plays`;
            } else {
                document.getElementById("kpiTopAlbum").innerText = top ? top.album_name : "None";
                document.getElementById("kpiTopAlbum").title = top ? top.album_name : "None";
                document.getElementById("kpiTopAlbumPlays").innerText = "0 album plays";
            }
        }

        function loadMore() {
            displayLimit += PAGE_STEP;
            renderGrid();
        }

        function resetFilters() {
            document.getElementById("searchInput").value = "";
            document.getElementById("genreFilter").value = "";
            document.getElementById("statusFilter").value = "all";
            document.getElementById("sortFilter").value = "most_played";
            onFilterChange();
        }

        document.addEventListener("DOMContentLoaded", () => {
            onFilterChange();
        });
    </script>
</body>
</html>
"""


# ==============================================================================
# TAB 2: CRATE DIGGER (With Apple Music & Audio Previews)
# ==============================================================================
RECOMMEND_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crate Digger - Spotify Dash</title>
    <!-- SpinSleeve Full-Bleed Turntable Tab Icon -->
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' fill='none'%3E%3Ccircle cx='48' cy='52' r='46' fill='%230C0F12' stroke='%231DB954' stroke-width='3'/%3E%3Ccircle cx='48' cy='52' r='40' fill='%231DB954'/%3E%3Cpath d='M30 40c9-2.5 19-1.5 27 3' stroke='%230C0F12' stroke-width='5' stroke-linecap='round'/%3E%3Cpath d='M33 49c8-1.8 16-1 22 2.5' stroke='%230C0F12' stroke-width='4.2' stroke-linecap='round'/%3E%3Cpath d='M36 58c6-1.2 12-0.5 17 2' stroke='%230C0F12' stroke-width='3.5' stroke-linecap='round'/%3E%3Ccircle cx='48' cy='52' r='5' fill='%230C0F12'/%3E%3Ccircle cx='86' cy='14' r='9' fill='%23181D22' stroke='%239CA3AF' stroke-width='3'/%3E%3Ccircle cx='86' cy='14' r='4' fill='%231DB954'/%3E%3Cpath d='M83 19 L66 62 L52 68' stroke='%23FFFFFF' stroke-width='4.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3Crect x='43' y='63' width='11' height='8' rx='2' fill='%230C0F12' stroke='%231DB954' stroke-width='1.5' transform='rotate(-22 48 67)'/%3E%3C/svg%3E">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
        .card-bg { background-color: #181d22; }
        .card-bg:hover { background-color: #21272e; }
        .spotlight-card { background: linear-gradient(145deg, #181d22 0%, #12161a 100%); }
        .spotlight-card:hover { border-color: #1DB954; }
        .pill-active { background-color: #1DB954; color: #000; font-weight: 700; }
        .pill-inactive { background-color: #1b2127; color: #9ca3af; border: 1px solid #28323c; }
        .pill-inactive:hover { background-color: #28323c; color: #fff; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">

    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-4 border-b border-gray-800 gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 flex-shrink-0">
                        {{ brand_icon | safe }}
                    </div>
                    <h1 class="text-3xl font-extrabold tracking-tight text-white">Crate Digger</h1>
                </div>
                <p class="text-xs text-gray-400 mt-1">Smart recommendation engine powered by listening history</p>
            </div>

            <!-- Quick Action Links -->
            <div class="flex flex-wrap items-center gap-2.5">
                <button id="audioToggleBtn" onclick="toggleHoverAudio()"
                        class="text-xs font-semibold px-3 py-2 rounded-lg border border-gray-700 bg-gray-800/80 text-gray-300 hover:text-white flex items-center gap-1.5 transition">
                    <span id="audioIcon">🔊</span> <span id="audioText">Hover Audio: ON</span>
                </button>
                <button onclick="spinAgain()" class="text-xs font-bold text-black bg-[#1DB954] hover:bg-[#1ed760] px-4 py-2 rounded-lg transition shadow-md flex items-center gap-1.5">
                    <span>🎲</span> Spin Again
                </button>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="flex items-center gap-2 mb-6 border-b border-gray-800 pb-3">
            <a href="/" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📚</span> Library Explorer
            </a>
            <a href="/recommend" class="px-4 py-2 rounded-lg text-xs font-bold transition bg-[#1DB954]/15 text-[#1DB954] border border-[#1DB954]/30 flex items-center gap-2">
                <span>📻</span> Crate Digger
            </a>
        </nav>

        <!-- Control Deck: Filter & Preference Configurator -->
        <div class="card-bg p-5 rounded-2xl border border-gray-800 mb-8 shadow-lg">
            <div class="space-y-4">
                <!-- 1. Listening Mode -->
                <div>
                    <label class="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">1. Listening Mode</label>
                    <div class="flex flex-wrap gap-2.5">
                        <button onclick="setMode('discover')" id="modeBtn-discover" class="pill-active px-4 py-2 rounded-xl text-xs transition flex items-center gap-2">
                            <span>🔍</span> Discover (Never Played: {{ kpis.unplayed_albums }} albums)
                        </button>
                        <button onclick="setMode('favorites')" id="modeBtn-favorites" class="pill-inactive px-4 py-2 rounded-xl text-xs transition flex items-center gap-2">
                            <span>⭐</span> Favorites (Heavy Rotation: {{ kpis.played_albums }} albums)
                        </button>
                    </div>
                </div>

                <!-- 2. Mood & Vibe -->
                <div>
                    <label class="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">2. Mood & Vibe</label>
                    <div class="flex flex-wrap gap-2">
                        <button onclick="setVibe('all')" id="vibeBtn-all" class="pill-active px-3.5 py-1.5 rounded-lg text-xs transition">🌌 Any Vibe</button>
                        <button onclick="setVibe('chill')" id="vibeBtn-chill" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">🌙 Late Night / Chill</button>
                        <button onclick="setVibe('energetic')" id="vibeBtn-energetic" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">⚡ Energetic / Focus</button>
                        <button onclick="setVibe('mellow')" id="vibeBtn-mellow" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">☕ Mellow / Acoustic</button>
                        <button onclick="setVibe('vintage')" id="vibeBtn-vintage" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">📻 Vintage Classics</button>
                    </div>
                </div>

                <!-- 3. Era & Genre Refinement -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-gray-800/80">
                    <div>
                        <label class="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">3. Era Preference</label>
                        <div class="flex flex-wrap gap-2">
                            <button onclick="setEra('all')" id="eraBtn-all" class="pill-active px-3 py-1.5 rounded-lg text-xs transition">Any Era</button>
                            <button onclick="setEra('recent')" id="eraBtn-recent" class="pill-inactive px-3 py-1.5 rounded-lg text-xs transition">✨ Recent (2018+)</button>
                            <button onclick="setEra('modern')" id="eraBtn-modern" class="pill-inactive px-3 py-1.5 rounded-lg text-xs transition">💿 2000s & 2010s</button>
                            <button onclick="setEra('classic')" id="eraBtn-classic" class="pill-inactive px-3 py-1.5 rounded-lg text-xs transition">📼 Vintage (< 2000)</button>
                        </div>
                    </div>
                    <div>
                        <label class="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">4. Specific Sub-Genre (Optional)</label>
                        <select id="genreSelect" onchange="onGenreSelect(this.value)" class="w-full bg-[#11151a] border border-gray-700/80 rounded-lg p-2 text-xs text-gray-200 focus:outline-none focus:border-[#1DB954]">
                            <option value="">Any Genre</option>
                            {% for g in top_genres %}
                            <option value="{{ g }}">{{ g|title }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <!-- Section: Top 3 Spotlight Picks -->
        <div class="mb-10">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-[#1DB954] animate-pulse"></span>
                    <h2 class="text-xl font-black text-white tracking-tight">Top 3 Spotlight Picks For You</h2>
                </div>
                <div class="text-xs text-gray-400">
                    <span id="poolCountText">Calculating candidates...</span>
                </div>
            </div>

            <!-- Spotlight 3 Cards Container -->
            <div id="spotlightContainer" class="grid grid-cols-1 md:grid-cols-3 gap-5">
                <!-- Populated via JavaScript -->
            </div>
        </div>

        <!-- Section: Ranked Candidate Pool Below -->
        <div>
            <div class="flex items-center justify-between mb-4 pb-2 border-b border-gray-800">
                <h3 class="text-sm font-bold uppercase tracking-wider text-gray-300">All Matching Candidates</h3>
                <span class="text-xs text-gray-500" id="candidateSubtext"></span>
            </div>
            <div id="candidateGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                <!-- Populated via JavaScript -->
            </div>
        </div>
    </div>

    <!-- Floating Audio Preview Banner -->
    <div id="previewToast" class="fixed bottom-5 right-5 z-50 bg-[#161a1f]/95 backdrop-blur-md border border-[#1DB954]/50 shadow-2xl rounded-2xl p-4 flex items-center gap-4 transition-all duration-300 transform translate-y-28 opacity-0 pointer-events-none max-w-sm">
        <div class="w-9 h-9 rounded-full bg-[#1DB954]/20 flex items-center justify-center flex-shrink-0 border border-[#1DB954]/40">
            <span class="text-sm animate-pulse">🎵</span>
        </div>
        <div class="flex-grow min-w-0">
            <p class="text-xs font-bold text-white truncate" id="toastTrack">Previewing Track</p>
            <p class="text-[11px] text-gray-400 truncate" id="toastArtist">Artist • Album</p>
        </div>
        <div class="flex items-center gap-1.5 flex-shrink-0">
            <a id="toastAppleLink" href="#" target="_blank" class="text-[10px] bg-[#FA233B]/20 text-[#FA233B] hover:bg-[#FA233B] hover:text-white px-2 py-1 rounded font-bold border border-[#FA233B]/30 transition" title="Open in Apple Music">
                🍎 Apple
            </a>
            <button onclick="stopPreview()" class="text-gray-400 hover:text-white p-1 text-sm font-bold">✕</button>
        </div>
    </div>

    <!-- Recommendation Engine Logic -->
    <script>
        const ALL_ALBUMS = {{ albums | tojson }};
        let selectedMode = 'discover';
        let selectedVibe = 'all';
        let selectedEra = 'all';
        let selectedGenre = '';
        let currentSeed = Math.random();

        // Hover Audio Preview Controller
        let hoverTimer = null;
        let activeAudio = new Audio();
        let currentHoverKey = null;
        let isAudioEnabled = true;
        const previewUrlCache = new Map();

        activeAudio.volume = 0.75;
        activeAudio.addEventListener('ended', () => hidePreviewToast());

        function toggleHoverAudio() {
            isAudioEnabled = !isAudioEnabled;
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                btnText.innerText = 'Hover Audio: ON';
                btnIcon.innerText = '🔊';
            } else {
                stopPreview();
                btnText.innerText = 'Hover Audio: MUTED';
                btnIcon.innerText = '🔇';
            }
        }

        function onCardHover(artist, album, spotifyUrl, cardEl) {
            if (!isAudioEnabled) return;
            const key = `${artist.toLowerCase()}::${album.toLowerCase()}`;
            currentHoverKey = key;

            if (hoverTimer) clearTimeout(hoverTimer);

            hoverTimer = setTimeout(async () => {
                if (currentHoverKey !== key) return;

                let data = previewUrlCache.get(key);
                if (!data) {
                    try {
                        const res = await fetch(`/api/preview?artist=${encodeURIComponent(artist)}&album=${encodeURIComponent(album)}`);
                        data = await res.json();
                        previewUrlCache.set(key, data);
                    } catch (e) {
                        return;
                    }
                }

                if (currentHoverKey !== key) return;

                if (data && data.preview_url) {
                    activeAudio.src = data.preview_url;
                    activeAudio.play().then(() => {
                        showPreviewToast(artist, album, data.track_name || 'Preview Snippet', data.apple_music_url, spotifyUrl);
                        const pulse = cardEl.querySelector('.audio-pulse');
                        if (pulse) pulse.classList.remove('hidden');
                    }).catch(e => {});
                }
            }, 350);
        }

        function onCardLeave(cardEl) {
            if (hoverTimer) clearTimeout(hoverTimer);
            currentHoverKey = null;
            stopPreview();
            if (cardEl) {
                const pulse = cardEl.querySelector('.audio-pulse');
                if (pulse) pulse.classList.add('hidden');
            }
        }

        function stopPreview() {
            activeAudio.pause();
            activeAudio.currentTime = 0;
            hidePreviewToast();
            document.querySelectorAll('.audio-pulse').forEach(el => el.classList.add('hidden'));
        }

        function showPreviewToast(artist, album, track, appleUrl, spotifyUrl) {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            document.getElementById('toastTrack').innerText = track;
            document.getElementById('toastArtist').innerText = `${artist} • ${album}`;
            const amLink = document.getElementById('toastAppleLink');
            if (amLink && appleUrl) amLink.href = appleUrl;

            toast.classList.remove('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.add('translate-y-0', 'opacity-100');
        }

        function hidePreviewToast() {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            toast.classList.add('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.remove('translate-y-0', 'opacity-100');
        }

        const VIBES = {
            all: { name: "Any Vibe", keywords: [] },
            chill: {
                name: "Late Night / Chill",
                keywords: ["ambient", "dream pop", "downtempo", "jazz", "soul", "trip hop", "lo-fi", "slowcore", "chill", "folk", "r&b", "bossa", "art pop"]
            },
            energetic: {
                name: "Energetic / Focus",
                keywords: ["electronic", "post-punk", "afrobeat", "dance", "synthpop", "funk", "rock", "punk", "techno", "house", "krautrock", "disco", "garage"]
            },
            mellow: {
                name: "Mellow / Acoustic",
                keywords: ["acoustic", "singer-songwriter", "chamber pop", "folk", "indie folk", "country", "americana", "classical", "piano"]
            },
            vintage: {
                name: "Crate Digger / Vintage",
                keywords: ["classic soul", "hard bop", "psych rock", "afro-cuban", "reggae", "motown", "funk", "blues", "vintage", "70s", "60s"]
            }
        };

        const ERAS = {
            all: { min: 1900, max: 2099 },
            recent: { min: 2018, max: 2099 },
            modern: { min: 2000, max: 2017 },
            classic: { min: 1900, max: 1999 }
        };

        function setMode(mode) {
            selectedMode = mode;
            document.getElementById('modeBtn-discover').className = mode === 'discover' ? 'pill-active px-4 py-2 rounded-xl text-xs transition flex items-center gap-2' : 'pill-inactive px-4 py-2 rounded-xl text-xs transition flex items-center gap-2';
            document.getElementById('modeBtn-favorites').className = mode === 'favorites' ? 'pill-active px-4 py-2 rounded-xl text-xs transition flex items-center gap-2' : 'pill-inactive px-4 py-2 rounded-xl text-xs transition flex items-center gap-2';
            spinAgain();
        }

        function setVibe(vibe) {
            selectedVibe = vibe;
            ['all', 'chill', 'energetic', 'mellow', 'vintage'].forEach(v => {
                const btn = document.getElementById(`vibeBtn-${v}`);
                if (btn) btn.className = v === vibe ? 'pill-active px-3.5 py-1.5 rounded-lg text-xs transition' : 'pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition';
            });
            spinAgain();
        }

        function setEra(era) {
            selectedEra = era;
            ['all', 'recent', 'modern', 'classic'].forEach(e => {
                const btn = document.getElementById(`eraBtn-${e}`);
                if (btn) btn.className = e === era ? 'pill-active px-3 py-1.5 rounded-lg text-xs transition' : 'pill-inactive px-3 py-1.5 rounded-lg text-xs transition';
            });
            spinAgain();
        }

        function onGenreSelect(genre) {
            selectedGenre = genre.toLowerCase();
            spinAgain();
        }

        function spinAgain() {
            currentSeed = Math.random();
            renderRecommendations();
        }

        function computeRankedCandidates(seed) {
            const era = ERAS[selectedEra];

            let pool = ALL_ALBUMS.filter(a => {
                if (selectedMode === 'discover' && (a.album_track_plays || 0) > 0) return false;
                if (selectedMode === 'favorites' && (a.album_track_plays || 0) === 0) return false;

                if (selectedGenre && (!a.album_genres || !a.album_genres.toLowerCase().includes(selectedGenre))) {
                    return false;
                }

                const yr = parseInt(a.release_year) || 0;
                if (yr > 0 && (yr < era.min || yr > era.max)) return false;

                return true;
            });

            const scored = pool.map((a, idx) => {
                let score = 1.0;
                const genres = (a.album_genres || "").toLowerCase();

                if (selectedVibe !== 'all') {
                    const kws = VIBES[selectedVibe].keywords;
                    let matches = 0;
                    for (let kw of kws) {
                        if (genres.includes(kw)) matches++;
                    }
                    score *= (matches > 0 ? (1.5 + matches * 0.4) : 0.3);
                }

                if (selectedMode === 'favorites') {
                    score *= (1 + Math.log10(1 + (a.album_plays || 1)));
                } else {
                    if (a.album_image_url) score *= 1.15;
                }

                const hash = ((idx * 1337 + seed * 99991) % 100) / 100;
                score *= (0.8 + hash * 0.4);

                return { ...a, recScore: score };
            });

            scored.sort((a, b) => b.recScore - a.recScore);
            return scored;
        }

        function renderRecommendations() {
            const candidates = computeRankedCandidates(currentSeed);
            document.getElementById('poolCountText').innerText = `Matched ${candidates.length.toLocaleString()} albums in your library`;
            document.getElementById('candidateSubtext').innerText = `Showing top matching recommendations`;

            const spotlight = document.getElementById('spotlightContainer');
            const grid = document.getElementById('candidateGrid');

            if (candidates.length === 0) {
                spotlight.innerHTML = `
                    <div class="col-span-full card-bg p-8 rounded-2xl text-center text-gray-500 border border-gray-800">
                        <p class="text-base font-semibold text-gray-300">No albums matched this exact combination.</p>
                        <p class="text-xs text-gray-500 mt-1">Try switching to "Any Vibe" or "Any Era" to widen your candidate pool.</p>
                    </div>
                `;
                grid.innerHTML = "";
                return;
            }

            // Top 3 Spotlight
            const top3 = candidates.slice(0, 3);
            let spotlightHtml = "";
            top3.forEach((a, i) => {
                const img = a.album_image_url || "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=500&q=80";
                const badgeLabel = selectedMode === 'discover' 
                    ? (i === 0 ? "✨ #1 Top Discovery" : `🎯 Recommendation #${i+1}`)
                    : (i === 0 ? "🔥 #1 Heavy Rotation" : `⭐ Favorite Pick #${i+1}`);

                const genres = a.album_genres ? a.album_genres.split(", ").slice(0, 3).join(" • ") : "Curated Release";
                const playsText = a.album_plays > 0 ? `${a.album_plays} plays logged` : "Never played";
                const safeArtist = (a.album_artist_name || "").replace(/'/g, "\\'");
                const safeAlbum = (a.album_name || "").replace(/'/g, "\\'");
                const appleOpenUrl = `/open/apple?artist=${encodeURIComponent(a.album_artist_name)}&album=${encodeURIComponent(a.album_name)}`;

                spotlightHtml += `
                    <div class="spotlight-card border border-gray-800/80 rounded-2xl p-4 flex flex-col justify-between shadow-xl transition duration-300 relative"
                         onmouseenter="onCardHover('${safeArtist}', '${safeAlbum}', '${a.album_url}', this)"
                         onmouseleave="onCardLeave(this)">
                        <div>
                            <div class="flex items-center justify-between mb-3 text-[11px]">
                                <span class="bg-[#1DB954]/20 text-[#1DB954] font-bold px-2.5 py-1 rounded-full border border-[#1DB954]/30">${badgeLabel}</span>
                                <span class="text-gray-400 font-medium">${a.release_year}</span>
                            </div>

                            <div class="relative w-full aspect-square rounded-xl overflow-hidden bg-gray-900 mb-3.5 shadow-md">
                                <img src="${img}" alt="${a.album_name}" class="w-full h-full object-cover">
                                
                                <div class="audio-pulse hidden absolute bottom-2 left-2 bg-black/85 backdrop-blur-md px-2.5 py-1 rounded-full text-[10px] font-bold text-[#1DB954] border border-[#1DB954]/50 shadow-md flex items-center gap-1 z-20">
                                    <span>🎵</span> <span class="animate-pulse">Previewing 30s Snippet</span>
                                </div>
                            </div>

                            <h3 class="font-extrabold text-base text-white truncate" title="${a.album_name}">${a.album_name}</h3>
                            <p class="text-xs font-semibold text-gray-300 truncate mt-0.5">${a.album_artist_name}</p>
                            <p class="text-[11px] text-gray-500 truncate mt-1">${genres}</p>
                        </div>

                        <div class="mt-4 pt-3 border-t border-gray-800/60 flex items-center justify-between gap-2">
                            <span class="text-[11px] text-gray-400 font-medium">${playsText}</span>
                            <div class="flex items-center gap-1.5">
                                <a href="${appleOpenUrl}" target="_blank" rel="noopener noreferrer"
                                   class="bg-[#FA233B]/15 hover:bg-[#FA233B] hover:text-white text-[#FA233B] border border-[#FA233B]/30 text-xs font-bold px-2.5 py-1.5 rounded-xl transition flex items-center gap-1 shadow">
                                    🍎 Apple Music
                                </a>
                                <a href="${a.album_url}" target="_blank" rel="noopener noreferrer"
                                   class="bg-[#1DB954] hover:bg-[#1ed760] text-black text-xs font-bold px-3 py-1.5 rounded-xl transition flex items-center gap-1 shadow">
                                    ▶ Spotify
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            });
            spotlight.innerHTML = spotlightHtml;

            // Rest of Candidates
            const remaining = candidates.slice(3, 27);
            let gridHtml = "";
            for (let a of remaining) {
                const img = a.album_image_url || "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80";
                const plays = a.album_plays > 0 ? `🔥 ${a.album_plays} plays` : '✨ Unplayed';
                const safeArtist = (a.album_artist_name || "").replace(/'/g, "\\'");
                const safeAlbum = (a.album_name || "").replace(/'/g, "\\'");
                const appleCandidateOpenUrl = `/open/apple?artist=${encodeURIComponent(a.album_artist_name)}&album=${encodeURIComponent(a.album_name)}`;

                gridHtml += `
                    <div class="card-bg group block rounded-xl p-3 border border-gray-800/80 hover:border-gray-700 transition duration-200 shadow-sm flex flex-col justify-between relative cursor-pointer"
                         onmouseenter="onCardHover('${safeArtist}', '${safeAlbum}', '${a.album_url}', this)"
                         onmouseleave="onCardLeave(this)"
                         onclick="window.open('${a.album_url}', '_blank')">
                        <div>
                            <div class="relative w-full aspect-square rounded-lg overflow-hidden bg-gray-900 mb-2.5">
                                <img src="${img}" alt="${a.album_name}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                                <div class="absolute top-1.5 right-1.5 bg-black/60 backdrop-blur-sm text-[10px] text-gray-200 px-2 py-0.5 rounded-full font-bold">
                                    ${plays}
                                </div>
                                <div class="audio-pulse hidden absolute bottom-1.5 left-1.5 bg-black/85 backdrop-blur-md px-1.5 py-0.5 rounded-full text-[9px] font-bold text-[#1DB954] border border-[#1DB954]/50 shadow-md flex items-center gap-1 z-20">
                                    <span>🎵</span> <span class="animate-pulse">Preview</span>
                                </div>
                            </div>
                            <h4 class="font-bold text-xs text-white truncate group-hover:text-[#1DB954] transition" title="${a.album_name}">${a.album_name}</h4>
                            <p class="text-[11px] text-gray-400 truncate mt-0.5">${a.album_artist_name}</p>
                        </div>
                        <div class="mt-2 pt-1.5 border-t border-gray-800/60 text-[10px] text-gray-500 flex justify-between items-center">
                            <span>${a.release_year}</span>
                            <a href="${appleCandidateOpenUrl}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"
                               class="text-[9px] font-semibold text-[#FA233B] bg-[#FA233B]/10 hover:bg-[#FA233B] hover:text-white border border-[#FA233B]/30 px-1.5 py-0.5 rounded transition">
                                🍎 Apple
                            </a>
                        </div>
                    </div>
                `;
            }
            grid.innerHTML = gridHtml;
        }

        document.addEventListener("DOMContentLoaded", () => {
            renderRecommendations();
        });
    </script>
</body>
</html>
"""


# ==============================================================================
# ROUTE HANDLERS
# ==============================================================================

@app.route("/api/preview")
def api_preview():
    """
    On-demand iTunes audio preview & Apple Music direct URL lookup.
    Cached in-memory to provide instantaneous repeated responses.
    """
    artist = request.args.get("artist", "").strip()
    album = request.args.get("album", "").strip()
    if not artist and not album:
        return jsonify({"status": "error", "message": "Missing artist or album"})

    key = f"{artist.lower()}::{album.lower()}"
    if key in _preview_cache:
        return jsonify(_preview_cache[key])

    term = f"{artist} {album}"
    try:
        res = requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "entity": "song", "limit": 1},
            timeout=3.5
        )
        data = res.json()
        if data.get("resultCount", 0) > 0:
            result = data["results"][0]
            am_url = result.get("collectionViewUrl") or result.get("trackViewUrl")
            payload = {
                "status": "success",
                "preview_url": result.get("previewUrl"),
                "apple_music_url": am_url,
                "track_name": result.get("trackName", "Preview Snippet")
            }
        else:
            payload = {
                "status": "not_found",
                "preview_url": None,
                "apple_music_url": f"https://music.apple.com/us/search?term={urllib.parse.quote(term)}",
                "track_name": None
            }
    except Exception as e:
        payload = {
            "status": "error",
            "message": str(e),
            "preview_url": None,
            "apple_music_url": f"https://music.apple.com/us/search?term={urllib.parse.quote(term)}",
            "track_name": None
        }

    _preview_cache[key] = payload
    return jsonify(payload)


@app.route("/open/apple")
def open_apple():
    """
    Resolves the exact Apple Music album ID and redirects directly
    to the album view in the Apple Music app on iOS / macOS.
    """
    artist = request.args.get("artist", "").strip()
    album = request.args.get("album", "").strip()
    if not artist and not album:
        return redirect("https://music.apple.com")

    key = f"{artist.lower()}::{album.lower()}"
    # Check if already resolved in preview cache
    if key in _preview_cache and _preview_cache[key].get("apple_music_url"):
        return redirect(_preview_cache[key]["apple_music_url"])

    term = f"{artist} {album}"
    try:
        res = requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "entity": "album", "limit": 1},
            timeout=3.5
        )
        data = res.json()
        if data.get("resultCount", 0) > 0:
            am_url = data["results"][0].get("collectionViewUrl")
            if am_url:
                if key not in _preview_cache:
                    _preview_cache[key] = {}
                _preview_cache[key]["apple_music_url"] = am_url
                return redirect(am_url)
    except Exception:
        pass

    fallback_url = f"https://music.apple.com/us/search?term={urllib.parse.quote(term)}"
    return redirect(fallback_url)


@app.route("/icons")
def icon_showcase():
    return render_template_string(
        ICONS_PREVIEW_HTML,
        svg_a=ICON_A_SVG,
        svg_b=ICON_B_SVG,
        svg_c=ICON_C_SVG
    )


@app.route("/favicon.svg")
@app.route("/favicon.ico")
def favicon():
    return Response(ICON_A_SVG, mimetype="image/svg+xml")


@app.route("/")
def index():
    data = fetch_album_data()
    return render_template_string(
        EXPLORER_HTML_TEMPLATE,
        albums=data["albums"],
        top_genres=data["top_genres"],
        kpis=data["kpis"],
        brand_icon=ICON_A_SVG
    )


@app.route("/recommend")
def recommend():
    data = fetch_album_data()
    return render_template_string(
        RECOMMEND_HTML_TEMPLATE,
        albums=data["albums"],
        top_genres=data["top_genres"],
        kpis=data["kpis"],
        brand_icon=ICON_A_SVG
    )


@app.route("/api/albums")
def api_albums():
    data = fetch_album_data()
    return jsonify({
        "status": "success",
        "total": len(data["albums"]),
        "kpis": data["kpis"]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
