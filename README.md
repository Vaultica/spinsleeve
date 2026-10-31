# Spotify Dash

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Google Cloud Run](https://img.shields.io/badge/GCP-Cloud%20Run%20Jobs-orange.svg)](https://cloud.google.com/run)
[![BigQuery](https://img.shields.io/badge/Storage-BigQuery-blue.svg)](https://cloud.google.com/bigquery)
[![dbt](https://img.shields.io/badge/Transform-dbt-orange.svg)](https://www.getdbt.com/)

An automated, serverless data pipeline that continuously extracts personal Spotify listening history and saved albums, archives the raw JSON to Google Cloud Storage, loads records into BigQuery, transforms the data using dbt, and feeds analytics dashboards in Looker Studio.

---

## Architecture Overview

```text
┌───────────────────────┐
│   Spotify Web API     │
│  (/recently-played)   │
└───────────┬───────────┘
            │ OAuth 2.0 (Headless refresh token)
            ▼
┌─────────────────────────────────────────────────────────────┐
│ Google Cloud Run Job: spotify-pipeline-job (Python 3.11)    │
│  - Scheduled every 2 hours via Cloud Scheduler (europe-west2│
│  - Pulls secrets from Secret Manager                        │
│  - Queries BQ for MAX(played_at) with 10-min lookback buffer│
└───────────┬───────────────────────────────────┬─────────────┘
            │                                   │
            ▼                                   ▼
┌───────────────────────────┐       ┌───────────────────────────────┐
│ Google Cloud Storage      │       │ Google BigQuery               │
│ gs://.../spotify/YYYY/MM/ │       │ Dataset: spotify              │
│ (Raw JSON event archives) │       │ Landing: play_history_new     │
└───────────────────────────┘       └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │ dbt (Data Build Tool) Views   │
                                    │  - playback_history (deduped) │
                                    │  - most_played_tracks         │
                                    │  - most_played_artists        │
                                    │  - most_played_albums         │
                                    │  - all_albums_features        │
                                    └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │ Looker Studio Dashboards      │
                                    │  - Real-time listening stats  │
                                    └───────────────────────────────┘
```

---

## Key Pipeline Features

1. **Headless OAuth 2.0 Automation:**
   - Uses `spotipy.oauth2.SpotifyOAuth` with a permanent refresh token stored in **GCP Secret Manager**.
   - No interactive browser or manual token refreshing required in production.

2. **100% Data Integrity & Gap-Free Polling:**
   - **The Problem:** Spotify's `/me/player/recently-played` API has a hard buffer limit of only 50 tracks. Heavy listening (100–150 songs/day) overflows this buffer every ~3 hours, causing silent data loss on once-daily schedules.
   - **The Solution:** Cloud Scheduler triggers the pipeline **every 2 hours** (`0 */2 * * *`).
   - **Lookback Buffer:** The job queries `SELECT MAX(played_at) FROM play_history_new`, applies a 10-minute lookback buffer, and requests Spotify items with `after=timestamp_ms`. This guarantees boundary events are never dropped across intervals.

3. **Raw Landing + Downstream Deduplication:**
   - Raw play events are preserved in GCS and appended into the landing table `play_history_new`.
   - The downstream dbt model `playback_history` dynamically deduplicates overlapping boundary records using `GROUP BY`, providing clean, consistent metrics for dashboards.

4. **Zero-Idle Serverless Compute:**
   - Runs as a **Cloud Run Job** in `europe-west2` (co-located with Strava pipelines).
   - Container executes to completion in ~10 seconds and terminates, minimizing compute cost.

---

## Repository Structure

```text
spotify-dash/
├── Dockerfile                  # Container definition (Python 3.11-slim)
├── entrypoint.sh               # Cloud Run Job execution wrapper
├── .dockerignore               # Build optimization exclusions
├── .gitignore                  # Git ignore rules (protects credentials & cache)
├── README.md                   # Project documentation
├── src/
│   ├── auth/
│   │   └── get_refresh_token.py # One-time helper to generate refresh token
│   ├── functions/
│   │   ├── main.py             # Core pipeline logic (GCS upload, BQ ingestion)
│   │   └── requirements.txt    # Modernized dependencies
│   └── dbt/spotify-dash/
│       ├── dbt_project.yml     # dbt project configuration (dbt 1.x+)
│       └── models/
│           ├── sources.yml     # BigQuery source definitions
│           └── spotify/        # Analytics models
│               ├── playback_history.sql     # Deduplicated playback events
│               ├── most_played_tracks.sql   # Track ranking
│               ├── most_played_artists.sql  # Artist ranking
│               ├── most_played_albums.sql   # Album ranking
│               └── all_albums_features.sql  # Saved album library analysis
└── tests/
    └── test_functions.py       # Unit tests (mocking BQ, Spotify, GCS)
```

---

## Local Development & Setup

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Google Cloud SDK (`gcloud`)
- A Spotify Developer Application with `http://127.0.0.1:8080/callback` added under Redirect URIs

### 2. Environment Setup
```bash
# Clone repository
git clone https://github.com/Vaultica/spotify-dash.git
cd spotify-dash

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r src/functions/requirements.txt
```

### 3. Generate Spotify Refresh Token (One-Time)
```bash
export SPOTIPY_CLIENT_ID="<your_client_id>"
export SPOTIPY_CLIENT_SECRET="<your_client_secret>"
export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8080/callback"

python src/auth/get_refresh_token.py
```
This launches a browser window to authorize your Spotify app and outputs your permanent `SPOTIPY_REFRESH_TOKEN`.

### 4. Running Unit Tests
```bash
python tests/test_functions.py
```

### 5. Running Ingestion Locally
```bash
export SPOTIPY_REFRESH_TOKEN="<your_refresh_token>"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service_account.json"

# Ingest recently played tracks:
python src/functions/main.py tracks

# Ingest saved albums:
python src/functions/main.py albums
```

---

## Cloud Deployment (Google Cloud Platform)

### 1. Store Secrets in Secret Manager
```bash
echo -n "<client_id>"     | gcloud secrets create SPOTIPY_CLIENT_ID --data-file=-
echo -n "<client_secret>" | gcloud secrets create SPOTIPY_CLIENT_SECRET --data-file=-
echo -n "<refresh_token>" | gcloud secrets create SPOTIPY_REFRESH_TOKEN --data-file=-
```

### 2. Build Container Image (Cloud Build)
```bash
gcloud builds submit . \
  --tag=europe-west2-docker.pkg.dev/<PROJECT_ID>/spotify-repo/spotify-pipeline:latest
```

### 3. Deploy Cloud Run Job
```bash
gcloud run jobs create spotify-pipeline-job \
  --image=europe-west2-docker.pkg.dev/<PROJECT_ID>/spotify-repo/spotify-pipeline:latest \
  --region=europe-west2 \
  --service-account=spotify-data@<PROJECT_ID>.iam.gserviceaccount.com \
  --set-env-vars="GCP_PROJECT=<PROJECT_ID>,GCS_BUCKET=<PROJECT_ID>,BQ_DATASET=spotify" \
  --set-secrets="SPOTIPY_CLIENT_ID=SPOTIPY_CLIENT_ID:latest,SPOTIPY_CLIENT_SECRET=SPOTIPY_CLIENT_SECRET:latest,SPOTIPY_REFRESH_TOKEN=SPOTIPY_REFRESH_TOKEN:latest" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=1 \
  --task-timeout=10m
```

### 4. Configure Automated Schedule (Cloud Scheduler)
Runs every 2 hours:
```bash
gcloud scheduler jobs create http spotify-daily-sync \
  --location=europe-west2 \
  --schedule="0 */2 * * *" \
  --time-zone="UTC" \
  --uri="https://europe-west2-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/<PROJECT_ID>/jobs/spotify-pipeline-job:run" \
  --http-method=POST \
  --oauth-service-account-email="spotify-data@<PROJECT_ID>.iam.gserviceaccount.com" \
  --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
  --description="Automated 2-hour sync for Spotify listening history"
```

---

## Operational Commands

### Trigger Job Manually
```bash
gcloud run jobs execute spotify-pipeline-job --region=europe-west2 --wait
```

### Read Latest Logs
```bash
gcloud beta run jobs executions logs read <EXECUTION_NAME> --region=europe-west2
```

### Query Recent Plays in BigQuery
```sql
SELECT
  track_name,
  track_album_artists_0_name AS artist_name,
  track_album_name           AS album_name,
  TIMESTAMP(played_at)       AS played_at,
  track_uri
FROM
  `<PROJECT_ID>.spotify.playback_history`
ORDER BY
  played_at DESC
LIMIT 50;
```

---

## License
Apache License 2.0 - See [LICENSE](LICENSE) for details.
