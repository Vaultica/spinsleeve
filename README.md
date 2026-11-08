# SpinSleeve

[![Live Application](https://img.shields.io/badge/Live%20App-spinsleeve.cc-1DB954.svg)](https://spinsleeve.cc)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Google Cloud Run](https://img.shields.io/badge/GCP-Cloud%20Run-orange.svg)](https://cloud.google.com/run)
[![BigQuery](https://img.shields.io/badge/Storage-BigQuery-blue.svg)](https://cloud.google.com/bigquery)
[![Cloud Datastore](https://img.shields.io/badge/Database-Datastore-green.svg)](https://cloud.google.com/datastore)

---

## 1. Purpose & Mission

**SpinSleeve** (`https://spinsleeve.cc`) is a multi-tenant physical-style virtual vinyl crate, 12" gatefold archival liner notes reader, listening telemetry engine, and friend-to-friend taste compatibility platform.

### High-Level Goals & Mission
* **Digital Curation to Physical Ritual:** Transform flat digital streaming libraries into interactive 12" record crates complete with tactile spinning vinyl platters, album sleeve badges (`🔥 X Plays`), and unowned discovery crates (`"You Should Save These"`).
* **Archival Storytelling:** Unify streaming history with rich editorial context, scraping Wikipedia, Discogs, and Pitchfork reviews to deliver 12" gatefold liner notes, ratings, and personnel rosters.
* **Multi-Tenant Social Lounge (SpinPals):** Enable music collectors to connect, compare hybrid acoustic compatibility scores, and discover top borrow recommendations.
* **Serverless Scale & Data Isolation:** Built on a robust multi-tenant Google Cloud architecture ensuring strict tenant data isolation in BigQuery (`spotify_v2`) backed by blazing-fast Cloud Datastore document caching (`~50ms` loads).

---

## 2. Architecture Topology (Mermaid)

```mermaid
graph TD
    User["🌐 Collector (Browser)"] -->|HTTPS / SSL| Firebase["Firebase Hosting CDN (Reverse Proxy)"]
    Firebase -->|__session Cookie & Rewrites| CloudRun["Cloud Run Service: spotify-dashboard-beta\n(Flask Multi-Tenant V2 App)"]
    
    subgraph "Google Cloud Platform (secret-compass-181513)"
        CloudRun -->|Read/Write Caches & User Vault| Datastore["Google Cloud Datastore\n(Users, Tokens, UserCatalogCache)"]
        CloudRun -->|Analytical Queries & Materialized Views| BigQuery["Google BigQuery (US)\nDataset: spotify_v2\n(playback_history, user_saved_albums, album_enriched_metadata)"]
        
        Scheduler["Cloud Scheduler\n(Every 2h Sync / Daily Enrichment)"] -->|OIDC Trigger| CloudJob["Cloud Run Job\nspotify-v2-pipeline-job & enrichment-job"]
        CloudJob -->|Refresh Tokens & Ingest Plays| SpotifyAPI["Spotify Web API"]
        CloudJob -->|Load Scrobbles & Rematerialize| BigQuery
        CloudJob -->|Invalidate Document Cache| Datastore
    end
```

---

## 3. Project File Map

* **`src/report_v2/app.py`:** Production multi-tenant Flask application (`Library Explorer`, `Crate Digger`, `Analytics`, `SpinPals`, and `Admin Control Deck`).
* **`src/pipeline_v2/sync.py`:** Automated multi-tenant synchronization engine ingesting plays and saved albums into BigQuery.
* **`src/pipeline_v2/enrich.py`:** V2 album metadata scraper enriching records with 12" gatefold archival liner notes.
* **`manage_users.py`:** Administrative CLI tool for managing user approvals and permissions.
* **`INFRA_RUNBOOK.md` & `TECHNICAL_SPECS.md`:** Comprehensive infrastructure runbooks and technical specifications.

---

## 4. Operational Commands

### Execute Multi-Tenant Pipeline On-Demand
```bash
gcloud run jobs execute spotify-v2-pipeline-job --region=europe-west2
```

### Execute V2 Album Metadata Enrichment On-Demand
```bash
gcloud run jobs execute spotify-v2-enrichment-job --region=europe-west2 --args="enrich.py,100"
```

### Deploy Updated Beta App
```bash
CLOUDSDK_PYTHON=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
  gcloud builds submit src/report_v2 --tag=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-dashboard-v2:latest
gcloud run deploy spotify-dashboard-beta \
  --image=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-dashboard-v2:latest \
  --region=europe-west2
```

---

## 5. License

PolyForm Noncommercial License 1.0.0 — See [LICENSE](LICENSE) for details.
