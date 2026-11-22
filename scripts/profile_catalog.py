"""
SpinSleeve Catalog Data Profiling Script (`scripts/profile_catalog.py`)
---------------------------------------------------------------------
Computes full distribution counts and intersection matrices across all filter options
(Macro-Genres, Eras, Vibes, Play Status, and Unowned Crate coverage) to highlight
unbalance, zero-count gaps, and metadata coverage.
Outputs results to terminal stdout and writes `catalog_profile_report.md`.
"""
import os
import sys
import argparse
import pandas as pd
from collections import Counter, defaultdict

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "report_v2")))

from app_config import PROJECT_ID, DATASET_V2
from pipeline_v2.classifier import classify_macro_genre, extract_derived_moods

VIBES = {
    "chill": ['ambient', 'chill', 'downtempo', 'lo-fi', 'dream pop', 'slowcore', 'shoegaze', 'trip hop', 'ethereal', 'ambient pop', 'minimalism', 'idm', 'post-rock', 'bedroom pop', 'chillwave', 'drone'],
    "energetic": ['punk', 'hard rock', 'garage rock', 'alternative rock', 'grunge', 'noise rock', 'post-punk', 'electronic', 'dance', 'techno', 'house', 'hip hop', 'rap', 'club', 'breakbeat', 'big beat', 'drum and bass', 'edm', 'synthpop', 'indietronica'],
    "mellow": ['folk', 'acoustic', 'singer-songwriter', 'indie folk', 'chamber pop', 'chamber folk', 'jazz', 'bossa nova', 'quiet storm', 'americana', 'bluegrass', 'soft rock', 'chanson', 'soul'],
    "vintage": ['classic rock', 'psychedelic rock', 'blues', 'motown', 'classic soul', 'brill building', 'roots rock', 'funk', 'hard bop', 'soul jazz', 'traditional pop', 'rockabilly', 'doo-wop', 'vintage']
}

