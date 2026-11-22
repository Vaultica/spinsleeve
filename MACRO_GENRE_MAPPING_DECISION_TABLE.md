# SpinSleeve Macro-Genre Classification & Filtering Decision Table

This decision table details the end-to-end logic of how albums are mapped to macro-genres, how the UI dropdown is populated, and how filtering evaluates album records.

---

## 1. Pipeline Enrichment & Classification Logic (`src/pipeline_v2/classifier.py`)

When an album is enriched by `enrich.py`, raw metadata from Spotify (artist/album genres), Discogs (styles), and MusicBrainz (tags) are concatenated into a lowercase text corpus:
`corpus = f"{genres_str or ''} {styles_str or ''} {mb_tags or ''}".lower()`

The classifier evaluates `corpus` against prioritized regex pattern rules (`MACRO_GENRE_RULES`) in sequential order:

| Macro-Genre | Trigger Regex Patterns (`MACRO_GENRE_RULES`) | Example Spotify/Discogs Tags |
| :--- | :--- | :--- |
| **Ambient** | `\bambient\b`, `\bdrone\b`, `\bsoundscape\b`, `\bfield recordings?\b`, `\bnew age\b` | ambient, drone, soundscape |
| **Metal** | `\bmetal\b`, `\bthrash\b`, `\bdoom metal\b`, `\bblack metal\b`, `\bdeath metal\b`, `\bgrindcore\b`, `\bheavy metal\b` | heavy metal, death metal, thrash |
| **Punk / Alternative** | `\bpunk\b`, `\bpost-punk\b`, `\bhardcore punk\b`, `\bgrunge\b`, `\bemo\b`, `\briot grrrl\b`, `\bgarage punk\b` | post-punk, grunge, hardcore |
| **Electronic** | `\belectronic\b`, `\bedm\b`, `\bclub\b`, `\btechno\b`, `\bhouse\b`, `\belectro\b`, `\bidm\b`, `\bdrum and bass\b`, `\bdnb\b`, `\btrance\b`, `\bdowntempo\b`, `\btrip hop\b`, `\bsynth-?pop\b`, `\belectronica\b`, `\buk bass\b`, `\buk garage\b`, `\bgarage\b`, `\bbass\b`, `\bbreaks?\b`, `\bbreakbeat\b`, `\bhyperpop\b`, `\bglitch\b` | electronica, idm, house, uk bass |
| **Hip-Hop** | `\bhip[ -]?hop\b`, `\brap\b`, `\btrap\b`, `\bboom bap\b`, `\bdrill\b`, `\bconscious rap\b` | hip hop, rap, trap |
| **Jazz** | `\bjazz\b`, `\bbebop\b`, `\bhard bop\b`, `\bmodal jazz\b`, `\bfusion\b`, `\bfree jazz\b`, `\bbig band\b`, `\bcool jazz\b` | jazz, bebop, fusion |
| **R&B / Soul** | `\br&b\b`, `\bsoul\b`, `\bfunk\b`, `\bmotown\b`, `\bneo[ -]soul\b`, `\bcontemporary r&b\b`, `\bgospel\b` | soul, funk, neo-soul |
| **Classical** | `\bclassical\b`, `\bchamber music\b`, `\bsymphon(?:y|ic)\b`, `\bchoral\b`, `\bopera\b`, `\bmodern classical\b` | classical, chamber music, symphony |
| **Folk / Country** | `\bfolk\b`, `\bcountry\b`, `\bbluegrass\b`, `\bamericana\b`, `\bappalachian\b`, `\bsinger-songwriter\b`, `\balt-country\b` | folk, country, americana |
| **Reggae / Dub** | `\breggae\b`, `\bdub\b`, `\bska\b`, `\broots reggae\b`, `\bdancehall\b`, `\brocker\b` | reggae, dub, ska |
| **Blues** | `\bblues\b`, `\bdelta blues\b`, `\bchicago blues\b`, `\belectric blues\b` | blues, chicago blues |
| **Rock** | `\brock\b`, `\bindie rock\b`, `\bpsychedelic rock\b`, `\bprog(?:ressive)? rock\b`, `\bshoegaze\b`, `\bclassic rock\b`, `\bart rock\b`, `\bhard rock\b` | indie rock, psychedelic rock, shoegaze |
| **Pop** | `\bpop\b`, `\bindie pop\b`, `\bdance-pop\b`, `\bchamber pop\b`, `\bbaroque pop\b`, `\bpower pop\b` | pop, indie pop, baroque pop, chamber pop |
| **Latin / World** | `\blatin\b`, `\bbossa nova\b`, `\btango\b`, `\bsamba\b`, `\bafrobeat\b`, `\bcumbia\b`, `\bflamenco\b`, `\bworld\b` | latin, bossa nova, afrobeat |
| **Fallback** | *No regex pattern matched* | Assigned to **`Eclectic / Other`** |

---

## 2. Dropdown Population Logic (`src/report_v2/services/catalog.py`)

* **Source Data:** When loading user catalogs from BigQuery or Cloud Datastore cache (`UserCatalogCache`), the service builds `top_genres` strictly by counting distinct macro-genres (`macro_genre`) present across all saved albums in the user's library (excluding `"Eclectic / Other"` and `"Unknown"`).
* **UI Delivery:** Rendered in `explorer.html` as the level-1 Macro-Genre filter dropdown (`#genreSelect`).

---

## 3. UI Filtering & Recommendation Matching (`src/report_v2/templates/explorer.html`)

When a user selects a macro-genre from the dropdown (or uses Crate Digger mode), dual-layer matching is evaluated:

| Condition / Input | Matching Logic (`matchG` / `runRecommender`) | Outcome |
| :--- | :--- | :--- |
| **`genre === "all"`** | Matches all records | Returns all albums |
| **Macro-Genre Match** | `a.macro_genre.toLowerCase() === genre` OR `a.macro_genre.toLowerCase().includes(genre)` | Matches albums assigned to that macro-genre |
| **Raw Genre Match** | `a.album_genres.toLowerCase().includes(genre)` | Fallback: matches albums whose raw Spotify/Discogs genres contain the keyword |
| **Mismatch** | Neither macro-genre nor raw genres match | Album is filtered out of the current view |
