"""
SpinSleeve APP-16 Semantic Liner-Note & Metadata Classifier.

Provides deterministic NLP and rule-based atmospheric classification:
- Macro-genre categorization from Spotify, Discogs, and MusicBrainz genres.
- Derived moods extraction from liner notes, reviews, and critical summaries.
- Descriptive stylistic tags extraction (instrumentation, production style).
- Enrichment quality scoring (0.0 to 1.0 completeness metric).
"""

import re
from typing import Dict, List, Optional, Any

# Standard Macro Genre Categories
MACRO_GENRE_RULES = [
    ("Ambient", [
        r"\bambient\b", r"\bdrone\b", r"\bsoundscape\b", r"\bfield recordings?\b", r"\bnew age\b",
        r"\bdark ambient\b", r"\bspace ambient\b"
    ]),
    ("Metal", [
        r"\bmetal\b", r"\bthrash\b", r"\bdoom metal\b", r"\bblack metal\b", r"\bdeath metal\b",
        r"\bgrindcore\b", r"\bheavy metal\b", r"\bsludge metal\b", r"\bstoner metal\b"
    ]),
    ("Punk / Alternative", [
        r"\bpunk\b", r"\bpost-punk\b", r"\bhardcore punk\b", r"\bgrunge\b", r"\bemo\b",
        r"\briot grrrl\b", r"\bgarage punk\b", r"\bnoise rock\b", r"\bmath rock\b",
        r"\bpost-hardcore\b", r"\balternative rock\b", r"\balt-rock\b"
    ]),
    ("Electronic", [
        r"\belectronic\b", r"\bedm\b", r"\bclub\b", r"\btechno\b", r"\bhouse\b", r"\belectro\b",
        r"\bidm\b", r"\bdrum and bass\b", r"\bdnb\b", r"\btrance\b", r"\bdowntempo\b",
        r"\btrip hop\b", r"\bsynth-?pop\b", r"\belectronica\b", r"\buk bass\b", r"\buk garage\b",
        r"\bgarage\b", r"\bbass\b", r"\bbreaks?\b", r"\bbreakbeat\b", r"\bhyperpop\b",
        r"\bglitch\b", r"\bchillwave\b", r"\belectroclash\b", r"\bsynthwave\b", r"\bvaporwave\b",
        r"\bambient techno\b", r"\bminimal techno\b", r"\bdeep house\b", r"\belectronic music\b",
        r"\bnu-disco\b"
    ]),
    ("Hip-Hop", [
        r"\bhip[ -]?hop\b", r"\brap\b", r"\btrap\b", r"\bboom bap\b", r"\bdrill\b",
        r"\bconscious rap\b", r"\bcloud rap\b", r"\beast coast hip hop\b", r"\bwest coast hip hop\b"
    ]),
    ("Jazz", [
        r"\bjazz\b", r"\bbebop\b", r"\bhard bop\b", r"\bmodal jazz\b", r"\bfusion\b",
        r"\bfree jazz\b", r"\bbig band\b", r"\bcool jazz\b", r"\bspiritual jazz\b",
        r"\bnu jazz\b", r"\bjazz funk\b", r"\bambient jazz\b", r"\bjazz fusion\b",
        r"\blounge\b", r"\bexotica\b", r"\beasy listening\b"
    ]),
    ("R&B / Soul", [
        r"\br&b\b", r"\bsoul\b", r"\bfunk\b", r"\bmotown\b", r"\bneo[ -]soul\b",
        r"\bcontemporary r&b\b", r"\bgospel\b", r"\bdisco\b", r"\bquiet storm\b",
        r"\bboogie\b", r"\bdoo-wop\b"
    ]),
    ("Classical", [
        r"\bclassical\b", r"\bchamber music\b", r"\bsymphon(?:y|ic)\b", r"\bchoral\b",
        r"\bopera\b", r"\bmodern classical\b", r"\bneo[- ]?classical\b", r"\bminimalis(?:t|m)\b",
        r"\bcontemporary classical\b", r"\bpost-classical\b", r"\bconcerto\b", r"\bsonata\b",
        r"\bstring quartet\b", r"\bpiano solo\b", r"\bbaroque\b"
    ]),
    ("Folk / Country", [
        r"\bfolk\b", r"\bcountry\b", r"\bbluegrass\b", r"\bamericana\b", r"\bappalachian\b",
        r"\bsinger-songwriter\b", r"\balt-country\b", r"\bindie folk\b", r"\bfreak folk\b",
        r"\btraditional folk\b", r"\bcontemporary folk\b"
    ]),
    ("Reggae / Dub", [
        r"\breggae\b", r"\bdub\b", r"\bska\b", r"\broots reggae\b", r"\bdancehall\b",
        r"\brocker\b", r"\brocksteady\b"
    ]),
    ("Blues", [
        r"\bblues\b", r"\bdelta blues\b", r"\bchicago blues\b", r"\belectric blues\b",
        r"\bacoustic blues\b"
    ]),
    ("Rock", [
        r"\brock\b", r"\bindie rock\b", r"\bpsychedelic rock\b", r"\bprog(?:ressive)? rock\b",
        r"\bshoegaze\b", r"\bclassic rock\b", r"\bart rock\b", r"\bhard rock\b",
        r"\bslowcore\b", r"\bpsychedelic\b", r"\bneo-psychedelic\b", r"\bkrautrock\b",
        r"\bpost-rock\b", r"\bgarage rock\b", r"\bspace rock\b", r"\bglam rock\b"
    ]),
    ("Pop", [
        r"\bpop\b", r"\bindie pop\b", r"\bdance-pop\b", r"\bchamber pop\b", r"\bbaroque pop\b",
        r"\bpower pop\b", r"\bbritpop\b", r"\bart pop\b", r"\bchanson\b", r"\byé-yé\b",
        r"\belectropop\b", r"\bdream pop\b"
    ]),
    ("Latin / World", [
        r"\blatin\b", r"\bbossa[- ]?nova\b", r"\bbossanova\b", r"\btango\b", r"\bsamba\b",
        r"\bafrobeat\b", r"\bcumbia\b", r"\bflamenco\b", r"\bworld\b", r"\bbikutsi\b",
        r"\bhighlife\b", r"\bshibuya-kei\b", r"\bmpb\b", r"\btropi[c|k]alia\b", r"\btropicália\b",
        r"\bcalypso\b", r"\bsalsa\b", r"\bandean\b"
    ]),
]

