import os
import json
import time
from collections import Counter
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
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


HTML_TEMPLATE = """
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
        .spotify-green { color: #1DB954; }
        .bg-spotify-green { background-color: #1DB954; }
        .bg-spotify-green:hover { background-color: #1ed760; }
        .card-bg { background-color: #181d22; }
        .card-bg:hover { background-color: #21272e; }
        .badge-fav { background: linear-gradient(135deg, #1DB954 0%, #15803d 100%); }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">

    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-6 border-b border-gray-800 gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <svg class="w-9 h-9 text-[#1DB954]" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.494 17.306c-.215.353-.674.466-1.026.25-2.813-1.718-6.353-2.106-10.523-1.153-.404.093-.812-.162-.905-.566-.093-.404.162-.812.566-.905 4.567-1.043 8.47-.6 11.637 1.348.353.215.466.674.251 1.026zm1.467-3.265c-.27.44-.847.578-1.287.308-3.22-1.979-8.127-2.553-11.936-1.396-.498.151-1.03-.135-1.182-.633-.151-.498.135-1.03.633-1.182 4.354-1.32 9.776-.682 13.464 1.616.44.27.578.847.308 1.287zm.126-3.414c-3.86-2.292-10.228-2.504-13.916-1.385-.593.18-1.224-.16-1.404-.753-.18-.593.16-1.224.753-1.404 4.242-1.288 11.278-1.042 15.736 1.605.534.317.708 1.01.392 1.544-.318.535-1.01.71-1.545.394z"/>
                    </svg>
                    <h1 class="text-3xl font-extrabold tracking-tight text-white">Album Playlist Explorer</h1>
                </div>
                <p class="text-xs text-gray-400 mt-1">Smart library browser powered by BigQuery & Cloud Run</p>
            </div>

            <!-- Header Quick Actions -->
            <div class="flex items-center gap-3">
                <button onclick="resetFilters()" class="text-xs text-gray-400 hover:text-white bg-gray-800/80 hover:bg-gray-700 px-3.5 py-2 rounded-lg border border-gray-700 transition">
                    Reset Filters
                </button>
                <a href="https://open.spotify.com" target="_blank" class="text-xs font-semibold text-black bg-[#1DB954] hover:bg-[#1ed760] px-4 py-2 rounded-lg transition shadow-sm">
                    Open Spotify
                </a>
            </div>
        </header>

        <!-- KPI Metrics Ribbon -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="card-bg p-4 rounded-xl border border-gray-800 shadow-sm">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Saved Albums</p>
                <p class="text-2xl font-black mt-1 text-white">{{ kpis.total_albums }}</p>
            </div>
            <div class="card-bg p-4 rounded-xl border border-gray-800 shadow-sm">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Library Explored</p>
                <p class="text-2xl font-black mt-1 text-[#1DB954]">{{ kpis.pct_explored }}%</p>
                <p class="text-[11px] text-gray-500 mt-0.5">{{ kpis.played_albums }} played / {{ kpis.unplayed_albums }} unplayed</p>
            </div>
            <div class="card-bg p-4 rounded-xl border border-gray-800 shadow-sm">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Total Album Plays</p>
                <p class="text-2xl font-black mt-1 text-white">{{ kpis.total_plays }}</p>
            </div>
            <div class="card-bg p-4 rounded-xl border border-gray-800 shadow-sm">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Most Played Album</p>
                <p class="text-base font-bold mt-1 text-white truncate" title="{{ kpis.top_album }}">{{ kpis.top_album }}</p>
                <p class="text-[11px] text-[#1DB954] mt-0.5">{{ kpis.top_album_plays }} album plays</p>
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
            <!-- Dynamically populated via JavaScript -->
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
                // Search filter
                if (query) {
                    const matchName = a.album_name && a.album_name.toLowerCase().includes(query);
                    const matchArtist = a.album_artist_name && a.album_artist_name.toLowerCase().includes(query);
                    if (!matchName && !matchArtist) return false;
                }

                // Genre filter
                if (genre) {
                    if (!a.album_genres || !a.album_genres.toLowerCase().includes(genre)) {
                        return false;
                    }
                }

                // Status filter
                if (status === "favorites" && a.album_track_plays === 0) return false;
                if (status === "unplayed" && a.album_track_plays > 0) return false;

                return true;
            });

            // Sorting
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
            renderGrid();
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

        // Initial render
        document.addEventListener("DOMContentLoaded", () => {
            onFilterChange();
        });
    </script>
</body>
</html>
"""


SPOTIFY_FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#1DB954"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.494 17.306c-.215.353-.674.466-1.026.25-2.813-1.718-6.353-2.106-10.523-1.153-.404.093-.812-.162-.905-.566-.093-.404.162-.812.566-.905 4.567-1.043 8.47-.6 11.637 1.348.353.215.466.674.251 1.026zm1.467-3.265c-.27.44-.847.578-1.287.308-3.22-1.979-8.127-2.553-11.936-1.396-.498.151-1.03-.135-1.182-.633-.151-.498.135-1.03.633-1.182 4.354-1.32 9.776-.682 13.464 1.616.44.27.578.847.308 1.287zm.126-3.414c-3.86-2.292-10.228-2.504-13.916-1.385-.593.18-1.224-.16-1.404-.753-.18-.593.16-1.224.753-1.404 4.242-1.288 11.278-1.042 15.736 1.605.534.317.708 1.01.392 1.544-.318.535-1.01.71-1.545.394z"/></svg>"""


@app.route("/favicon.svg")
@app.route("/favicon.ico")
def favicon():
    from flask import Response
    return Response(SPOTIFY_FAVICON_SVG, mimetype="image/svg+xml")


@app.route("/")
def index():
    data = fetch_album_data()
    return render_template_string(
        HTML_TEMPLATE,
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