def profile_user_catalog(user_id: str):
    """Profiles catalog distribution and intersection matrices for a given user."""
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT_ID)

        report_lines = []
        def log(msg=""):
            print(msg)
            report_lines.append(msg)

        log(f"\n============================================================")
        log(f" SPINSLEEVE CATALOG DATA PROFILE & DISTRIBUTION MATRIX")
        log(f" User ID: {user_id} | GCP Project: {PROJECT_ID}")
        log(f"============================================================\n")

        # 1. Fetch Saved Albums Features
        saved_query = f"""
        SELECT 
            album_id, album_name, album_artist_name, release_year, added_at,
            album_genres, album_track_plays, album_track_plays_30d,
            macro_genre, derived_moods, enrichment_quality_score
        FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table`
        WHERE user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        )
        df_saved = client.query(saved_query, job_config=job_config).to_dataframe()

        log(f"📁 Total Saved Library Albums: {len(df_saved)}")
        if df_saved.empty:
            log("No saved albums found for user.")
            return

        # Categorize Era
        def get_era(year_str):
            try:
                y = int(str(year_str)[:4])
            except Exception:
                y = 0
            if y == 0:
                return "Unknown"
            if y < 2000:
                return "Classic (<2000)"
            elif y < 2018:
                return "Modern (00s-10s)"
            else:
                return "Recent (2018+)"

        df_saved['era'] = df_saved['release_year'].apply(get_era)

        # Categorize Vibe safely handling array/list types without pandas ambiguity errors
        def get_vibe(genres_str, moods_list):
            m_list = []
            if moods_list is not None:
                try:
                    if hasattr(moods_list, "tolist"):
                        m_list = moods_list.tolist()
                    elif isinstance(moods_list, (list, tuple)):
                        m_list = list(moods_list)
                    elif isinstance(moods_list, str):
                        m_list = [m.strip() for m in moods_list.split(",") if m.strip()]
                except Exception:
                    m_list = []

            moods_str = " ".join(str(m) for m in m_list if m is not None)
            corpus = f"{str(genres_str or '')} {moods_str}".lower()
            assigned = []
            for vibe, keywords in VIBES.items():
                if any(kw in corpus for kw in keywords):
                    assigned.append(vibe.title())
            return assigned if assigned else ["Eclectic / Other"]

        df_saved['vibes_list'] = df_saved.apply(
            lambda r: get_vibe(r.get('album_genres'), r.get('derived_moods')), axis=1
        )

        # 2. Macro-Genre Distribution
        log("\n### 1. Macro-Genre Distribution")
        mg_counts = df_saved['macro_genre'].value_counts()
        for mg, count in mg_counts.items():
            pct = (count / len(df_saved)) * 100
            bar = "█" * int(pct / 3) if pct > 0 else ""
            log(f"  {str(mg).ljust(22)} : {str(count).rjust(3)} ({pct:5.1f}%) {bar}")

        # 3. Era Distribution
        log("\n### 2. Era Distribution")
        era_counts = df_saved['era'].value_counts()
        for era, count in era_counts.items():
            pct = (count / len(df_saved)) * 100
            bar = "█" * int(pct / 4) if pct > 0 else ""
            log(f"  {str(era).ljust(18)} : {str(count).rjust(3)} ({pct:5.1f}%) {bar}")

        # 4. Play Status / Horizon Distribution
        log("\n### 3. Play Status Distribution")
        def get_status(row):
            p30 = row.get('album_track_plays_30d', 0)
            if pd.isna(p30): p30 = 0
            else: p30 = int(p30)

            tot = row.get('album_track_plays', 0)
            if pd.isna(tot): tot = 0
            else: tot = int(tot)

            if tot == 0:
                return "Unplayed Gems"
            elif p30 > 0:
                return "Heavy Rotation (30D)"
            else:
                return "Cold Shelf"

        df_saved['status'] = df_saved.apply(get_status, axis=1)
        status_counts = df_saved['status'].value_counts()
        for st, count in status_counts.items():
            pct = (count / len(df_saved)) * 100
            bar = "█" * int(pct / 4) if pct > 0 else ""
            log(f"  {str(st).ljust(22)} : {str(count).rjust(3)} ({pct:5.1f}%) {bar}")

        # 5. Macro-Genre x Era Matrix
        log("\n### 4. Matrix: Macro-Genre x Era")
        matrix_mg_era = pd.crosstab(df_saved['macro_genre'], df_saved['era'], margins=True)
        log("```")
        log(matrix_mg_era.to_string())
        log("```")

        # 6. Macro-Genre x Play Status Matrix
        log("\n### 5. Matrix: Macro-Genre x Play Status")
        matrix_mg_status = pd.crosstab(df_saved['macro_genre'], df_saved['status'], margins=True)
        log("```")
        log(matrix_mg_status.to_string())
        log("```")

        # 7. Coverage Gaps & Imbalances Highlight
        log("\n### 6. Coverage Gaps & Imbalances Highlight")
        gaps_found = False
        for mg in mg_counts.index:
            subset = df_saved[df_saved['macro_genre'] == mg]
            unplayed_count = len(subset[subset['status'] == 'Unplayed Gems'])
            if unplayed_count == 0 and len(subset) >= 5:
                log(f"  ⚠️  Gap Alert: '{mg}' has {len(subset)} albums but 0 Unplayed Gems (100% explored).")
                gaps_found = True

        if not gaps_found:
            log("  ✨ No major structural coverage gaps detected across active categories.")

        log("\n============================================================")
        log(" PROFILING COMPLETE")
        log("============================================================\n")

        # Write markdown report
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "catalog_profile_report.md"))
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# SpinSleeve Catalog Profile Report\n\n")
            f.write(f"Generated for user: **{user_id}**\n\n")
            f.write("\n".join(report_lines))
        print(f"\n📄 Profiling report successfully written to: {report_path}")

    except Exception as e:
        print(f"Error profiling catalog: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile SpinSleeve catalog distribution and matrices.")
    parser.add_argument("--user", default="sergebou", help="User ID to profile (default: sergebou)")
    args = parser.parse_args()
    profile_user_catalog(args.user)