# Standard Mood Taxonomies and Keyword Dictionaries
MOOD_LEXICON = {
    "Late Night": [
        r"\blate night\b", r"\bmidnight\b", r"\bnocturnal\b", r"\binsomnia\b", r"\b3\s*am\b",
        r"\bafter hours\b", r"\bvelvet\b", r"\bdimly lit\b", r"\bnoir\b", r"\bsmoky\b", r"\bdark room\b"
    ],
    "Chill": [
        r"\bchill\b", r"\blaid[- ]back\b", r"\brelax(?:ed|ing)\b", r"\bsooth(?:ing|e)\b",
        r"\bpeaceful\b", r"\bserene\b", r"\btranquil\b", r"\bcalm\b", r"\beasygoing\b", r"\bunwind\b"
    ],
    "Energetic": [
        r"\benergetic\b", r"\baggressive\b", r"\bdriving\b", r"\bpounding\b", r"\buptempo\b",
        r"\bhigh[- ]energy\b", r"\bexplosive\b", r"\bfrenzy\b", r"\bdanceable\b", r"\bfrenetic\b", r"\bhard-hitting\b"
    ],
    "Mellow": [
        r"\bmellow\b", r"\bsoft\b", r"\bsubtle\b", r"\bunderstated\b", r"\bgentle\b",
        r"\bdelicate\b", r"\bbreezy\b", r"\btender\b", r"\bquiet\b", r"\bmuted\b"
    ],
    "Vintage": [
        r"\bvintage\b", r"\bnostalgic\b", r"\bretro\b", r"\banalog\b", r"\bclassic\b",
        r"\bvinyl\b", r"\btape\b", r"\bdusty\b", r"\bhistoric\b", r"\bold-school\b", r"\b70s\b", r"\b60s\b", r"\b80s\b"
    ],
    "Melancholic": [
        r"\bmelanchol(?:y|ic)\b", r"\bsad(?:ness)?\b", r"\bsorrow\b", r"\bgrief\b", r"\bheartbreak\b",
        r"\bsomb(?:er|re)\b", r"\bmourn(?:ing|ful)\b", r"\bbittersweet\b", r"\bweeping\b", r"\bdespair\b", r"\btearful\b"
    ],
    "Uplifting": [
        r"\buplifting\b", r"\bjoyful\b", r"\beuphor(?:ia|ic)\b", r"\btriumphant\b", r"\bbright\b",
        r"\bhopeful\b", r"\bcelebrat(?:ory|ion)\b", r"\bblissful\b", r"\bcheerful\b", r"\bradiant\b", r"\binspirational\b"
    ],
    "Atmospheric": [
        r"\batmospheric\b", r"\bethereal\b", r"\bspacious\b", r"\breverb\b", r"\bexpansive\b",
        r"\bcinematic\b", r"\bdreamlike\b", r"\bdreamy\b", r"\bsprawling\b", r"\bsoundscape\b", r"\bhypnotic\b", r"\bimmersive\b"
    ],
    "Gritty": [
        r"\bgritty\b", r"\braw\b", r"\babrasive\b", r"\bdistort(?:ed|ion)\b", r"\bdirty\b",
        r"\blo-?fi\b", r"\bharsh\b", r"\bfuzzy\b", r"\bjagged\b", r"\bvisceral\b", r"\bgrimy\b"
    ],
    "Psychedelic": [
        r"\bpsychedelic\b", r"\btrippy\b", r"\bhallucinatory\b", r"\bkaleidoscop(?:e|ic)\b",
        r"\bwarped\b", r"\bacid\b", r"\bspacey\b", r"\bmind-bending\b", r"\bsurreal\b", r"\bdisorienting\b"
    ],
    "Introspective": [
        r"\bintrospective\b", r"\bcontemplative\b", r"\bconfessional\b", r"\bphilosophical\b",
        r"\bbrooding\b", r"\breflective\b", r"\bmeditative\b", r"\bsoul-searching\b", r"\bpersonal\b", r"\bintimate\b"
    ]
}

