# SpinSleeve Technical Specification: APP-18 — Zero-Shot Semantic Text Classification

## 1. Overview & Objective
Replace brittle, hand-tuned regex rules (`MACRO_GENRE_RULES`) in `src/pipeline_v2/classifier.py` with **Zero-Shot Semantic Text Classification** using lightweight sentence embeddings (e.g., `sentence-transformers` / `all-MiniLM-L6-v2`) or semantic vector similarity against canonical macro-genre anchor descriptions. This eliminates overfitting to early developer collections and generalizes robustly to any micro-genre or obscure tag.

---

## 2. Architecture & Data Flow

1. **Canonical Macro-Genre Anchors:**
   Define rich semantic descriptions for each macro-genre:
   - **Electronic:** *"Electronic music, IDM, techno, house, ambient electronica, club beats, and synthesized production."*
   - **Rock:** *"Rock music, indie rock, psychedelic rock, progressive rock, shoegaze, classic rock, and guitar-driven albums."*
   - **Pop:** *"Pop music, indie pop, synth-pop, dance-pop, chamber pop, and melodic vocal-driven albums."*
   - **Hip-Hop:** *"Hip-hop, rap, trap, boom bap, drill, and rhythm-driven urban poetry."*
   - **Jazz:** *"Jazz music, bebop, modal jazz, free jazz, fusion, and brass improvisation."*
   - **Classical:** *"Classical music, orchestral works, chamber music, symphony, opera, and baroque compositions."*
   - **Folk / Country:** *"Folk, country, bluegrass, americana, singer-songwriter acoustic storytelling."*
   - **R&B / Soul:** *"R&B, soul, funk, motown, neo-soul, and groove-oriented vocal performance."*
   - **Ambient:** *"Ambient soundscapes, drone recordings, serene minimal textures, and field recordings."*
   - **Punk / Alternative:** *"Punk rock, post-punk, hardcore, grunge, emo, and counterculture alternative music."*
   - **Reggae / Dub:** *_Reggae, dub, roots, ska, and dancehall rhythms."*
   - **Blues:** *"Blues, delta blues, chicago blues, and electric blues."*
   - **Latin / World:** *"Latin, bossa nova, afrobeat, flamenco, samba, and world music traditions."*

2. **Embedding & Scoring Engine:**
   - On enrichment (`enrich.py` / `classifier.py`), serialize album metadata corpus into a single string.
   - Compute embedding vector via lightweight local inference model (`sentence-transformers/all-MiniLM-L6-v2`).
   - Compute cosine similarity against pre-computed macro-genre anchor vectors.
   - Assign the highest-scoring macro-genre (with a confidence threshold; fallback to `Other / Unclassified` if similarity < threshold).

---

## 3. Implementation Plan & Migration
- **Dependencies:** Add `sentence-transformers` and `torch` (or quantized ONNX runtime for Cloud Run Jobs efficiency) to `src/pipeline_v2/requirements.txt`.
- **Backward Compatibility:** Maintain API contract `classify_macro_genre(genres_str, styles_str, mb_tags)` so downstream BigQuery DML and Flask routes require zero structural alterations.
- **Testing:** Expand `tests/test_app16_classification.py` to validate semantic zero-shot classification across ambiguous and compound genres.
