# SpinSleeve Infrastructure & Disaster Recovery Runbook

This document is the definitive, standalone reference to rebuild the entire SpinSleeve infrastructure on Google Cloud Platform (GCP) from scratch without relying on external memory or undocumented steps.

---

## 1. Global Project Specifications

| Attribute | Production Value |
| :--- | :--- |
| **GCP Project ID** | `secret-compass-181513` |
| **GCP Project Number** | `759946514926` |
| **Compute Region (Cloud Run Services & Jobs)** | `europe-west2` (London) |
| **Datastore / Firestore Region** | `europe-west2` (London, Datastore Mode, Free Tier) |
| **BigQuery Dataset Region** | `US` (Multi-region) |
| **Cloud Storage Bucket** | `gs://secret-compass-181513` |
| **Custom Domain** | `https://spinsleeve.cc` |
| **Beta Custom Domain** | `https://spinsleeve.cc/beta` |
| **Domain Registrar** | Namecheap (DNS A: `199.36.158.100`, CNAME: `spinsleeve.cc.`) |
| **Reverse Proxy & SSL** | Google Firebase Hosting site `secret-compass-181513` |

---

## 2. Service Accounts & IAM Permissions

### Primary Dedicated Service Account
```bash
SA_NAME="spotify-data"
SA_EMAIL="${SA_NAME}@secret-compass-181513.iam.gserviceaccount.com"

# Create service account (if initializing a new project)
gcloud iam service-accounts create $SA_NAME \
    --display-name="SpinSleeve Service Account" \
    --project=secret-compass-181513
```

### Required IAM Policy Bindings
Run these commands to grant the necessary roles:
```bash
PROJECT_ID="secret-compass-181513"
SA_EMAIL="spotify-data@secret-compass-181513.iam.gserviceaccount.com"

# 1. BigQuery Full Access (Queries, Views, DDL)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.admin"

# 2. Secret Manager Access (Client ID, Client Secret, Refresh Token)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# 3. Cloud Storage Access (Raw JSON Ingestion Archives)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin"

# 4. Cloud Run Invocation (For Cloud Scheduler to trigger Cloud Run Jobs)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker"

# 5. Cloud Datastore / Firestore (Multi-Tenant User & Session Vault)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/datastore.owner"
```

---

## 3. Secret Manager Credentials

SpinSleeve stores all sensitive secrets in Google Cloud Secret Manager:

```bash
# Create secrets
gcloud secrets create SPOTIPY_CLIENT_ID --replication-policy="automatic"
gcloud secrets create SPOTIPY_CLIENT_SECRET --replication-policy="automatic"
gcloud secrets create SPOTIPY_REFRESH_TOKEN --replication-policy="automatic"
gcloud secrets create FLASK_SECRET_KEY --replication-policy="automatic"

# Add versions (pass values via stdin or files)
echo -n "YOUR_SPOTIFY_CLIENT_ID" | gcloud secrets versions add SPOTIPY_CLIENT_ID --data-file=-
echo -n "YOUR_SPOTIFY_CLIENT_SECRET" | gcloud secrets versions add SPOTIPY_CLIENT_SECRET --data-file=-
echo -n "YOUR_SPOTIFY_REFRESH_TOKEN" | gcloud secrets versions add SPOTIPY_REFRESH_TOKEN --data-file=-
echo -n "spinsleeve-beta-secure-session-key-2026" | gcloud secrets versions add FLASK_SECRET_KEY --data-file=-
```

---

## 4. Artifact Registry Docker Repository

SpinSleeve Docker container images are stored in a dedicated regional repository:

```bash
# Create Docker repository in europe-west2
gcloud artifacts repositories create spotify-repo \
    --repository-format=docker \
    --location=europe-west2 \
    --description="SpinSleeve Docker Images" \
    --project=secret-compass-181513
```

---

## 5. BigQuery Data Layer

### Dataset 1: `spotify` (Legacy V1 Single-Tenant Dataset)
Location: `US`
* `spotify.play_history_new`: Append-only stream of listening history.
* `spotify.all_albums`: Saved album library (updated by ingestion).
* `spotify.album_enriched_metadata`: Universal archival liner notes (Wikipedia, Pitchfork, Discogs).
* `spotify.all_albums_features`: Core view joining albums + plays + enriched metadata.

### Dataset 2: `spotify_v2` (Modern Multi-Tenant Dataset)
Location: `US`