# Stylistic and Production Markers
TAG_LEXICON = {
    "Synthesizers": [r"\bsynthesizers?\b", r"\bsynths?\b", r"\bmoog\b", r"\bmodular synth\b", r"\barpeggiator\b", r"\banalog synth\b"],
    "Acoustic Guitar": [r"\bacoustic guitars?\b", r"\bfingerpicking\b", r"\bunplugged\b", r"\b12-string\b"],
    "Concept Album": [r"\bconcept album\b", r"\brock opera\b", r"\bnarrative arc\b", r"\bthematic\b"],
    "Lo-Fi Production": [r"\blo-?fi\b", r"\bcassette\b", r"\bfour-track\b", r"\bbedroom pop\b", r"\btape hiss\b", r"\bhome-recorded\b"],
    "Orchestral Strings": [r"\borchestr(?:a|al)\b", r"\bstring quartet\b", r"\bviolins?\b", r"\bcellos?\b", r"\bsymphony\b", r"\bchamber strings\b"],
    "Fuzz & Distortion": [r"\bfuzz\b", r"\bdistortion\b", r"\bfeedback\b", r"\boverdrive\b", r"\bwall of sound\b"],
    "Minimalist": [r"\bminimalis(?:t|m)\b", r"\bsparse\b", r"\bstripped-down\b", r"\bbare\b", r"\brestrained\b"],
    "Heavy Basslines": [r"\bsub-?bass\b", r"\b808\b", r"\bheavy bass\b", r"\bbasslines?\b", r"\bdub bass\b", r"\bgroove-driven\b"],
    "Field Recordings": [r"\bfield recordings?\b", r"\bambient noise\b", r"\btape loops?\b", r"\bfound sounds?\b"],
    "Live Energy": [r"\brecorded live\b", r"\blive session\b", r"\bjam session\b", r"\bimprovisation\b", r"\blive recording\b"],
    "Brass & Horns": [r"\bhorns?\b", r"\bbrass section\b", r"\btrumpets?\b", r"\bsaxophone\b", r"\btrombones?\b"]
}


# Canonical Macro-Genre Anchor Descriptions for APP-18 Zero-Shot Semantic Classification
MACRO_GENRE_ANCHORS = {
    "Ambient": "Ambient music, drone recordings, serene minimal textures, and field recordings.",
    "Metal": "Metal music, thrash, doom metal, black metal, death metal, grindcore, and heavy metal.",
    "Punk / Alternative": "Punk rock, post-punk, hardcore, grunge, emo, and counterculture alternative music.",
    "Electronic": "Electronic music, IDM, techno, house, ambient electronica, club beats, and synthesized production.",
    "Hip-Hop": "Hip-hop, rap, trap, boom bap, drill, and rhythm-driven urban poetry.",
    "Jazz": "Jazz music, bebop, modal jazz, free jazz, fusion, and brass improvisation.",
    "R&B / Soul": "R&B, soul, funk, motown, neo-soul, and groove-oriented vocal performance.",
    "Classical": "Classical music, orchestral works, chamber music, symphony, opera, and baroque compositions.",
    "Folk / Country": "Folk, country, bluegrass, americana, singer-songwriter acoustic storytelling.",
    "Reggae / Dub": "Reggae, dub, roots, ska, and dancehall rhythms.",
    "Blues": "Blues, delta blues, chicago blues, and electric blues.",
    "Rock": "Rock music, indie rock, psychedelic rock, progressive rock, shoegaze, classic rock, and guitar-driven albums.",
    "Pop": "Pop music, indie pop, synth-pop, dance-pop, chamber pop, and melodic vocal-driven albums.",
    "Latin / World": "Latin, bossa nova, afrobeat, flamenco, samba, and world music traditions."
}

