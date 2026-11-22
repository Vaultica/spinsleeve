# SpinSleeve Macro-Genre Classification & Filtering Decision Table

This decision table details the end-to-end logic of how albums are mapped to macro-genres, how the UI dropdown is populated, and how filtering evaluates album records.

---

## 1. Pipeline Enrichment & Classification Logic (`src/pipeline_v2/classifier.py`)

When an album is enriched by `enrich.py`, raw metadata from Spotify (artist/album genres), Discogs (styles), and MusicBrainz (tags) are concatenated into a lowercase text corpus:
`corpus = f"{genres_str or ''} {styles_str or ''} {mb_tags or ''}".lower()`

### Evaluation Rule: **Sequential First-Match Win**
The classifier evaluates `corpus` against prioritized regex pattern rules (`MACRO_GENRE_RULES`) **sequentially from top to bottom**. The **first** matching regex pattern wins and assigns the primary macro-genre. Tags are aggregated cumulatively into the corpus, but precedence is determined by the order of rules in the classification pipeline.

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
| **Fallback** | *No regex pattern matched* | Assigned to **`Other / Unclassified`** |

---

## 2. Terminology: Raw Genres vs. Normalized Macro-Genres

* **Raw Genres (`album_genres`):** These are the original, unfiltered micro-genre tags returned directly by Spotify (e.g., `"uk alternative hip hop"`, `"chamber psych"`, `"detroit indie"`).
* **Normalized Macro-Genres (`macro_genre`):** These are the high-level, standardized Level-1 categories (e.g., `"Electronic"`, `"Rock"`, `"Pop"`, `"Other / Unclassified"`) assigned by the classifier for clean library navigation and filtering.

---

## 3. Dropdown Population Logic (`src/report_v2/services/catalog.py`)

* **Source Data:** Rendered in `explorer.html` as the level-1 Macro-Genre filter dropdown (`#genreSelect`), populated strictly from the distinct normalized macro-genres present in the user's library (`macro_genre_counter`).

---

## 4. UI Filtering & Recommendation Matching (`src/report_v2/templates/explorer.html`)

When a user selects a macro-genre from the dropdown (or uses Crate Digger mode), dual-layer matching evaluates both macro-genres and raw genres:

| Condition / Input | Matching Logic (`matchG` / `runRecommender`) | Outcome |
| :--- | :--- | :--- |
| **`genre === "all"`** | Matches all records | Returns all albums |
| **Macro-Genre Match** | `a.macro_genre.toLowerCase() === genre` OR `a.macro_genre.toLowerCase().includes(genre)` | Matches albums assigned to that macro-genre |
| **Raw Genre Match** | `a.album_genres.toLowerCase().includes(genre)` | Fallback: matches albums whose raw Spotify/Discogs genres contain the keyword |
| **Mismatch** | Neither macro-genre nor raw genres match | Album is filtered out of the current view |