```bash
# Create v2 dataset
bq --location=US mk --dataset \
    --description="SpinSleeve Multi-Tenant V2 Analytics & Library Dataset" \
    secret-compass-181513:spotify_v2
```

#### Table 1: `playback_history` (Partitioned & Clustered)
```sql
CREATE TABLE IF NOT EXISTS `secret-compass-181513.spotify_v2.playback_history` (
  user_id STRING NOT NULL,
  played_at TIMESTAMP NOT NULL,
  track_uri STRING,
  track_id STRING,
  track_name STRING,
  artist_id STRING,
  artist_name STRING,
  album_id STRING,
  album_name STRING
)
PARTITION BY DATE(played_at)
CLUSTER BY user_id, artist_name;
```

#### Table 2: `user_saved_albums` (Clustered Library State)
```sql
CREATE TABLE IF NOT EXISTS `secret-compass-181513.spotify_v2.user_saved_albums` (
  user_id STRING NOT NULL,
  album_id STRING NOT NULL,
  album_uri STRING,
  album_name STRING NOT NULL,
  artist_id STRING,
  artist_name STRING NOT NULL,
  added_at TIMESTAMP,
  release_date STRING,
  release_year INT64,
  tracks_total INT64,
  album_type STRING,
  label STRING,
  image_url STRING,
  genres STRING
)
CLUSTER BY user_id, artist_name;
```

#### Table 3: `album_enriched_metadata` (Universal & Shared)
```sql
CREATE OR REPLACE TABLE `secret-compass-181513.spotify_v2.album_enriched_metadata` AS
SELECT * FROM `secret-compass-181513.spotify.album_enriched_metadata`;
```

#### View: `user_albums_features` (Dynamic Multi-Tenant View)
```sql
CREATE OR REPLACE VIEW `secret-compass-181513.spotify_v2.user_albums_features` AS
WITH album_plays_by_id AS (
  SELECT 
    user_id,
    album_id,
    COUNT(*) as track_plays_by_id,
    COUNTIF(played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)) as track_plays_by_id_30d
  FROM `secret-compass-181513.spotify_v2.playback_history`
  WHERE album_id IS NOT NULL AND album_id != ""
  GROUP BY user_id, album_id
),
album_plays_by_name AS (
  SELECT 
    user_id,
    LOWER(TRIM(album_name)) as norm_album_name,
    LOWER(TRIM(artist_name)) as norm_artist_name,
    COUNT(*) as track_plays_by_name,
    COUNTIF(played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)) as track_plays_by_name_30d
  FROM `secret-compass-181513.spotify_v2.playback_history`
  GROUP BY user_id, norm_album_name, norm_artist_name
),
raw_albums AS (
  SELECT 
    a.*,
    ROW_NUMBER() OVER(
      PARTITION BY a.user_id, LOWER(TRIM(a.artist_name)), LOWER(TRIM(a.album_name))
      ORDER BY 
        CASE WHEN a.image_url IS NOT NULL AND a.image_url != "" THEN 1 ELSE 2 END ASC,
        a.added_at DESC
    ) as dedupe_rank
  FROM `secret-compass-181513.spotify_v2.user_saved_albums` a
  WHERE COALESCE(a.tracks_total, 0) > 2
),
deduped AS (
  SELECT * FROM raw_albums WHERE dedupe_rank = 1
)
SELECT 
  d.user_id,
  d.album_id,
  d.album_name,
  d.artist_name as album_artist_name,
  d.added_at,
  d.release_date as album_release_date,
  d.release_year,
  d.tracks_total as album_tracks_total,
  d.album_type,
  d.label as album_label,
  d.image_url as album_image_url,
  d.genres as album_genres,
  GREATEST(COALESCE(pid.track_plays_by_id, 0), COALESCE(pname.track_plays_by_name, 0)) as album_track_plays,
  ROUND(GREATEST(COALESCE(pid.track_plays_by_id, 0), COALESCE(pname.track_plays_by_name, 0)) / NULLIF(d.tracks_total, 0), 1) as album_plays,
  GREATEST(COALESCE(pid.track_plays_by_id_30d, 0), COALESCE(pname.track_plays_by_name_30d, 0)) as album_track_plays_30d,
  ROUND(GREATEST(COALESCE(pid.track_plays_by_id_30d, 0), COALESCE(pname.track_plays_by_name_30d, 0)) / NULLIF(d.tracks_total, 0), 1) as album_plays_30d,
  CONCAT("https://open.spotify.com/album/", d.album_id) as album_url,
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
FROM deduped d
LEFT JOIN album_plays_by_id pid
  ON d.user_id = pid.user_id AND d.album_id = pid.album_id
LEFT JOIN album_plays_by_name pname
  ON d.user_id = pname.user_id 
  AND LOWER(TRIM(d.album_name)) = pname.norm_album_name
  AND LOWER(TRIM(d.artist_name)) = pname.norm_artist_name
LEFT JOIN `secret-compass-181513.spotify_v2.album_enriched_metadata` e
  ON d.album_id = e.album_id;
```

