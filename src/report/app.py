import os
import re
import json
import time
import urllib.parse
from collections import Counter
from datetime import datetime
import requests
import pandas as pd
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


def fetch_album_data(force_refresh=False):
    global _cached_data, _cache_time
    now = time.time()
    if not force_refresh and _cached_data is not None and (now - _cache_time) < CACHE_TTL:
        return _cached_data

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
    SELECT
      coalesce(f.album_name, 'Unknown Album') as album_name,
      coalesce(f.album_artist_name, 'Unknown Artist') as album_artist_name,
      f.added_at,
      f.album_release_date,
      f.album_type,
      f.album_label,
      coalesce(f.album_tracks_total, 0) as album_tracks_total,
      f.album_image_url,
      coalesce(f.album_genres, '') as album_genres,
      coalesce(f.album_track_plays, 0) as album_track_plays,
      coalesce(f.album_plays, 0.0) as album_plays,
      coalesce(f.album_url, 'https://open.spotify.com') as album_url,
      REGEXP_EXTRACT(f.album_url, r"album/([a-zA-Z0-9]+)") as album_id,
      e.pitchfork_score,
      e.metacritic_score,
      e.allmusic_score,
      e.discogs_rating,
      e.discogs_votes,
      e.album_description,
      e.personnel,
      e.wikipedia_url,
      e.discogs_url,
      e.styles as enriched_styles
    FROM
      `{PROJECT_ID}.{DATASET_NAME}.all_albums_features` f
    LEFT JOIN
      `{PROJECT_ID}.{DATASET_NAME}.album_enriched_metadata` e
      ON REGEXP_EXTRACT(f.album_url, r"album/([a-zA-Z0-9]+)") = e.album_id
    ORDER BY
      f.album_plays DESC, f.added_at DESC
    """
    df = client.query(query).to_dataframe()

    # Preprocess dates and years
    df["release_year"] = df["album_release_date"].apply(
        lambda x: str(x)[:4] if x and str(x)[:4].isdigit() else "Unknown"
    )

    albums = []
    for _, r in df.iterrows():
        p_str = str(r["personnel"]) if pd.notna(r["personnel"]) else ""
        p_list = [p.strip() for p in p_str.split("•") if p.strip()] if p_str else []
        has_gatefold = bool(
            (pd.notna(r["album_description"]) and str(r["album_description"]).strip()) or
            (pd.notna(r["personnel"]) and str(r["personnel"]).strip())
        )
        albums.append({
            "album_name": r["album_name"],
            "album_artist_name": r["album_artist_name"],
            "added_at": str(r["added_at"]) if pd.notna(r["added_at"]) else "",
            "album_release_date": str(r["album_release_date"]) if pd.notna(r["album_release_date"]) else "",
            "album_type": r["album_type"],
            "album_label": r["album_label"],
            "album_tracks_total": int(r["album_tracks_total"]),
            "album_image_url": r["album_image_url"] or "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=600&auto=format&fit=crop&q=80",
            "album_genres": r["album_genres"] or "",
            "album_track_plays": int(r["album_track_plays"]),
            "album_plays": float(r["album_plays"]),
            "album_url": r["album_url"],
            "album_id": r["album_id"] or "",
            "release_year": r["release_year"],
            "has_gatefold": has_gatefold,
            "pitchfork_score": r["pitchfork_score"] if pd.notna(r["pitchfork_score"]) else "",
            "metacritic_score": r["metacritic_score"] if pd.notna(r["metacritic_score"]) else "",
            "allmusic_score": r["allmusic_score"] if pd.notna(r["allmusic_score"]) else "",
            "discogs_rating": str(r["discogs_rating"]) if pd.notna(r["discogs_rating"]) else "",
            "discogs_votes": int(r["discogs_votes"]) if pd.notna(r["discogs_votes"]) else 0,
            "album_description": r["album_description"] if pd.notna(r["album_description"]) else "",
            "personnel": p_list,
            "wikipedia_url": r["wikipedia_url"] if pd.notna(r["wikipedia_url"]) else "",
            "discogs_url": r["discogs_url"] if pd.notna(r["discogs_url"]) else "",
            "styles": r["enriched_styles"] if pd.notna(r["enriched_styles"]) else r["album_genres"] or ""
        })

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

        let isModalOpen = false;

        function onCardLeave(cardEl) {
            if (hoverTimer) clearTimeout(hoverTimer);
            if (isModalOpen) return;
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

                const safeArtist = (a.album_artist_name || "").replace(/'/g, "\\'");
                const safeAlbum = (a.album_name || "").replace(/'/g, "\\'");
                const appleOpenUrl = `/open/apple?artist=${encodeURIComponent(a.album_artist_name)}&album=${encodeURIComponent(a.album_name)}`;

                const gatefoldBtn = a.has_gatefold ? `
                    <button onclick="event.stopPropagation(); openGatefoldModal('${a.album_id}')" 
                            title="Open 12&quot; Gatefold Liner Notes"
                            class="absolute top-2 left-2 w-7 h-7 rounded-full bg-black/60 hover:bg-amber-500 hover:text-black text-amber-300 border border-amber-500/30 backdrop-blur-md flex items-center justify-center transition shadow-lg opacity-90 hover:scale-110 z-20">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                    </button>
                ` : '';

                html += `
                    <div class="card-bg group block rounded-2xl p-3 border border-gray-800/80 hover:border-amber-500/30 transition duration-200 shadow-sm hover:shadow-xl flex flex-col justify-between relative cursor-pointer"
                         onmouseenter="onCardHover('${safeArtist}', '${safeAlbum}', '${a.album_url}', this)"
                         onmouseleave="onCardLeave(this)"
                         onclick="${a.has_gatefold ? `openGatefoldModal('${a.album_id}')` : `window.open('${a.album_url}', '_blank')`}">
                        <div>
                            <!-- Album Cover -->
                            <div class="relative w-full aspect-square rounded-xl overflow-hidden bg-gray-900 mb-2.5">
                                <img src="${img}" alt="${a.album_name}" loading="lazy"
                                     class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                                
                                <!-- Top-Left: Gatefold Booklet Icon -->
                                ${gatefoldBtn}

                                <!-- Top-Right: Number of Plays Badge -->
                                <div class="absolute top-2 right-2 z-10">
                                    ${playsBadge}
                                </div>

                                <!-- Audio Playing Badge Indicator -->
                                <div class="audio-pulse hidden absolute bottom-2 left-2 bg-black/85 backdrop-blur-md px-2 py-1 rounded-full text-[10px] font-bold text-[#1DB954] border border-[#1DB954]/50 shadow-md flex items-center gap-1 z-20">
                                    <span>🎵</span> <span class="animate-pulse">Previewing</span>
                                </div>
                            </div>

                            <!-- Album Title & Artist -->
                            <h3 class="font-bold text-xs text-white truncate group-hover:text-amber-300 transition" title="${a.album_name}">
                                ${a.album_name}
                            </h3>
                            <p class="text-[11px] text-gray-400 truncate mt-0.5" title="${a.album_artist_name}">
                                ${a.album_artist_name}
                            </p>
                            <p class="text-[10px] font-mono text-gray-500 mt-1">
                                ${a.release_year}
                            </p>
                        </div>

                        <!-- Footer tags & Streaming Link -->
                        <div class="mt-2.5 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[10px] text-gray-500">
                            <div class="flex items-center gap-1.5">
                                <a href="${a.album_url}" target="_blank" rel="noopener noreferrer"
                                   onclick="event.stopPropagation()"
                                   class="text-[10px] font-semibold text-[#1DB954] bg-[#1DB954]/10 hover:bg-[#1ed760] hover:text-black border border-[#1DB954]/30 px-1.5 py-0.5 rounded transition flex items-center gap-1"
                                   title="Play on Spotify">
                                    🎧 Spotify
                                </a>
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

        // ==========================================
        // 12" GATEFOLD MODAL & AUDIO ENGINE
        // ==========================================
        let currentModalAlbum = null;
        let isModalAudioLoaded = false;

        function openGatefoldModal(albumId) {
            const a = ALL_ALBUMS.find(x => x.album_id === albumId);
            if (!a) return;
            isModalOpen = true;
            currentModalAlbum = a;

            // Desktop elements
            const coverEl = document.getElementById('mCover');
            if (coverEl) coverEl.src = a.album_image_url;
            const titleEl = document.getElementById('mTitle');
            if (titleEl) titleEl.textContent = a.album_name;
            const artistEl = document.getElementById('mArtist');
            if (artistEl) artistEl.textContent = a.album_artist_name;
            const metaEl = document.getElementById('mMeta');
            if (metaEl) metaEl.textContent = `${a.release_year} • ${a.album_genres || 'Album'}`;

            // Mobile elements
            const coverMobile = document.getElementById('mCoverMobile');
            if (coverMobile) coverMobile.src = a.album_image_url;
            const titleMobile = document.getElementById('mTitleMobile');
            if (titleMobile) titleMobile.textContent = a.album_name;
            const artistMobile = document.getElementById('mArtistMobile');
            if (artistMobile) artistMobile.textContent = a.album_artist_name;
            const metaMobile = document.getElementById('mMetaMobile');
            if (metaMobile) metaMobile.textContent = `${a.release_year} • ${a.album_genres || 'Album'}`;

            const stylesEl = document.getElementById('mStyles');
            if (stylesEl) stylesEl.textContent = a.styles || a.album_genres || '';
            const storyEl = document.getElementById('mStory');
            if (storyEl) storyEl.textContent = a.album_description || "Liner notes and critical reception not yet enriched for this title. Stream directly below.";

            let scoresHtml = '';
            if (a.pitchfork_score) {
                scoresHtml += `<span class="bg-red-950/80 border border-red-500/50 text-red-200 text-xs font-black px-2.5 py-1 rounded-lg">Pitchfork: ${a.pitchfork_score}</span>`;
            }
            if (a.metacritic_score) {
                scoresHtml += `<span class="bg-emerald-950/80 border border-emerald-500/50 text-emerald-200 text-xs font-black px-2.5 py-1 rounded-lg">Metacritic: ${a.metacritic_score}</span>`;
            }
            if (a.allmusic_score) {
                scoresHtml += `<span class="bg-blue-950/80 border border-blue-500/50 text-blue-200 text-xs font-black px-2.5 py-1 rounded-lg">AllMusic: ${a.allmusic_score}</span>`;
            }
            if (a.discogs_rating) {
                scoresHtml += `<span class="bg-amber-950/80 border border-amber-500/50 text-amber-200 text-xs font-bold px-2.5 py-1 rounded-lg">Discogs: ${a.discogs_rating}★ (${a.discogs_votes || 0} ratings)</span>`;
            }

            const scoresDesktop = document.getElementById('mScores');
            if (scoresDesktop) scoresDesktop.innerHTML = scoresHtml;
            const scoresMobile = document.getElementById('mScoresMobile');
            if (scoresMobile) scoresMobile.innerHTML = scoresHtml;

            // Links
            const appleOpenUrl = `/open/apple?artist=${encodeURIComponent(a.album_artist_name)}&album=${encodeURIComponent(a.album_name)}`;
            const sDesk = document.getElementById('mSpotify');
            if (sDesk) sDesk.href = a.album_url;
            const aDesk = document.getElementById('mApple');
            if (aDesk) aDesk.href = appleOpenUrl;

            const sMob = document.getElementById('mSpotifyMobile');
            if (sMob) sMob.href = a.album_url;
            const aMob = document.getElementById('mAppleMobile');
            if (aMob) aMob.href = appleOpenUrl;

            const wikiLink = document.getElementById('mWiki');
            if (wikiLink) {
                if (a.wikipedia_url) {
                    wikiLink.href = a.wikipedia_url;
                    wikiLink.style.display = 'inline';
                } else {
                    wikiLink.style.display = 'none';
                }
            }

            const discogsLink = document.getElementById('mDiscogs');
            if (discogsLink) {
                if (a.discogs_url) {
                    discogsLink.href = a.discogs_url;
                    discogsLink.style.display = 'inline';
                } else {
                    discogsLink.style.display = 'none';
                }
            }

            const pList = document.getElementById('mPersonnelList');
            if (pList) {
                pList.innerHTML = '';
                const pCount = document.getElementById('mPersonnelCount');
                if (a.personnel && a.personnel.length > 0) {
                    if (pCount) pCount.textContent = `${a.personnel.length} contributors`;
                    a.personnel.forEach(p => {
                        pList.innerHTML += `
                            <div class="bg-black/30 border border-gray-800/80 rounded-lg p-2 text-[11px] text-gray-300 flex items-center gap-1.5">
                                <span class="text-amber-400 text-xs">•</span>
                                <span class="truncate">${p}</span>
                            </div>
                        `;
                    });
                } else {
                    if (pCount) pCount.textContent = '0 contributors';
                    pList.innerHTML = '<p class="text-xs text-gray-500 col-span-2">No detailed personnel credits recorded yet.</p>';
                }
            }

            // AUDIO CONTINUITY: Keep playing if already active on hover
            const albumKey = `${a.album_artist_name.toLowerCase()}::${a.album_name.toLowerCase()}`;
            const playBtn = document.getElementById('mPlayBtn');
            const statusEl = document.getElementById('mAudioStatus');
            const trackNameEl = document.getElementById('mTrackName');
            const pulseDot = document.getElementById('mPulseDot');

            if (!activeAudio.paused && currentHoverKey === albumKey) {
                isModalAudioLoaded = true;
                if (playBtn) playBtn.textContent = '⏸';
                if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-ping';
                if (statusEl) statusEl.textContent = 'Playing snippet...';
                const cached = previewUrlCache.get(albumKey);
                if (cached && cached.track_name && trackNameEl) {
                    trackNameEl.textContent = cached.track_name;
                }
                hidePreviewToast();
            } else {
                setupGatefoldAudio(a);
            }

            document.getElementById('gatefoldModal').classList.remove('hidden');
        }

        function setupGatefoldAudio(album) {
            isModalAudioLoaded = false;
            activeAudio.pause();
            
            const playBtn = document.getElementById('mPlayBtn');
            const statusEl = document.getElementById('mAudioStatus');
            const trackNameEl = document.getElementById('mTrackName');
            const pulseDot = document.getElementById('mPulseDot');
            const progress = document.getElementById('mAudioProgress');

            if (playBtn) playBtn.textContent = '⏳';
            if (statusEl) statusEl.textContent = 'Fetching preview...';
            if (trackNameEl) trackNameEl.textContent = 'Loading audio snippet...';
            if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-amber-400 animate-pulse';
            if (progress) progress.style.width = '0%';

            fetch(`/api/preview?artist=${encodeURIComponent(album.album_artist_name)}&album=${encodeURIComponent(album.album_name)}`)
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success' && data.preview_url) {
                        activeAudio.src = data.preview_url;
                        isModalAudioLoaded = true;
                        if (playBtn) playBtn.textContent = '▶';
                        if (statusEl) statusEl.textContent = '30s Sample Ready';
                        if (trackNameEl) trackNameEl.textContent = data.track_name || 'Preview Snippet';
                        if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-500';
                    } else {
                        if (playBtn) playBtn.textContent = '✕';
                        if (statusEl) statusEl.textContent = 'No preview available';
                        if (trackNameEl) trackNameEl.textContent = 'Stream on Spotify or Apple Music';
                        if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-gray-600';
                    }
                })
                .catch(() => {
                    if (playBtn) playBtn.textContent = '✕';
                    if (statusEl) statusEl.textContent = 'Error loading preview';
                    if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-red-500';
                });
        }

        function toggleGatefoldAudio() {
            if (!isModalAudioLoaded) return;
            const playBtn = document.getElementById('mPlayBtn');
            const pulseDot = document.getElementById('mPulseDot');
            const statusEl = document.getElementById('mAudioStatus');

            if (activeAudio.paused) {
                activeAudio.play();
                if (playBtn) playBtn.textContent = '⏸';
                if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-ping';
                if (statusEl) statusEl.textContent = 'Playing snippet...';
            } else {
                activeAudio.pause();
                if (playBtn) playBtn.textContent = '▶';
                if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-500';
                if (statusEl) statusEl.textContent = 'Paused';
            }
        }

        activeAudio.ontimeupdate = () => {
            if (activeAudio.duration) {
                const pct = (activeAudio.currentTime / activeAudio.duration) * 100;
                const pBar = document.getElementById('mAudioProgress');
                if (pBar) pBar.style.width = `${pct}%`;
            }
        };

        activeAudio.onended = () => {
            const playBtn = document.getElementById('mPlayBtn');
            const pulseDot = document.getElementById('mPulseDot');
            const statusEl = document.getElementById('mAudioStatus');
            const pBar = document.getElementById('mAudioProgress');
            if (playBtn) playBtn.textContent = '▶';
            if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-500';
            if (statusEl) statusEl.textContent = 'Finished';
            if (pBar) pBar.style.width = '0%';
            hidePreviewToast();
        };

        function seekGatefoldAudio(e) {
            if (!isModalAudioLoaded || !activeAudio.duration) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            activeAudio.currentTime = pos * activeAudio.duration;
        }

        function closeGatefoldModal() {
            isModalOpen = false;
            activeAudio.pause();
            const modal = document.getElementById('gatefoldModal');
            if (modal) modal.classList.add('hidden');
            hidePreviewToast();
            document.querySelectorAll('.audio-pulse').forEach(el => el.classList.add('hidden'));
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeGatefoldModal();
        });

        document.addEventListener('click', (e) => {
            if (e.target && e.target.id === 'gatefoldModal') closeGatefoldModal();
        });
    </script>

    <!-- 12-INCH GATEFOLD SLEEVE MODAL -->
    <div id="gatefoldModal" class="fixed inset-0 z-50 hidden bg-black/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-4">
        <div class="relative w-full max-w-4xl max-h-[94vh] bg-[#12161f] border border-amber-500/40 rounded-2xl sm:rounded-3xl shadow-2xl overflow-y-auto md:overflow-hidden flex flex-col md:flex-row">
            
            <!-- Close Button -->
            <button onclick="closeGatefoldModal()" class="absolute top-3 right-3 z-30 w-8 h-8 rounded-full bg-black/70 text-gray-300 hover:text-white flex items-center justify-center border border-gray-700 text-sm shadow">
                ✕
            </button>

            <!-- MOBILE-ONLY HEADER (Compact & Scroll-Free: ~110px) -->
            <div class="block md:hidden bg-black/50 p-4 border-b border-gray-800 shrink-0 pr-12">
                <div class="flex items-center gap-3">
                    <div class="w-16 h-16 rounded-xl overflow-hidden shrink-0 border border-gray-700/80 shadow">
                        <img id="mCoverMobile" src="" alt="Album Cover" class="w-full h-full object-cover">
                    </div>
                    <div class="flex-1 min-w-0">
                        <h2 id="mTitleMobile" class="text-sm font-black text-white leading-tight truncate"></h2>
                        <p id="mArtistMobile" class="text-xs text-gray-300 truncate mt-0.5"></p>
                        <p id="mMetaMobile" class="text-[10px] text-amber-300/80 font-mono mt-0.5 truncate"></p>
                    </div>
                </div>
                <!-- Score Badges Mobile -->
                <div id="mScoresMobile" class="flex flex-wrap gap-1 mt-2.5"></div>
                <!-- Mobile Streaming Links -->
                <div class="flex items-center gap-2 mt-3 pt-2.5 border-t border-gray-800/80">
                    <a id="mSpotifyMobile" href="#" target="_blank" class="flex-1 bg-[#1DB954] text-black text-[11px] font-black py-1.5 rounded-lg text-center shadow">
                        Spotify
                    </a>
                    <a id="mAppleMobile" href="#" target="_blank" class="flex-1 bg-[#FA233B] text-white text-[11px] font-black py-1.5 rounded-lg text-center shadow">
                        Apple Music
                    </a>
                </div>
            </div>

            <!-- DESKTOP-ONLY LEFT PANEL (12" Full Left Sleeve) -->
            <div class="hidden md:flex w-5/12 bg-black/40 p-6 flex-col justify-between border-r border-gray-800 shrink-0">
                <div>
                    <div class="relative aspect-square max-w-[260px] mx-auto rounded-2xl overflow-hidden shadow-2xl mb-4 border border-gray-700/60">
                        <img id="mCover" src="" alt="Album Cover" class="w-full h-full object-cover">
                    </div>
                    <h2 id="mTitle" class="text-base font-black text-white leading-snug"></h2>
                    <p id="mArtist" class="text-xs text-gray-300 font-medium"></p>
                    <p id="mMeta" class="text-[11px] text-amber-300/80 font-mono mt-0.5"></p>

                    <!-- Critical Score Badges Desktop -->
                    <div id="mScores" class="flex flex-wrap gap-1.5 mt-3"></div>
                </div>

                <!-- Desktop Streaming Links -->
                <div class="mt-4 pt-3 border-t border-gray-800/80 space-y-2">
                    <div class="flex items-center gap-2">
                        <a id="mSpotify" href="#" target="_blank" class="flex-1 bg-[#1DB954] hover:bg-[#1ed760] text-black text-xs font-black py-2 rounded-xl text-center transition shadow">
                            Open Spotify
                        </a>
                        <a id="mApple" href="#" target="_blank" class="flex-1 bg-[#FA233B] hover:bg-[#fb4a5d] text-white text-xs font-black py-2 rounded-xl text-center transition shadow">
                            Apple Music
                        </a>
                    </div>
                    <div class="flex items-center justify-between text-[11px] text-gray-400 pt-1">
                        <a id="mWiki" href="#" target="_blank" class="hover:text-white underline">Wikipedia Article ↗</a>
                        <a id="mDiscogs" href="#" target="_blank" class="hover:text-white underline">Discogs Release ↗</a>
                    </div>
                </div>
            </div>

            <!-- RIGHT PANEL (The Gatefold Liner Notes & Pinned Audio Player) -->
            <div class="w-full md:w-7/12 p-4 sm:p-6 flex flex-col md:max-h-[94vh]">
                <!-- Header -->
                <div class="flex items-center justify-between pb-2 border-b border-gray-800 shrink-0">
                    <span class="text-xs font-mono font-bold tracking-widest text-amber-400 uppercase">
                        📜 COMPLETE LINER NOTES &amp; BACKGROUND
                    </span>
                    <span id="mStyles" class="text-[10px] text-gray-400 bg-gray-800/80 px-2 py-0.5 rounded-full border border-gray-700"></span>
                </div>

                <!-- 30s Audio Sample Player (Pinned at the Top, Never Scrolled Away) -->
                <div class="my-3 p-3 bg-black/50 border border-gray-800/80 rounded-2xl flex flex-col gap-1.5 shrink-0 shadow-sm">
                    <div class="flex items-center justify-between">
                        <span class="text-[10px] font-mono tracking-wider uppercase text-gray-400 font-bold flex items-center gap-1.5">
                            <span id="mPulseDot" class="w-2 h-2 rounded-full bg-gray-500"></span>
                            30s Audio Sample
                        </span>
                        <span id="mAudioStatus" class="text-[10px] font-mono text-gray-400">Loading...</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <button id="mPlayBtn" onclick="toggleGatefoldAudio()" class="w-8 h-8 rounded-full bg-amber-500 hover:bg-amber-400 text-black flex items-center justify-center font-bold text-xs transition shadow-lg shrink-0">
                            ▶
                        </button>
                        <div class="flex-1 min-w-0">
                            <p id="mTrackName" class="text-xs font-semibold text-white truncate">Preparing sample...</p>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden mt-1 cursor-pointer" onclick="seekGatefoldAudio(event)">
                                <div id="mAudioProgress" class="bg-amber-400 h-full w-0 transition-all duration-100"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Scrollable Liner Notes & Story Area -->
                <div class="flex-1 overflow-y-auto custom-scroll pr-1 sm:pr-2 space-y-4">
                    <!-- Story Section -->
                    <div>
                        <h4 class="text-xs font-mono uppercase tracking-wider text-gray-400 font-bold mb-1.5">Album Narrative &amp; Critical Reception</h4>
                        <p id="mStory" class="text-xs text-gray-300 leading-relaxed bg-black/25 p-3.5 rounded-xl border border-gray-800/60"></p>
                    </div>

                    <!-- Personnel Roster Section -->
                    <div>
                        <h4 class="text-xs font-mono uppercase tracking-wider text-gray-400 font-bold mb-2 flex items-center justify-between">
                            <span>Production &amp; Musician Credits</span>
                            <span id="mPersonnelCount" class="text-[10px] text-amber-400 font-normal"></span>
                        </h4>
                        <div id="mPersonnelList" class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pb-6"></div>
                    </div>
                </div>
            </div>

        </div>
    </div>
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

        let isModalOpen = false;

        function onCardLeave(cardEl) {
            if (hoverTimer) clearTimeout(hoverTimer);
            if (isModalOpen) return;
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
                    <div class="spotlight-card border border-gray-800/80 rounded-2xl p-4 flex flex-col justify-between shadow-xl transition duration-300 relative cursor-pointer"
                         onmouseenter="onCardHover('${safeArtist}', '${safeAlbum}', '${a.album_url}', this)"
                         onmouseleave="onCardLeave(this)"
                         onclick="${a.has_gatefold ? `openGatefoldModal('${a.album_id}')` : `window.open('${a.album_url}', '_blank')`}">
                        <div>
                            <div class="flex items-center justify-between mb-3 text-[11px]">
                                <span class="bg-[#1DB954]/20 text-[#1DB954] font-bold px-2.5 py-1 rounded-full border border-[#1DB954]/30">${badgeLabel}</span>
                                <span class="text-gray-400 font-medium">${a.release_year}</span>
                            </div>

                            <div class="relative w-full aspect-square rounded-xl overflow-hidden bg-gray-900 mb-3.5 shadow-md">
                                <img src="${img}" alt="${a.album_name}" class="w-full h-full object-cover">
                                
                                ${a.has_gatefold ? `
                                <button onclick="event.stopPropagation(); openGatefoldModal('${a.album_id}')" 
                                        title="Open 12&quot; Gatefold Liner Notes"
                                        class="absolute top-2.5 left-2.5 w-8 h-8 rounded-full bg-black/60 hover:bg-amber-500 hover:text-black text-amber-300 border border-amber-500/30 backdrop-blur-md flex items-center justify-center transition shadow-lg opacity-90 hover:scale-110 z-20">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                    </svg>
                                </button>
                                ` : ''}

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
                                ${a.has_gatefold ? `
                                <button onclick="event.stopPropagation(); openGatefoldModal('${a.album_id}')"
                                        class="bg-amber-500/15 hover:bg-amber-500 hover:text-black text-amber-300 border border-amber-500/30 text-xs font-bold px-2 py-1.5 rounded-xl transition flex items-center gap-1 shadow">
                                    <span>📖</span> Liner Notes
                                </button>
                                ` : ''}
                                <a href="${appleOpenUrl}" target="_blank" rel="noopener noreferrer"
                                   onclick="event.stopPropagation()"
                                   class="bg-[#FA233B]/15 hover:bg-[#FA233B] hover:text-white text-[#FA233B] border border-[#FA233B]/30 text-xs font-bold px-2.5 py-1.5 rounded-xl transition flex items-center gap-1 shadow">
                                    🍎 Apple
                                </a>
                                <a href="${a.album_url}" target="_blank" rel="noopener noreferrer"
                                   onclick="event.stopPropagation()"
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
                    <div class="card-bg group block rounded-xl p-3 border border-gray-800/80 hover:border-amber-500/30 transition duration-200 shadow-sm flex flex-col justify-between relative cursor-pointer"
                         onmouseenter="onCardHover('${safeArtist}', '${safeAlbum}', '${a.album_url}', this)"
                         onmouseleave="onCardLeave(this)"
                         onclick="${a.has_gatefold ? `openGatefoldModal('${a.album_id}')` : `window.open('${a.album_url}', '_blank')`}">
                        <div>
                            <div class="relative w-full aspect-square rounded-lg overflow-hidden bg-gray-900 mb-2.5">
                                <img src="${img}" alt="${a.album_name}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                                
                                <!-- Top-Left: Gatefold Booklet Icon -->
                                ${a.has_gatefold ? `
                                <button onclick="event.stopPropagation(); openGatefoldModal('${a.album_id}')" 
                                        title="Open 12&quot; Gatefold Liner Notes"
                                        class="absolute top-1.5 left-1.5 w-6 h-6 rounded-full bg-black/60 hover:bg-amber-500 hover:text-black text-amber-300 border border-amber-500/30 backdrop-blur-md flex items-center justify-center transition shadow-lg opacity-90 hover:scale-110 z-20">
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                    </svg>
                                </button>
                                ` : ''}

                                <!-- Top-Right: Number of Plays Badge -->
                                <div class="absolute top-1.5 right-1.5 bg-black/60 backdrop-blur-sm text-[10px] text-gray-200 px-2 py-0.5 rounded-full font-bold">
                                    ${plays}
                                </div>

                                <div class="audio-pulse hidden absolute bottom-1.5 left-1.5 bg-black/85 backdrop-blur-md px-1.5 py-0.5 rounded-full text-[9px] font-bold text-[#1DB954] border border-[#1DB954]/50 shadow-md flex items-center gap-1 z-20">
                                    <span>🎵</span> <span class="animate-pulse">Preview</span>
                                </div>
                            </div>
                            <h4 class="font-bold text-xs text-white truncate group-hover:text-amber-300 transition" title="${a.album_name}">${a.album_name}</h4>
                            <p class="text-[11px] text-gray-400 truncate mt-0.5">${a.album_artist_name}</p>
                        </div>
                        <div class="mt-2 pt-1.5 border-t border-gray-800/60 text-[10px] text-gray-500 flex justify-between items-center">
                            <span>${a.release_year}</span>
                            <div class="flex items-center gap-1">
                                <a href="${appleCandidateOpenUrl}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()"
                                   class="text-[9px] font-semibold text-[#FA233B] bg-[#FA233B]/10 hover:bg-[#FA233B] hover:text-white border border-[#FA233B]/30 px-1.5 py-0.5 rounded transition">
                                    🍎 Apple
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }
            grid.innerHTML = gridHtml;
        }

        document.addEventListener("DOMContentLoaded", () => {
            renderRecommendations();
        });

        // ==========================================
        // 12" GATEFOLD MODAL & AUDIO ENGINE (CRATE DIGGER)
        // ==========================================
        let currentModalAlbum = null;
        let isModalAudioLoaded = false;

        function openGatefoldModal(albumId) {
            const a = ALL_ALBUMS.find(x => x.album_id === albumId);
            if (!a) return;
            isModalOpen = true;
            currentModalAlbum = a;

            // Desktop elements
            const coverEl = document.getElementById('mCover');
            if (coverEl) coverEl.src = a.album_image_url;
            const titleEl = document.getElementById('mTitle');
            if (titleEl) titleEl.textContent = a.album_name;
            const artistEl = document.getElementById('mArtist');
            if (artistEl) artistEl.textContent = a.album_artist_name;
            const metaEl = document.getElementById('mMeta');
            if (metaEl) metaEl.textContent = `${a.release_year} • ${a.album_genres || 'Album'}`;

            // Mobile elements
            const coverMobile = document.getElementById('mCoverMobile');
            if (coverMobile) coverMobile.src = a.album_image_url;
            const titleMobile = document.getElementById('mTitleMobile');
            if (titleMobile) titleMobile.textContent = a.album_name;
            const artistMobile = document.getElementById('mArtistMobile');
            if (artistMobile) artistMobile.textContent = a.album_artist_name;
            const metaMobile = document.getElementById('mMetaMobile');
            if (metaMobile) metaMobile.textContent = `${a.release_year} • ${a.album_genres || 'Album'}`;

            const stylesEl = document.getElementById('mStyles');
            if (stylesEl) stylesEl.textContent = a.styles || a.album_genres || '';
            const storyEl = document.getElementById('mStory');
            if (storyEl) storyEl.textContent = a.album_description || "Liner notes and critical reception not yet enriched for this title. Stream directly below.";

            let scoresHtml = '';
            if (a.pitchfork_score) {
                scoresHtml += `<span class="bg-red-950/80 border border-red-500/50 text-red-200 text-xs font-black px-2.5 py-1 rounded-lg">Pitchfork: ${a.pitchfork_score}</span>`;
            }
            if (a.metacritic_score) {
                scoresHtml += `<span class="bg-emerald-950/80 border border-emerald-500/50 text-emerald-200 text-xs font-black px-2.5 py-1 rounded-lg">Metacritic: ${a.metacritic_score}</span>`;
            }
            if (a.allmusic_score) {
                scoresHtml += `<span class="bg-blue-950/80 border border-blue-500/50 text-blue-200 text-xs font-black px-2.5 py-1 rounded-lg">AllMusic: ${a.allmusic_score}</span>`;
            }
            if (a.discogs_rating) {
                scoresHtml += `<span class="bg-amber-950/80 border border-amber-500/50 text-amber-200 text-xs font-bold px-2.5 py-1 rounded-lg">Discogs: ${a.discogs_rating}★ (${a.discogs_votes || 0} ratings)</span>`;
            }

            const scoresDesktop = document.getElementById('mScores');
            if (scoresDesktop) scoresDesktop.innerHTML = scoresHtml;
            const scoresMobile = document.getElementById('mScoresMobile');
            if (scoresMobile) scoresMobile.innerHTML = scoresHtml;

            // Links
            const appleOpenUrl = `/open/apple?artist=${encodeURIComponent(a.album_artist_name)}&album=${encodeURIComponent(a.album_name)}`;
            const sDesk = document.getElementById('mSpotify');
            if (sDesk) sDesk.href = a.album_url;
            const aDesk = document.getElementById('mApple');
            if (aDesk) aDesk.href = appleOpenUrl;

            const sMob = document.getElementById('mSpotifyMobile');
            if (sMob) sMob.href = a.album_url;
            const aMob = document.getElementById('mAppleMobile');
            if (aMob) aMob.href = appleOpenUrl;

            const wikiLink = document.getElementById('mWiki');
            if (wikiLink) {
                if (a.wikipedia_url) {
                    wikiLink.href = a.wikipedia_url;
                    wikiLink.style.display = 'inline';
                } else {
                    wikiLink.style.display = 'none';
                }
            }

            const discogsLink = document.getElementById('mDiscogs');
            if (discogsLink) {
                if (a.discogs_url) {
                    discogsLink.href = a.discogs_url;
                    discogsLink.style.display = 'inline';
                } else {
                    discogsLink.style.display = 'none';
                }
            }

            const pList = document.getElementById('mPersonnelList');
            if (pList) {
                pList.innerHTML = '';
                const pCount = document.getElementById('mPersonnelCount');
                if (a.personnel && a.personnel.length > 0) {
                    if (pCount) pCount.textContent = `${a.personnel.length} contributors`;
                    a.personnel.forEach(p => {
                        pList.innerHTML += `
                            <div class="bg-black/30 border border-gray-800/80 rounded-lg p-2 text-[11px] text-gray-300 flex items-center gap-1.5">
                                <span class="text-amber-400 text-xs">•</span>
                                <span class="truncate">${p}</span>
                            </div>
                        `;
                    });
                } else {
                    if (pCount) pCount.textContent = '0 contributors';
                    pList.innerHTML = '<p class="text-xs text-gray-500 col-span-2">No detailed personnel credits recorded yet.</p>';
                }
            }

            // AUDIO CONTINUITY: Keep playing if already active on hover
            const albumKey = `${a.album_artist_name.toLowerCase()}::${a.album_name.toLowerCase()}`;
            const playBtn = document.getElementById('mPlayBtn');
            const statusEl = document.getElementById('mAudioStatus');
            const trackNameEl = document.getElementById('mTrackName');
            const pulseDot = document.getElementById('mPulseDot');

            if (!activeAudio.paused && currentHoverKey === albumKey) {
                isModalAudioLoaded = true;
                if (playBtn) playBtn.textContent = '⏸';
                if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-ping';
                if (statusEl) statusEl.textContent = 'Playing snippet...';
                const cached = previewUrlCache.get(albumKey);
                if (cached && cached.track_name && trackNameEl) {
                    trackNameEl.textContent = cached.track_name;
                }
                hidePreviewToast();
            } else {
                setupGatefoldAudio(a);
            }

            document.getElementById('gatefoldModal').classList.remove('hidden');
        }

        function setupGatefoldAudio(album) {
            isModalAudioLoaded = false;
            activeAudio.pause();
            
            const playBtn = document.getElementById('mPlayBtn');
            const statusEl = document.getElementById('mAudioStatus');
            const trackNameEl = document.getElementById('mTrackName');
            const pulseDot = document.getElementById('mPulseDot');
            const progress = document.getElementById('mAudioProgress');

            if (playBtn) playBtn.textContent = '⏳';
            if (statusEl) statusEl.textContent = 'Fetching preview...';
            if (trackNameEl) trackNameEl.textContent = 'Loading audio snippet...';
            if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-amber-400 animate-pulse';
            if (progress) progress.style.width = '0%';

            fetch(`/api/preview?artist=${encodeURIComponent(album.album_artist_name)}&album=${encodeURIComponent(album.album_name)}`)
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success' && data.preview_url) {
                        activeAudio.src = data.preview_url;
                        isModalAudioLoaded = true;
                        if (playBtn) playBtn.textContent = '▶';
                        if (statusEl) statusEl.textContent = '30s Sample Ready';
                        if (trackNameEl) trackNameEl.textContent = data.track_name || 'Preview Snippet';
                        if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-500';
                    } else {
                        if (playBtn) playBtn.textContent = '✕';
                        if (statusEl) statusEl.textContent = 'No preview available';
                        if (trackNameEl) trackNameEl.textContent = 'Stream on Spotify or Apple Music';
                        if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-gray-600';
                    }
                })
                .catch(() => {
                    if (playBtn) playBtn.textContent = '✕';
                    if (statusEl) statusEl.textContent = 'Error loading preview';
                    if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-red-500';
                });
        }

        function toggleGatefoldAudio() {
            if (!isModalAudioLoaded) return;
            const playBtn = document.getElementById('mPlayBtn');
            const pulseDot = document.getElementById('mPulseDot');
            const statusEl = document.getElementById('mAudioStatus');

            if (activeAudio.paused) {
                activeAudio.play();
                if (playBtn) playBtn.textContent = '⏸';
                if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-ping';
                if (statusEl) statusEl.textContent = 'Playing snippet...';
            } else {
                activeAudio.pause();
                if (playBtn) playBtn.textContent = '▶';
                if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-500';
                if (statusEl) statusEl.textContent = 'Paused';
            }
        }

        activeAudio.ontimeupdate = () => {
            if (activeAudio.duration) {
                const pct = (activeAudio.currentTime / activeAudio.duration) * 100;
                const pBar = document.getElementById('mAudioProgress');
                if (pBar) pBar.style.width = `${pct}%`;
            }
        };

        activeAudio.onended = () => {
            const playBtn = document.getElementById('mPlayBtn');
            const pulseDot = document.getElementById('mPulseDot');
            const statusEl = document.getElementById('mAudioStatus');
            const pBar = document.getElementById('mAudioProgress');
            if (playBtn) playBtn.textContent = '▶';
            if (pulseDot) pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-500';
            if (statusEl) statusEl.textContent = 'Finished';
            if (pBar) pBar.style.width = '0%';
            hidePreviewToast();
        };

        function seekGatefoldAudio(e) {
            if (!isModalAudioLoaded || !activeAudio.duration) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const pos = (e.clientX - rect.left) / rect.width;
            activeAudio.currentTime = pos * activeAudio.duration;
        }

        function closeGatefoldModal() {
            isModalOpen = false;
            activeAudio.pause();
            const modal = document.getElementById('gatefoldModal');
            if (modal) modal.classList.add('hidden');
            hidePreviewToast();
            document.querySelectorAll('.audio-pulse').forEach(el => el.classList.add('hidden'));
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeGatefoldModal();
        });

        document.addEventListener('click', (e) => {
            if (e.target && e.target.id === 'gatefoldModal') closeGatefoldModal();
        });
    </script>

    <!-- 12-INCH GATEFOLD SLEEVE MODAL -->
    <div id="gatefoldModal" class="fixed inset-0 z-50 hidden bg-black/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-4">
        <div class="relative w-full max-w-4xl max-h-[94vh] bg-[#12161f] border border-amber-500/40 rounded-2xl sm:rounded-3xl shadow-2xl overflow-y-auto md:overflow-hidden flex flex-col md:flex-row">
            
            <!-- Close Button -->
            <button onclick="closeGatefoldModal()" class="absolute top-3 right-3 z-30 w-8 h-8 rounded-full bg-black/70 text-gray-300 hover:text-white flex items-center justify-center border border-gray-700 text-sm shadow">
                ✕
            </button>

            <!-- MOBILE-ONLY HEADER (Compact & Scroll-Free: ~110px) -->
            <div class="block md:hidden bg-black/50 p-4 border-b border-gray-800 shrink-0 pr-12">
                <div class="flex items-center gap-3">
                    <div class="w-16 h-16 rounded-xl overflow-hidden shrink-0 border border-gray-700/80 shadow">
                        <img id="mCoverMobile" src="" alt="Album Cover" class="w-full h-full object-cover">
                    </div>
                    <div class="flex-1 min-w-0">
                        <h2 id="mTitleMobile" class="text-sm font-black text-white leading-tight truncate"></h2>
                        <p id="mArtistMobile" class="text-xs text-gray-300 truncate mt-0.5"></p>
                        <p id="mMetaMobile" class="text-[10px] text-amber-300/80 font-mono mt-0.5 truncate"></p>
                    </div>
                </div>
                <!-- Score Badges Mobile -->
                <div id="mScoresMobile" class="flex flex-wrap gap-1 mt-2.5"></div>
                <!-- Mobile Streaming Links -->
                <div class="flex items-center gap-2 mt-3 pt-2.5 border-t border-gray-800/80">
                    <a id="mSpotifyMobile" href="#" target="_blank" class="flex-1 bg-[#1DB954] text-black text-[11px] font-black py-1.5 rounded-lg text-center shadow">
                        Spotify
                    </a>
                    <a id="mAppleMobile" href="#" target="_blank" class="flex-1 bg-[#FA233B] text-white text-[11px] font-black py-1.5 rounded-lg text-center shadow">
                        Apple Music
                    </a>
                </div>
            </div>

            <!-- DESKTOP-ONLY LEFT PANEL (12" Full Left Sleeve) -->
            <div class="hidden md:flex w-5/12 bg-black/40 p-6 flex-col justify-between border-r border-gray-800 shrink-0">
                <div>
                    <div class="relative aspect-square max-w-[260px] mx-auto rounded-2xl overflow-hidden shadow-2xl mb-4 border border-gray-700/60">
                        <img id="mCover" src="" alt="Album Cover" class="w-full h-full object-cover">
                    </div>
                    <h2 id="mTitle" class="text-base font-black text-white leading-snug"></h2>
                    <p id="mArtist" class="text-xs text-gray-300 font-medium"></p>
                    <p id="mMeta" class="text-[11px] text-amber-300/80 font-mono mt-0.5"></p>

                    <!-- Critical Score Badges Desktop -->
                    <div id="mScores" class="flex flex-wrap gap-1.5 mt-3"></div>
                </div>

                <!-- Desktop Streaming Links -->
                <div class="mt-4 pt-3 border-t border-gray-800/80 space-y-2">
                    <div class="flex items-center gap-2">
                        <a id="mSpotify" href="#" target="_blank" class="flex-1 bg-[#1DB954] hover:bg-[#1ed760] text-black text-xs font-black py-2 rounded-xl text-center transition shadow">
                            Open Spotify
                        </a>
                        <a id="mApple" href="#" target="_blank" class="flex-1 bg-[#FA233B] hover:bg-[#fb4a5d] text-white text-xs font-black py-2 rounded-xl text-center transition shadow">
                            Apple Music
                        </a>
                    </div>
                    <div class="flex items-center justify-between text-[11px] text-gray-400 pt-1">
                        <a id="mWiki" href="#" target="_blank" class="hover:text-white underline">Wikipedia Article ↗</a>
                        <a id="mDiscogs" href="#" target="_blank" class="hover:text-white underline">Discogs Release ↗</a>
                    </div>
                </div>
            </div>

            <!-- RIGHT PANEL (The Gatefold Liner Notes & Pinned Audio Player) -->
            <div class="w-full md:w-7/12 p-4 sm:p-6 flex flex-col md:max-h-[94vh]">
                <!-- Header -->
                <div class="flex items-center justify-between pb-2 border-b border-gray-800 shrink-0">
                    <span class="text-xs font-mono font-bold tracking-widest text-amber-400 uppercase">
                        📜 COMPLETE LINER NOTES &amp; BACKGROUND
                    </span>
                    <span id="mStyles" class="text-[10px] text-gray-400 bg-gray-800/80 px-2 py-0.5 rounded-full border border-gray-700"></span>
                </div>

                <!-- 30s Audio Sample Player (Pinned at the Top, Never Scrolled Away) -->
                <div class="my-3 p-3 bg-black/50 border border-gray-800/80 rounded-2xl flex flex-col gap-1.5 shrink-0 shadow-sm">
                    <div class="flex items-center justify-between">
                        <span class="text-[10px] font-mono tracking-wider uppercase text-gray-400 font-bold flex items-center gap-1.5">
                            <span id="mPulseDot" class="w-2 h-2 rounded-full bg-gray-500"></span>
                            30s Audio Sample
                        </span>
                        <span id="mAudioStatus" class="text-[10px] font-mono text-gray-400">Loading...</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <button id="mPlayBtn" onclick="toggleGatefoldAudio()" class="w-8 h-8 rounded-full bg-amber-500 hover:bg-amber-400 text-black flex items-center justify-center font-bold text-xs transition shadow-lg shrink-0">
                            ▶
                        </button>
                        <div class="flex-1 min-w-0">
                            <p id="mTrackName" class="text-xs font-semibold text-white truncate">Preparing sample...</p>
                            <div class="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden mt-1 cursor-pointer" onclick="seekGatefoldAudio(event)">
                                <div id="mAudioProgress" class="bg-amber-400 h-full w-0 transition-all duration-100"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Scrollable Liner Notes & Story Area -->
                <div class="flex-1 overflow-y-auto custom-scroll pr-1 sm:pr-2 space-y-4">
                    <!-- Story Section -->
                    <div>
                        <h4 class="text-xs font-mono uppercase tracking-wider text-gray-400 font-bold mb-1.5">Album Narrative &amp; Critical Reception</h4>
                        <p id="mStory" class="text-xs text-gray-300 leading-relaxed bg-black/25 p-3.5 rounded-xl border border-gray-800/60"></p>
                    </div>

                    <!-- Personnel Roster Section -->
                    <div>
                        <h4 class="text-xs font-mono uppercase tracking-wider text-gray-400 font-bold mb-2 flex items-center justify-between">
                            <span>Production &amp; Musician Credits</span>
                            <span id="mPersonnelCount" class="text-[10px] text-amber-400 font-normal"></span>
                        </h4>
                        <div id="mPersonnelList" class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pb-6"></div>
                    </div>
                </div>
            </div>

        </div>
    </div>
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
            raw_url = result.get("collectionViewUrl") or result.get("trackViewUrl") or ""
            m = re.search(r"/album/(?:[^/]+/)?(\d+)", raw_url)
            am_url = f"https://geo.music.apple.com/album/{m.group(1)}?app=music&ls=1" if m else raw_url
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
                "apple_music_url": f"https://geo.music.apple.com/search?term={urllib.parse.quote(term)}&app=music",
                "track_name": None
            }
    except Exception as e:
        payload = {
            "status": "error",
            "message": str(e),
            "preview_url": None,
            "apple_music_url": f"https://geo.music.apple.com/search?term={urllib.parse.quote(f'{artist} {album}')}&app=music",
            "track_name": None
        }

    _preview_cache[key] = payload
    return jsonify(payload)


APPLE_REDIRECT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Opening Apple Music...</title>
    <meta http-equiv="refresh" content="0; url={{ geo_url | safe }}">
    <script>
        // Direct client-side navigation preserves iOS Universal Links
        window.location.replace("{{ geo_url | safe }}");
    </script>
</head>
<body style="background-color: #0c0f12; color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center;">
    <div>
        <p style="font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem;">Opening Apple Music...</p>
        <p style="font-size: 0.85rem; color: #9ca3af; margin-bottom: 1.25rem;">
            If the album doesn't open automatically:
        </p>
        <a href="{{ geo_url | safe }}" style="background-color: #FA233B; color: #fff; font-size: 0.85rem; font-weight: 700; padding: 10px 20px; border-radius: 12px; text-decoration: none; display: inline-block;">
            Tap to Open Album
        </a>
    </div>
</body>
</html>
"""