_EMBEDDING_MODEL = None
_ANCHOR_EMBEDDINGS = None


def _get_embedding_model():
    global _EMBEDDING_MODEL, _ANCHOR_EMBEDDINGS
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            anchor_texts = list(MACRO_GENRE_ANCHORS.values())
            _ANCHOR_EMBEDDINGS = _EMBEDDING_MODEL.encode(anchor_texts, convert_to_tensor=True)
        except Exception:
            _EMBEDDING_MODEL = False
    return _EMBEDDING_MODEL, _ANCHOR_EMBEDDINGS


def classify_macro_genre_semantic(corpus: str, threshold: float = 0.35) -> Optional[str]:
    """
    Classifies genre corpus using zero-shot semantic similarity against macro-genre anchors.
    """
    model, anchor_embeddings = _get_embedding_model()
    if not model or model is False or anchor_embeddings is None:
        return None
    try:
        from sentence_transformers import util
        corpus_emb = model.encode(corpus, convert_to_tensor=True)
        cos_scores = util.cos_sim(corpus_emb, anchor_embeddings)[0]
        best_idx = int(cos_scores.argmax())
        best_score = float(cos_scores[best_idx])
        if best_score >= threshold:
            macro_names = list(MACRO_GENRE_ANCHORS.keys())
            return macro_names[best_idx]
    except Exception:
        pass
    return None


def _tally_macro_genre_votes(corpus: str) -> Dict[str, int]:
    """
    Counts total regex keyword occurrences across all macro-genre pattern sets.
    """
    votes: Dict[str, int] = {}
    for macro, patterns in MACRO_GENRE_RULES:
        count = 0
        for pat in patterns:
            matches = re.findall(pat, corpus)
            count += len(matches)
        if count > 0:
            votes[macro] = count
    return votes


def _pick_dominant_macro_genre(votes: Dict[str, int]) -> str:
    """
    Selects the dominant macro-genre with the highest vote count.
    Breaks ties deterministically using the canonical order in MACRO_GENRE_RULES.
    """
    priority = {macro: idx for idx, (macro, _) in enumerate(MACRO_GENRE_RULES)}
    sorted_votes = sorted(votes.items(), key=lambda kv: (-kv[1], priority.get(kv[0], 999)))
    return sorted_votes[0][0]


def classify_macro_genre(
    genres_str: Optional[str] = "",
    styles_str: Optional[str] = "",
    mb_tags: Optional[str] = "",
    description: Optional[str] = ""
) -> str:
    """
    Classifies combined genres, styles, tags, and optional narrative description into a normalized macro genre.
    Uses multi-vote dominant-frequency scoring with zero-shot semantic support and narrative fallback:
    1. Multi-vote dominant frequency on explicit tag corpus (genres + styles + MusicBrainz tags).
    2. Zero-shot semantic similarity on tag corpus.
    3. Fallback to narrative snippet (first 400 chars of album description or liner notes) via dominant voting.
    4. Zero-shot semantic similarity on narrative snippet.
    5. Returns 'Other / Unclassified' if completely inconclusive.
    """
    tag_corpus = f"{genres_str or ''} {styles_str or ''} {mb_tags or ''}".strip().lower()

    # 1. Multi-vote dominant frequency on explicit tag corpus
    if tag_corpus:
        tag_votes = _tally_macro_genre_votes(tag_corpus)
        if tag_votes:
            return _pick_dominant_macro_genre(tag_votes)

        # 2. Zero-shot semantic similarity on tag corpus
        semantic_result = classify_macro_genre_semantic(tag_corpus)
        if semantic_result:
            return semantic_result

    # 3. Fallback to narrative description snippet (first 400 chars)
    narrative_corpus = (description or "").strip().lower()[:400]
    if narrative_corpus:
        narr_votes = _tally_macro_genre_votes(narrative_corpus)
        if narr_votes:
            return _pick_dominant_macro_genre(narr_votes)

        # 4. Zero-shot semantic similarity on narrative
        semantic_narr = classify_macro_genre_semantic(narrative_corpus)
        if semantic_narr:
            return semantic_narr

    return "Other / Unclassified"