#### Table 4: `user_albums_features_table` (Materialized Physical Table - INFRA-03a)
*Re-materialized automatically by `sync.py` and `enrich.py` pipeline runs to bypass analytical view compilation.*
```sql
CREATE OR REPLACE TABLE `secret-compass-181513.spotify_v2.user_albums_features_table`
CLUSTER BY user_id AS
SELECT * FROM `secret-compass-181513.spotify_v2.user_albums_features`;
```

---

## 6. Cloud Run Services (Web Applications)

### Primary Service: `spotify-dashboard-beta` (V2 Multi-Tenant Production)
Serves all live production traffic for `https://spinsleeve.cc` (as well as `/beta/*` backward-compatible paths):
```bash
# Build production multi-tenant container image
CLOUDSDK_PYTHON=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
  gcloud builds submit src/report_v2 \
    --tag=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-dashboard-v2:latest

# Deploy to Cloud Run
CLOUDSDK_PYTHON=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
  gcloud run deploy spotify-dashboard-beta \
    --image=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-dashboard-v2:latest \
    --region=europe-west2 \
    --service-account=spotify-data@secret-compass-181513.iam.gserviceaccount.com \
    --set-env-vars=GCP_PROJECT=secret-compass-181513 \
    --allow-unauthenticated
```

### Legacy Service: `spotify-dashboard-service` (V1 Single-User - Deprecated)
Retained for disaster recovery rollback. All public traffic has been flipped to `spotify-dashboard-beta` via Firebase Hosting.

---

## 7. Cloud Run Jobs (Ingestion & Enrichment Pipelines)

### Job 1: `spotify-pipeline-job` (V1 Ingestion - Deprecated)
Legacy single-user ingestion job. Triggers were paused in Phase 6.

### Job 2: `spotify-enrichment-job` (V1 Legacy Archive Enrichment - Deprecated)
Legacy single-user enrichment job targeting `spotify.album_enriched_metadata`. Replaced by `spotify-v2-enrichment-job`.

### Job 3: `spotify-v2-pipeline-job` (Active V2 Multi-Tenant Pipeline)
Loops through all approved friends in Datastore, refreshes their individual tokens, and syncs tracks and saved albums into `spotify_v2`:
```bash
# Build multi-tenant pipeline container (includes both sync.py and enrich.py)
CLOUDSDK_PYTHON=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
  gcloud builds submit src/pipeline_v2 \
    --tag=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-v2-pipeline:latest

# Deploy Sync Job
gcloud run jobs deploy spotify-v2-pipeline-job \
    --image=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-v2-pipeline:latest \
    --region=europe-west2 \
    --service-account=spotify-data@secret-compass-181513.iam.gserviceaccount.com \
    --set-env-vars=GCP_PROJECT=secret-compass-181513,GCS_BUCKET=secret-compass-181513 \
    --set-secrets=SPOTIPY_CLIENT_ID=SPOTIPY_CLIENT_ID:latest,SPOTIPY_CLIENT_SECRET=SPOTIPY_CLIENT_SECRET:latest \
    --max-retries=1 \
    --task-timeout=15m \
    --memory=512Mi \
    --cpu=1

# Execute on-demand sync run
gcloud run jobs execute spotify-v2-pipeline-job --region=europe-west2
```

