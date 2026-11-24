"""
SpinSleeve Classifier Comparison Script (`scripts/profile_classifier_comparison.py`)
----------------------------------------------------------------------------------
Runs side-by-side macro-genre profiling between the legacy deterministic Regex engine
and the new APP-18 Zero-Shot Semantic Embeddings classifier (all-MiniLM-L6-v2).
Computes exact cosine similarity scores (confidence levels) to assist with threshold tuning.
Materializes the results to `classifier_comparison_report.md`.
"""

import os
import sys
import argparse
import re
import pandas as pd

# Add src and report_v2 to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "report_v2")))

from app_config import PROJECT_ID, DATASET_V2
from pipeline_v2.classifier import MACRO_GENRE_RULES, MACRO_GENRE_ANCHORS, _get_embedding_model

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def regex_classify(genres: str) -> str:
    """Classifies genre corpus using legacy regex rules only."""
    corpus = str(genres or "").lower()
    if not corpus.strip():
        return "Other / Unclassified"
    for macro, patterns in MACRO_GENRE_RULES:
        for pat in patterns:
            if re.search(pat, corpus):
                return macro
    return "Other / Unclassified"


def semantic_classify_with_confidence(genres: str, threshold: float = 0.35):
    """
    Computes zero-shot semantic prediction and returns (macro_genre, confidence_score).
    Falls back to regex if confidence < threshold or model unavailable.
    """
    corpus = str(genres or "").lower()
    if not corpus.strip():
        return "Other / Unclassified", 0.0

    model, anchor_embeddings = _get_embedding_model()
    if not model or model is False or anchor_embeddings is None:
        reg = regex_classify(genres)
        return reg, 0.0

    try:
        from sentence_transformers import util
        corpus_emb = model.encode(corpus, convert_to_tensor=True)
        cos_scores = util.cos_sim(corpus_emb, anchor_embeddings)[0]
        best_idx = int(cos_scores.argmax())
        best_score = float(cos_scores[best_idx])
        macro_names = list(MACRO_GENRE_ANCHORS.keys())
        predicted_macro = macro_names[best_idx]

        if best_score >= threshold:
            return predicted_macro, round(best_score, 3)
        else:
            # Fallback to regex
            reg = regex_classify(genres)
            return reg, round(best_score, 3)
    except Exception:
        reg = regex_classify(genres)
        return reg, 0.0