def extract_derived_moods(
    summary: Optional[str] = "",
    notes: Optional[str] = "",
    styles: Optional[str] = "",
    genres: Optional[str] = "",
    max_moods: int = 4
) -> List[str]:
    """
    Extracts high-confidence atmospheric mood tokens from album narratives and tags.
    Returns a sorted list of top mood strings (e.g. ['Atmospheric', 'Chill', 'Late Night']).
    """
    corpus = f"{summary or ''} {notes or ''} {styles or ''} {genres or ''}".lower()
    if not corpus.strip():
        return ["Chill"]

    scores: Dict[str, int] = {}
    for mood, patterns in MOOD_LEXICON.items():
        hit_count = 0
        for pat in patterns:
            matches = re.findall(pat, corpus)
            hit_count += len(matches)
        if hit_count > 0:
            scores[mood] = hit_count

    if not scores:
        return ["Chill"]

    # Sort descending by score, take top max_moods
    sorted_moods = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [m[0] for m in sorted_moods[:max_moods]]


def extract_descriptive_tags(
    summary: Optional[str] = "",
    notes: Optional[str] = "",
    styles: Optional[str] = "",
    genres: Optional[str] = "",
    max_tags: int = 4
) -> List[str]:
    """
    Extracts descriptive instrumentation and production style markers.
    Returns a list of tags (e.g. ['Synthesizers', 'Concept Album']).
    """
    corpus = f"{summary or ''} {notes or ''} {styles or ''} {genres or ''}".lower()
    if not corpus.strip():
        return []

    scores: Dict[str, int] = {}
    for tag, patterns in TAG_LEXICON.items():
        hit_count = 0
        for pat in patterns:
            matches = re.findall(pat, corpus)
            hit_count += len(matches)
        if hit_count > 0:
            scores[tag] = hit_count

    sorted_tags = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [t[0] for t in sorted_tags[:max_tags]]


def compute_enrichment_quality_score(
    has_summary: bool,
    has_review: bool,
    has_personnel: bool,
    has_community_rating: bool
) -> float:
    """
    Computes a weighted 0.0 to 1.0 completeness and fidelity score:
    - Summary present: +0.35
    - Critical reviews present: +0.25
    - Personnel/credits present: +0.25
    - Community ratings present: +0.15
    """
    score = 0.0
    if has_summary:
        score += 0.35
    if has_review:
        score += 0.25
    if has_personnel:
        score += 0.25
    if has_community_rating:
        score += 0.15
    return round(min(max(score, 0.0), 1.0), 2)


def classify_album_metadata(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates an album record and returns synthesized APP-16 classifications:
    - macro_genre (str)
    - derived_moods (List[str])
    - descriptive_tags (List[str])
    - enrichment_quality_score (float)
    """
    genres = str(record.get("genres") or "")
    styles = str(record.get("styles") or record.get("discogs_styles") or "")
    mb_tags = str(record.get("mb_tags") or "")
    summary = str(record.get("album_description") or record.get("wiki_summary") or "")
    notes = str(record.get("discogs_notes") or "")
    personnel = str(record.get("personnel") or "")

    macro_genre = classify_macro_genre(genres, styles, mb_tags, description=summary or notes)
    derived_moods = extract_derived_moods(summary, notes, styles, genres)
    descriptive_tags = extract_descriptive_tags(summary, notes, styles, genres)

    has_summary = len(summary.strip()) >= 50
    has_review = bool(
        record.get("pitchfork_score") or
        record.get("metacritic_score") or
        record.get("allmusic_score") or
        record.get("guardian_score")
    )
    has_personnel = len(personnel.strip()) > 0
    disc_rat = record.get("discogs_rating")
    has_community = disc_rat is not None and float(disc_rat or 0.0) > 0.0

    quality_score = compute_enrichment_quality_score(has_summary, has_review, has_personnel, has_community)

    return {
        "macro_genre": macro_genre,
        "derived_moods": derived_moods,
        "descriptive_tags": descriptive_tags,
        "enrichment_quality_score": quality_score
    }
