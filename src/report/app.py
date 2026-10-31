import os
import json
import time
from collections import Counter
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, Response
from google.cloud import bigquery

app = Flask(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT", "secret-compass-181513")
DATASET_NAME = os.getenv("BQ_DATASET", "spotify")

# Cache query results in memory to make dashboard snappy
CACHE_TTL = 600  # 10 minutes
_cached_data = None
_cache_time = 0


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


SPOTIFY_FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#1DB954"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.494 17.306c-.215.353-.674.466-1.026.25-2.813-1.718-6.353-2.106-10.523-1.153-.404.093-.812-.162-.905-.566-.093-.404.162-.812.566-.905 4.567-1.043 8.47-.6 11.637 1.348.353.215.466.674.251 1.026zm1.467-3.265c-.27.44-.847.578-1.287.308-3.22-1.979-8.127-2.553-11.936-1.396-.498.151-1.03-.135-1.182-.633-.151-.498.135-1.03.633-1.182 4.354-1.32 9.776-.682 13.464 1.616.44.27.578.847.308 1.287zm.126-3.414c-3.86-2.292-10.228-2.504-13.916-1.385-.593.18-1.224-.16-1.404-.753-.18-.593.16-1.224.753-1.404 4.242-1.288 11.278-1.042 15.736 1.605.534.317.708 1.01.392 1.544-.318.535-1.01.71-1.545.394z"/></svg>"""


# ==============================================================================
# TAB 1: LIBRARY EXPLORER (The working, tested dashboard)
# ==============================================================================
EXPLORER_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spotify Album Playlist Explorer</title>
    <!-- Spotify Green Tab Icon -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="alternate icon" href="https://open.spotifycdn.com/cdn/images/favicon.0f31d2ea.ico">
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
                    <svg class="w-9 h-9 text-[#1DB954]" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.494 17.306c-.215.353-.674.466-1.026.25-2.813-1.718-6.353-2.106-10.523-1.153-.404.093-.812-.162-.905-.566-.093-.404.162-.812.566-.905 4.567-1.043 8.47-.6 11.637 1.348.353.215.466.674.251 1.026zm1.467-3.265c-.27.44-.847.578-1.287.308-3.22-1.979-8.127-2.553-11.936-1.396-.498.151-1.03-.135-1.182-.633-.151-.498.135-1.03.633-1.182 4.354-1.32 9.776-.682 13.464 1.616.44.27.578.847.308 1.287zm.126-3.414c-3.86-2.292-10.228-2.504-13.916-1.385-.593.18-1.224-.16-1.404-.753-.18-.593.16-1.224.753-1.404 4.242-1.288 11.278-1.042 15.736 1.605.534.317.708 1.01.392 1.544-.318.535-1.01.71-1.545.394z"/>
                    </svg>
                    <h1 class="text-3xl font-extrabold tracking-tight text-white">Spotify Album Dashboard</h1>
                </div>
                <p class="text-xs text-gray-400 mt-1">Personal catalog & smart playlist explorer</p>
            </div>

            <!-- Quick Action Links -->
            <div class="flex items-center gap-3">
                <button onclick="resetFilters()" class="text-xs text-gray-400 hover:text-white bg-gray-800/80 hover:bg-gray-700 px-3.5 py-2 rounded-lg border border-gray-700 transition">
                    Reset Filters
                </button>
                <a href="https://open.spotify.com" target="_blank" class="text-xs font-semibold text-black bg-[#1DB954] hover:bg-[#1ed760] px-4 py-2 rounded-lg transition shadow-sm">
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

                <!-- Status Filter (Played / Unplayed / All) -->
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
                <span id="filterDescription" class="italic text-gray-500"></span>
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

    <!-- Album Data Payload for Client-side Sorting & Filtering -->
    <script>
        const ALL_ALBUMS = {{ albums | tojson }};
        let filteredAlbums = [...ALL_ALBUMS];
        let displayLimit = 48;
        const PAGE_STEP = 48;

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

                html += `
                    <a href="${a.album_url}" target="_blank" rel="noopener noreferrer"
                       class="card-bg group block rounded-xl p-3 border border-gray-800/80 hover:border-gray-700 transition duration-200 shadow-sm hover:shadow-lg flex flex-col justify-between">
                        <div>
                            <!-- Album Cover -->
                            <div class="relative w-full aspect-square rounded-lg overflow-hidden bg-gray-900 mb-2.5">
                                <img src="${img}" alt="${a.album_name}" loading="lazy"
                                     class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                                
                                <!-- Floating Play Badge overlay -->
                                <div class="absolute top-2 right-2">
                                    ${playsBadge}
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

                        <!-- Footer tags -->
                        <div class="mt-2.5 pt-2 border-t border-gray-800/60 flex items-center justify-between text-[10px] text-gray-500">
                            <span>${a.release_year}</span>
                            <span class="truncate max-w-[100px] text-right" title="${a.album_genres}">${genres}</span>
                        </div>
                    </a>
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
# TAB 2: CRATE DIGGER (Smart personalized album recommender)
# ==============================================================================
RECOMMEND_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crate Digger - Spotify Dash</title>
    <!-- Spotify Green Tab Icon -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="alternate icon" href="https://open.spotifycdn.com/cdn/images/favicon.0f31d2ea.ico">
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
                    <svg class="w-9 h-9 text-[#1DB954]" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.494 17.306c-.215.353-.674.466-1.026.25-2.813-1.718-6.353-2.106-10.523-1.153-.404.093-.812-.162-.905-.566-.093-.404.162-.812.566-.905 4.567-1.043 8.47-.6 11.637 1.348.353.215.466.674.251 1.026zm1.467-3.265c-.27.44-.847.578-1.287.308-3.22-1.979-8.127-2.553-11.936-1.396-.498.151-1.03-.135-1.182-.633-.151-.498.135-1.03.633-1.182 4.354-1.32 9.776-.682 13.464 1.616.44.27.578.847.308 1.287zm.126-3.414c-3.86-2.292-10.228-2.504-13.916-1.385-.593.18-1.224-.16-1.404-.753-.18-.593.16-1.224.753-1.404 4.242-1.288 11.278-1.042 15.736 1.605.534.317.708 1.01.392 1.544-.318.535-1.01.71-1.545.394z"/>
                    </svg>
                    <h1 class="text-3xl font-extrabold tracking-tight text-white">Crate Digger</h1>
                </div>
                <p class="text-xs text-gray-400 mt-1">Smart recommendation engine powered by listening history</p>
            </div>

            <!-- Quick Action Links -->
            <div class="flex items-center gap-3">
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
                        <button onclick="setVibe('vintage')" id="vibeBtn-vintage" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">📻 Crate Digger / Vintage</button>
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
                <!-- Dynamically populated via JavaScript -->
            </div>
        </div>

        <!-- Section: Ranked Candidate Pool Below -->
        <div>
            <div class="flex items-center justify-between mb-4 pb-2 border-b border-gray-800">
                <h3 class="text-sm font-bold uppercase tracking-wider text-gray-300">All Matching Candidates</h3>
                <span class="text-xs text-gray-500" id="candidateSubtext"></span>
            </div>
            <div id="candidateGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                <!-- Dynamically populated via JavaScript -->
            </div>
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

            // Filter base pool
            let pool = ALL_ALBUMS.filter(a => {
                // Mode
                if (selectedMode === 'discover' && (a.album_track_plays || 0) > 0) return false;
                if (selectedMode === 'favorites' && (a.album_track_plays || 0) === 0) return false;

                // Specific Genre
                if (selectedGenre && (!a.album_genres || !a.album_genres.toLowerCase().includes(selectedGenre))) {
                    return false;
                }

                // Era
                const yr = parseInt(a.release_year) || 0;
                if (yr > 0 && (yr < era.min || yr > era.max)) return false;

                return true;
            });

            // Score albums
            const scored = pool.map((a, idx) => {
                let score = 1.0;
                const genres = (a.album_genres || "").toLowerCase();

                // Vibe Matching
                if (selectedVibe !== 'all') {
                    const kws = VIBES[selectedVibe].keywords;
                    let matches = 0;
                    for (let kw of kws) {
                        if (genres.includes(kw)) matches++;
                    }
                    score *= (matches > 0 ? (1.5 + matches * 0.4) : 0.3);
                }

                // Mode weighting
                if (selectedMode === 'favorites') {
                    // Logarithmic scale so top favorites rank high
                    score *= (1 + Math.log10(1 + (a.album_plays || 1)));
                } else {
                    // In discover mode, slightly favor covers with art and verified years
                    if (a.album_image_url) score *= 1.15;
                }

                // Serendipity Jitter for Spin Again
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

                spotlightHtml += `
                    <div class="spotlight-card border border-gray-800/80 rounded-2xl p-4 flex flex-col justify-between shadow-xl transition duration-300">
                        <div>
                            <div class="flex items-center justify-between mb-3 text-[11px]">
                                <span class="bg-[#1DB954]/20 text-[#1DB954] font-bold px-2.5 py-1 rounded-full border border-[#1DB954]/30">${badgeLabel}</span>
                                <span class="text-gray-400 font-medium">${a.release_year}</span>
                            </div>

                            <div class="relative w-full aspect-square rounded-xl overflow-hidden bg-gray-900 mb-3.5 shadow-md">
                                <img src="${img}" alt="${a.album_name}" class="w-full h-full object-cover">
                            </div>

                            <h3 class="font-extrabold text-base text-white truncate" title="${a.album_name}">${a.album_name}</h3>
                            <p class="text-xs font-semibold text-gray-300 truncate mt-0.5">${a.album_artist_name}</p>
                            <p class="text-[11px] text-gray-500 truncate mt-1">${genres}</p>
                        </div>

                        <div class="mt-4 pt-3 border-t border-gray-800/60 flex items-center justify-between">
                            <span class="text-[11px] text-gray-400 font-medium">${playsText}</span>
                            <a href="${a.album_url}" target="_blank" rel="noopener noreferrer"
                               class="bg-[#1DB954] hover:bg-[#1ed760] text-black text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-1.5 shadow">
                                <span>▶</span> Play on Spotify
                            </a>
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

                gridHtml += `
                    <a href="${a.album_url}" target="_blank" rel="noopener noreferrer"
                       class="card-bg group block rounded-xl p-3 border border-gray-800/80 hover:border-gray-700 transition duration-200 shadow-sm flex flex-col justify-between">
                        <div>
                            <div class="relative w-full aspect-square rounded-lg overflow-hidden bg-gray-900 mb-2.5">
                                <img src="${img}" alt="${a.album_name}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                                <div class="absolute top-1.5 right-1.5 bg-black/60 backdrop-blur-sm text-[10px] text-gray-200 px-2 py-0.5 rounded-full font-bold">
                                    ${plays}
                                </div>
                            </div>
                            <h4 class="font-bold text-xs text-white truncate group-hover:text-[#1DB954] transition" title="${a.album_name}">${a.album_name}</h4>
                            <p class="text-[11px] text-gray-400 truncate mt-0.5">${a.album_artist_name}</p>
                        </div>
                        <div class="mt-2 text-[10px] text-gray-500 flex justify-between">
                            <span>${a.release_year}</span>
                            <span class="text-[#1DB954]">▶ Play</span>
                        </div>
                    </a>
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


@app.route("/favicon.svg")
@app.route("/favicon.ico")
def favicon():
    return Response(SPOTIFY_FAVICON_SVG, mimetype="image/svg+xml")


@app.route("/")
def index():
    data = fetch_album_data()
    return render_template_string(
        EXPLORER_HTML_TEMPLATE,
        albums=data["albums"],
        top_genres=data["top_genres"],
        kpis=data["kpis"]
    )


@app.route("/recommend")
def recommend():
    data = fetch_album_data()
    return render_template_string(
        RECOMMEND_HTML_TEMPLATE,
        albums=data["albums"],
        top_genres=data["top_genres"],
        kpis=data["kpis"]
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