def run_comparison(user_id: str, probe_string: str = None):
    """Runs catalog-wide comparison with confidence scoring and materializes report."""
    if probe_string:
        print(f"\n============================================================")
        print(f" PROBING CUSTOM GENRE CORPUS: '{probe_string}'")
        print(f"============================================================")
        reg_res = regex_classify(probe_string)
        sem_res, conf = semantic_classify_with_confidence(probe_string)
        print(f"  • Regex Classification   : {reg_res}")
        print(f"  • Semantic Classification: {sem_res} (Confidence: {conf})")
        return

    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT_ID)

        report_lines = []
        def log(msg=""):
            print(msg)
            report_lines.append(msg)

        log(f"# SpinSleeve Classifier Comparison & Confidence Report (Regex vs. Semantic)")
        log(f"\n**Generated for User ID:** `{user_id}` | **GCP Project:** `{PROJECT_ID}`\n")
        log(f"---")

        query = f"""
        SELECT album_id, album_name, album_artist_name, album_genres 
        FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table` 
        WHERE user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        )
        df = client.query(query, job_config=job_config).to_dataframe()

        if df.empty:
            log(f"No saved albums found for user '{user_id}'.")
            return

        log(f"\n📁 **Total Saved Library Albums Analyzed:** {len(df)}\n")

        # Compute classifications
        df["regex_mg"] = df["album_genres"].apply(regex_classify)
        
        sem_results = df["album_genres"].apply(semantic_classify_with_confidence)
        df["semantic_mg"] = [r[0] for r in sem_results]
        df["confidence"] = [r[1] for r in sem_results]

        # 1. Aggregated Comparison Table
        log(f"\n## 1. Aggregated Macro-Genre Distribution Comparison")
        reg_counts = df["regex_mg"].value_counts()
        sem_counts = df["semantic_mg"].value_counts()
        
        comp_df = pd.DataFrame({
            "Regex (Legacy Count)": reg_counts,
            "Semantic (Zero-Shot Count)": sem_counts
        }).fillna(0).astype(int)
        
        comp_df["Regex %"] = (comp_df["Regex (Legacy Count)"] / len(df) * 100).round(1)
        comp_df["Semantic %"] = (comp_df["Semantic (Zero-Shot Count)"] / len(df) * 100).round(1)
        comp_df = comp_df[["Regex (Legacy Count)", "Regex %", "Semantic (Zero-Shot Count)", "Semantic %"]]

        log("\n```markdown")
        log(comp_df.to_string())
        log("```\n")

        # 2. Confidence Threshold Analysis
        log(f"\n## 2. Semantic Confidence & Threshold Analysis")
        log("Breakdown of semantic similarity confidence scores (cosine distance against macro-genre anchors):")
        
        c_high = len(df[df["confidence"] >= 0.50])
        c_mid = len(df[(df["confidence"] >= 0.40) & (df["confidence"] < 0.50)])
        c_low = len(df[(df["confidence"] >= 0.35) & (df["confidence"] < 0.40)])
        c_fallback = len(df[df["confidence"] < 0.35])

        log(f"- **High Confidence ($\\ge 0.50$):** {c_high} albums ({(c_high/len(df)*100):.1f}%)")
        log(f"- **Moderate Confidence ($0.40 - 0.49$):** {c_mid} albums ({(c_mid/len(df)*100):.1f}%)")
        log(f"- **Borderline Confidence ($0.35 - 0.39$):** {c_low} albums ({(c_low/len(df)*100):.1f}%)")
        log(f"- **Fallback Triggered ($< 0.35$):** {c_fallback} albums ({(c_fallback/len(df)*100):.1f}%)\n")

        # 3. Divergence Analysis
        diffs = df[df["regex_mg"] != df["semantic_mg"]]
        log(f"\n## 3. Divergence & Discrepancy Highlights")
        log(f"Total divergences detected between Regex and Semantic: **{len(diffs)}** out of {len(df)} albums.\n")

        if not diffs.empty:
            log("| Album Name | Artist | Genres Corpus | Regex | Semantic | Confidence |")
            log("| :--- | :--- | :--- | :--- | :--- | :---: |")
            for _, r in diffs.iterrows():
                log(f"| {r['album_name']} | {r['album_artist_name']} | `{r['album_genres']}` | **{r['regex_mg']}** | **{r['semantic_mg']}** | `{r['confidence']}` |")
        else:
            log("✨ Both classification engines produced identical macro-genres across all catalog records.")

        # 4. Full Album Report Classification Ledger
        log(f"\n## 4. Full Catalog Classification Ledger")
        log(f"Complete itemized classification record with confidence scores for all {len(df)} albums:\n")
        log("| # | Album Name | Artist | Genres Corpus | Assigned Macro-Genre | Confidence |")
        log("| :---: | :--- | :--- | :--- | :--- | :---: |")
        for idx, r in df.reset_index(drop=True).iterrows():
            log(f"| {idx+1} | {r['album_name']} | {r['album_artist_name']} | `{r['album_genres']}` | **{r['semantic_mg']}** | `{r['confidence']}` |")

        # Write markdown report file
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "classifier_comparison_report.md"))
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        print(f"\n📄 Comprehensive comparison & confidence report successfully materialized to: {report_path}")

    except Exception as e:
        print(f"Error running comparison: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare Regex vs. Semantic Classification & Confidence Analysis.")
    parser.add_argument("--user", default="sergebou", help="User ID to profile (default: sergebou)")
    parser.add_argument("--probe", default=None, help="Probe a specific custom genre string instead of full catalog")
    args = parser.parse_args()
    run_comparison(user_id=args.user, probe_string=args.probe)