### Job 4: `spotify-v2-enrichment-job` (Active V2 On-Demand Archive Enrichment)
Extracts Wikipedia narratives, Pitchfork reviews, Metacritic scores, and Discogs personnel into universal shared table `spotify_v2.album_enriched_metadata`:
```bash
# Deploy V2 Enrichment Job
gcloud run jobs deploy spotify-v2-enrichment-job \
    --image=europe-west2-docker.pkg.dev/secret-compass-181513/spotify-repo/spotify-v2-pipeline:latest \
    --command="python" \
    --args="enrich.py,50" \
    --region=europe-west2 \
    --service-account=spotify-data@secret-compass-181513.iam.gserviceaccount.com \
    --set-env-vars=GCP_PROJECT=secret-compass-181513,BQ_DATASET=spotify_v2 \
    --max-retries=0 \
    --task-timeout=30m \
    --memory=512Mi \
    --cpu=1

# Execute on-demand batch run (e.g. 50 or 100 albums)
gcloud run jobs execute spotify-v2-enrichment-job --region=europe-west2 --args="enrich.py,100"

# Run locally via virtualenv
python src/pipeline_v2/enrich.py --batch-size 50
```

---

## 8. Cloud Scheduler (Automation)

### Scheduler 1: `spotify-daily-sync` (V1 Single-User - PAUSED)
Legacy single-user scheduler. Paused during Phase 6 cutover:
```bash
# Pause legacy scheduler
gcloud scheduler jobs pause spotify-daily-sync --location=europe-west2

# Resume legacy scheduler (disaster recovery rollback only)
gcloud scheduler jobs resume spotify-daily-sync --location=europe-west2
```

### Scheduler 2: `spotify-v2-sync-scheduler` (Active V2 Multi-Tenant Scheduler)
Triggers the multi-tenant pipeline every 2 hours for all approved users:
```bash
gcloud scheduler jobs create http spotify-v2-sync-scheduler \
    --location=europe-west2 \
    --schedule="0 */2 * * *" \
    --time-zone="UTC" \
    --uri="https://europe-west2-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/secret-compass-181513/jobs/spotify-v2-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="spotify-data@secret-compass-181513.iam.gserviceaccount.com" \
    --description="Automated 2-hour multi-tenant sync for all approved SpinSleeve friends"
```

### Scheduler 3: `spotify-v2-enrichment-scheduler` (Active Daily V2 Enrichment Scheduler)
Triggers daily 12" gatefold archival metadata enrichment (Wikipedia narratives, Pitchfork reviews, Discogs personnel) at 04:00 UTC:
```bash
gcloud scheduler jobs create http spotify-v2-enrichment-scheduler \
    --location=europe-west2 \
    --schedule="0 4 * * *" \
    --time-zone="UTC" \
    --uri="https://europe-west2-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/secret-compass-181513/jobs/spotify-v2-enrichment-job:run" \
    --http-method=POST \
    --oauth-service-account-email="spotify-data@secret-compass-181513.iam.gserviceaccount.com" \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" \
    --description="Daily automated 12-inch gatefold archival metadata enrichment for SpinSleeve"
```

---

## 9. Custom Domain & Firebase Reverse Proxy (`spinsleeve.cc`)

Cloud Run in `europe-west2` does not support legacy GCP domain mappings. Domain routing and zero-cost SSL certificates are managed via **Google Firebase Hosting**.

### Namecheap DNS Settings
* **Type A (`@`):** `199.36.158.100`
* **Type CNAME (`www`):** `spinsleeve.cc.`

### Firebase Configuration (`firebase.json`)
All production routes (`**`) are routed directly to the multi-tenant V2 application on Cloud Run:
```json
{
  "hosting": {
    "public": "public",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "run": {
          "serviceId": "spotify-dashboard-beta",
          "region": "europe-west2"
        }
      }
    ]
  }
}
```

### Deploying Routing Updates
```bash
firebase deploy --only hosting
```

---

## 10. Multi-Tenant User & Invite Management CLI

A standalone CLI is located at the project root for managing beta users directly in Datastore:

```bash
# List all registered and pending friends
GOOGLE_APPLICATION_CREDENTIALS=~/Projects/spotify/cpb100-267aa5b92aa7.json \
  ./.venv/bin/python manage_users.py list

# Approve a friend
GOOGLE_APPLICATION_CREDENTIALS=~/Projects/spotify/cpb100-267aa5b92aa7.json \
  ./.venv/bin/python manage_users.py approve <spotify_id> --name="Alice"

# Approve an admin
GOOGLE_APPLICATION_CREDENTIALS=~/Projects/spotify/cpb100-267aa5b92aa7.json \
  ./.venv/bin/python manage_users.py approve sergebou --name="Serge" --role admin

# Revoke access
GOOGLE_APPLICATION_CREDENTIALS=~/Projects/spotify/cpb100-267aa5b92aa7.json \
  ./.venv/bin/python manage_users.py revoke <spotify_id>
```