@app.route("/open/apple")
def open_apple():
    """
    Resolves the exact Apple Music album ID, constructs an international
    geo-routing link (geo.music.apple.com with app=music), and renders
    a client-side redirect so iOS Universal Links open directly to the album.
    """
    artist = request.args.get("artist", "").strip()
    album = request.args.get("album", "").strip()
    if not artist and not album:
        return redirect("https://geo.music.apple.com?app=music")

    key = f"{artist.lower()}::{album.lower()}"
    geo_url = None

    if key in _preview_cache and _preview_cache[key].get("apple_music_url"):
        raw_url = _preview_cache[key]["apple_music_url"]
        m = re.search(r"/album/(?:[^/]+/)?(\d+)", raw_url)
        if m:
            geo_url = f"https://geo.music.apple.com/album/{m.group(1)}?app=music&ls=1"

    if not geo_url:
        term = f"{artist} {album}"
        try:
            res = requests.get(
                "https://itunes.apple.com/search",
                params={"term": term, "entity": "album", "limit": 1},
                timeout=3.5
            )
            data = res.json()
            if data.get("resultCount", 0) > 0:
                raw_url = data["results"][0].get("collectionViewUrl", "")
                m = re.search(r"/album/(?:[^/]+/)?(\d+)", raw_url)
                if m:
                    geo_url = f"https://geo.music.apple.com/album/{m.group(1)}?app=music&ls=1"
        except Exception:
            pass

    if not geo_url:
        fallback_term = urllib.parse.quote(f"{artist} {album}")
        geo_url = f"https://geo.music.apple.com/search?term={fallback_term}&app=music"

    return render_template_string(APPLE_REDIRECT_HTML, geo_url=geo_url)


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
    force_refresh = request.args.get("refresh") in ("1", "true")
    data = fetch_album_data(force_refresh=force_refresh)
    return render_template_string(
        EXPLORER_HTML_TEMPLATE,
        albums=data["albums"],
        top_genres=data["top_genres"],
        kpis=data["kpis"],
        brand_icon=ICON_A_SVG
    )


@app.route("/recommend")
def recommend():
    force_refresh = request.args.get("refresh") in ("1", "true")
    data = fetch_album_data(force_refresh=force_refresh)
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
