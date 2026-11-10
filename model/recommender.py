"""
Music Recommender Model
Active Primary Model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2

Computes 768-dimensional semantic embeddings to match natural-language user requests
(English, Hindi, and Hinglish) with songs from the MySQL database catalogue,
combined with history-aware personalization (vibes, past searches, likes, ratings, dislikes, skips).
"""

import os
import sys
import hashlib
import threading
import logging
import numpy as np
import torch

# Configure logging
logger = logging.getLogger(__name__)

# Active primary model configuration
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EMBEDDING_DIM = 768

# Global thread-safe singleton lock and instance
_model_lock = threading.Lock()
_model_instance = None

# Cache directory & file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "song_embeddings_mpnet.npz")

# In-memory song embedding cache protected by a lock
_cache_lock = threading.Lock()
_in_memory_embeddings = {}  # song_id -> np.ndarray (768,)
_in_memory_hashes = {}      # song_id -> str (md5 of text representation)
_in_memory_model_tag = None


def compute_cosine_similarity(a, b):
    """
    Computes cosine similarity between query tensor (1, D) and catalog tensor (N, D).
    Uses native PyTorch operations for maximum speed without external package overhead.
    """
    if not isinstance(a, torch.Tensor):
        a = torch.tensor(a, dtype=torch.float32)
    if not isinstance(b, torch.Tensor):
        b = torch.tensor(b, dtype=torch.float32)
    if a.dim() == 1:
        a = a.unsqueeze(0)
    if b.dim() == 1:
        b = b.unsqueeze(0)
    a_norm = torch.nn.functional.normalize(a, p=2, dim=1)
    b_norm = torch.nn.functional.normalize(b, p=2, dim=1)
    return torch.mm(a_norm, b_norm.transpose(0, 1))


def get_model():
    """
    Thread-safe lazy loader for the primary MPNet recommendation model:
    sentence-transformers/paraphrase-multilingual-mpnet-base-v2.
    Loads onto CUDA if available, otherwise CPU.
    Avoids redundant reloads across concurrent requests.
    """
    global _model_instance
    if _model_instance is None:
        with _model_lock:
            if _model_instance is None:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                print(f"[INFO] Loading primary recommendation model '{MODEL_NAME}' on {device}...", flush=True)
                try:
                    from sentence_transformers import SentenceTransformer
                    # Attempt loading from local HF cache first for instant startup
                    try:
                        _model_instance = SentenceTransformer(
                            MODEL_NAME, device=device, local_files_only=True
                        )
                    except Exception:
                        _model_instance = SentenceTransformer(MODEL_NAME, device=device)
                    print(f"[INFO] Model '{MODEL_NAME}' loaded successfully with {EMBEDDING_DIM}-dim embeddings.", flush=True)
                except Exception as exc:
                    err_msg = (
                        f"Failed to load primary recommendation model '{MODEL_NAME}'. "
                        f"Please ensure huggingface model is downloaded. Error: {exc}"
                    )
                    logger.error(err_msg)
                    raise RuntimeError(err_msg) from exc
    return _model_instance


def preload_model():
    """Explicitly pre-loads the primary MPNet model into memory during server startup."""
    return get_model()


def get_model_info():
    """Returns technical metadata about the active sentence-transformers model."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return {
        "primary_model": MODEL_NAME,
        "proposed_model": MODEL_NAME,
        "embedding_dimension": EMBEDDING_DIM,
        "device": device,
        "is_loaded": _model_instance is not None,
        "cache_file": CACHE_FILE,
        "cached_songs_count": len(_in_memory_embeddings)
    }


def create_song_representation(song):
    """
    Creates a combined text representation for a song using its:
    title, movie, artist, genre, mood, language, activity, and description.
    Safely handles missing or NULL fields.
    """
    if not isinstance(song, dict):
        return ""

    title = str(song.get("title") or "").strip()
    movie = str(song.get("movie") or "").strip()
    artist = str(song.get("artist") or "").strip()
    genre = str(song.get("genre") or "").strip()
    mood = str(song.get("mood") or "").strip()
    language = str(song.get("language") or "").strip()
    activity = str(song.get("activity") or "").strip()
    description = str(song.get("description") or "").strip()

    return (
        f"Title: {title}. "
        f"Movie: {movie}. "
        f"Artist: {artist}. "
        f"Genre: {genre}. "
        f"Mood: {mood}. "
        f"Language: {language}. "
        f"Activity: {activity}. "
        f"Description: {description}"
    )


def _hash_text(text):
    """Generates an MD5 digest of the input text for cache validation."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _ensure_cache_dir():
    """Ensures the cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _load_disk_cache():
    """
    Loads song embeddings from disk cache if present and valid.
    Invalidates any obsolete cache generated with older or mismatched models.
    """
    global _in_memory_embeddings, _in_memory_hashes, _in_memory_model_tag

    if not os.path.exists(CACHE_FILE):
        return False

    try:
        data = np.load(CACHE_FILE, allow_pickle=True)
        cached_model = str(data.get("model_name", ""))
        cached_dim = int(data.get("embedding_dim", 0))

        # Check for model version mismatch or obsolete embeddings
        if cached_model != MODEL_NAME or cached_dim != EMBEDDING_DIM:
            logger.warning(
                f"[CACHE INVALIDATION] Disk cache model '{cached_model}' ({cached_dim} dims) "
                f"does not match active '{MODEL_NAME}' ({EMBEDDING_DIM} dims). Invalidating cache."
            )
            try:
                os.remove(CACHE_FILE)
            except OSError:
                pass
            return False

        song_ids = data["song_ids"]
        hashes = data["hashes"]
        embeddings = data["embeddings"]

        if len(song_ids) == len(hashes) == len(embeddings):
            for sid, h, emb in zip(song_ids, hashes, embeddings):
                _in_memory_embeddings[int(sid)] = emb.astype(np.float32)
                _in_memory_hashes[int(sid)] = str(h)
            _in_memory_model_tag = MODEL_NAME
            logger.info(f"Loaded {len(_in_memory_embeddings)} song embeddings from disk cache.")
            return True
    except Exception as e:
        logger.warning(f"Failed to read disk cache '{CACHE_FILE}': {e}. Regenerating...")
        try:
            os.remove(CACHE_FILE)
        except OSError:
            pass

    return False


def _save_disk_cache():
    """Persists current in-memory embeddings to disk compressed."""
    if not _in_memory_embeddings:
        return

    _ensure_cache_dir()
    try:
        song_ids = np.array(list(_in_memory_embeddings.keys()), dtype=int)
        hashes = np.array([_in_memory_hashes[sid] for sid in song_ids])
        embeddings = np.vstack([_in_memory_embeddings[sid] for sid in song_ids]).astype(np.float32)

        np.savez_compressed(
            CACHE_FILE,
            model_name=MODEL_NAME,
            embedding_dim=EMBEDDING_DIM,
            song_ids=song_ids,
            hashes=hashes,
            embeddings=embeddings
        )
        logger.info(f"Persisted {len(song_ids)} MPNet song embeddings to {CACHE_FILE}.")
    except Exception as e:
        logger.warning(f"Could not persist embeddings to disk cache: {e}")


def get_cached_song_embeddings(songs, model=None):
    """
    Retrieves or generates 768-dimensional embeddings for all songs in the catalog.
    Uses in-memory cache first, falls back to disk cache, and encodes only missing or updated songs.
    Returns a PyTorch tensor of shape (len(songs), 768).
    """
    global _in_memory_embeddings, _in_memory_hashes, _in_memory_model_tag

    if not songs:
        return torch.empty((0, EMBEDDING_DIM))

    with _cache_lock:
        # Load from disk if memory cache is empty or from old model
        if _in_memory_model_tag != MODEL_NAME:
            _in_memory_embeddings.clear()
            _in_memory_hashes.clear()
            _load_disk_cache()
            _in_memory_model_tag = MODEL_NAME

        # Determine which songs need encoding
        songs_to_encode = []
        indices_to_encode = []

        for idx, song in enumerate(songs):
            sid = song.get("song_id")
            repr_text = create_song_representation(song)
            repr_hash = _hash_text(repr_text)

            # Check if cached and representation is unchanged
            if (
                sid not in _in_memory_embeddings
                or _in_memory_hashes.get(sid) != repr_hash
                or _in_memory_embeddings[sid].shape[-1] != EMBEDDING_DIM
            ):
                songs_to_encode.append(repr_text)
                indices_to_encode.append((sid, repr_hash))

        # If any songs are new, updated, or missing from cache, encode them
        if songs_to_encode:
            if model is None:
                model = get_model()

            logger.info(f"Generating MPNet embeddings for {len(songs_to_encode)} missing/updated songs...")
            new_embeddings = model.encode(
                songs_to_encode,
                convert_to_numpy=True,
                show_progress_bar=False
            )

            for (sid, r_hash), emb in zip(indices_to_encode, new_embeddings):
                _in_memory_embeddings[sid] = emb.astype(np.float32)
                _in_memory_hashes[sid] = r_hash

            # Save updated cache to disk
            _save_disk_cache()

        # Build embeddings matrix matching the input songs order
        ordered_embeddings = [
            _in_memory_embeddings[song.get("song_id")]
            for song in songs
        ]
        embeddings_matrix = np.vstack(ordered_embeddings).astype(np.float32)

        # Convert to torch tensor for cosine similarity computation
        device = "cuda" if torch.cuda.is_available() else "cpu"
        return torch.from_numpy(embeddings_matrix).to(device)


def _check_keyword_overlap(text, keywords):
    """Helper to check if any of the given keywords appear in the target text (case-insensitive)."""
    if not text or not keywords:
        return False
    lower_text = text.lower()
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if kw_clean and (kw_clean in lower_text or any(part in lower_text for part in kw_clean.split() if len(part) > 3)):
            return True
    return False


def recommend_songs(user_text, songs, top_k=5, user_history=None):
    """
    Recommend top_k songs based on cosine similarity with user's current mood prompt,
    personalized by their stored preferences and interaction history.

    Supports natural language requests in English, Hindi, and Hinglish.
    - Primary factor: Semantic similarity to the current prompt (75-80% weighting).
    - Secondary factor: Historical personalization (vibes, ratings, likes, favourites, dislikes, skips).
    """
    if not songs or not user_text or not str(user_text).strip():
        return []

    clean_prompt = str(user_text).strip()
    model = get_model()

    # 1. Generate user query embedding using proposed MPNet model (768 dimensions)
    user_embedding = model.encode(clean_prompt, convert_to_tensor=True)

    # 2. Retrieve cached song embeddings (768 dimensions)
    song_embeddings = get_cached_song_embeddings(songs, model=model)

    # 3. Calculate primary cosine similarity with current prompt
    cosine_scores = compute_cosine_similarity(user_embedding, song_embeddings)[0].cpu().numpy()

    # 4. Extract user history if provided
    history = user_history or {}
    vibe_prefs = history.get("vibe_preferences", [])
    liked_ids = set(history.get("liked_song_ids", []))
    disliked_ids = set(history.get("disliked_song_ids", []))
    favourite_ids = set(history.get("favourite_song_ids", []))
    skipped_ids = set(history.get("skipped_song_ids", []))
    ratings = history.get("ratings", {})  # {song_id: rating_int}
    past_prompts = history.get("past_prompts", [])

    scored_songs = []
    for idx, song in enumerate(songs):
        song_dict = dict(song)
        song_id = song_dict.get("song_id")
        raw_sim = float(cosine_scores[idx])

        # Personalization Adjustment
        adjustment = 0.0
        reasons = []

        # A. Basic Mood / Vibe Preference Match (+0.05)
        song_mood_genre = f"{song_dict.get('mood', '')} {song_dict.get('genre', '')} {song_dict.get('description', '')}"
        if vibe_prefs and _check_keyword_overlap(song_mood_genre, vibe_prefs):
            adjustment += 0.05
            reasons.append("matches your favorite vibes")

        # B. User Liked or Favourited (+0.04 to +0.06)
        if song_id in favourite_ids:
            adjustment += 0.04
            reasons.append("saved in your favorites")
        if song_id in liked_ids:
            adjustment += 0.04
            reasons.append("you liked this earlier")

        # C. Star Ratings
        if song_id in ratings:
            r = ratings[song_id]
            if r == 5:
                adjustment += 0.06
                reasons.append("rated 5 stars by you")
            elif r == 4:
                adjustment += 0.03
                reasons.append("rated 4 stars")
            elif r == 2:
                adjustment -= 0.05
            elif r == 1:
                adjustment -= 0.12

        # D. Disliked Songs Penalty (-0.15 penalty)
        if song_id in disliked_ids:
            adjustment -= 0.15

        # E. Skipped Songs (Mild penalty: -0.03, not treated as a full dislike)
        if song_id in skipped_ids and song_id not in liked_ids and song_id not in favourite_ids:
            adjustment -= 0.03

        # F. Past prompt alignment (Mild bonus: +0.02)
        if past_prompts and _check_keyword_overlap(song_mood_genre, past_prompts[:5]):
            adjustment += 0.02

        # Combined Score: Current mood is primary, adjustment personalizes ranking
        final_score = raw_sim + adjustment

        # Normalize score into intuitive percentage (45% to 98%)
        scaled = int(round(50 + (max(0.0, final_score) / 0.52) * 45))
        percentage = int(np.clip(scaled, 45, 98))

        # Dynamic note
        if reasons:
            dynamic_note = f"Recommended for your current mood & {', '.join(reasons[:2])}."
        else:
            dynamic_note = "Recommended based on your current mood request."

        song_dict["similarity_score"] = round(final_score, 4)
        song_dict["raw_similarity"] = round(raw_sim, 4)
        song_dict["match_percentage"] = percentage
        song_dict["dynamic_note"] = dynamic_note
        song_dict["model_used"] = MODEL_NAME
        scored_songs.append((final_score, song_dict))

    # Sort descending by final combined score
    scored_songs.sort(key=lambda x: x[0], reverse=True)

    return [item[1] for item in scored_songs[:top_k]]


def recommend_by_vibes(vibe_list, songs, top_k=6):
    """
    Generate automatic recommendations based on user's basic mood/vibe preferences
    saved during profile setup (Section B: Recommended for Your Vibe).
    Uses the proposed MPNet multilingual model.
    """
    if not songs:
        return []

    vibes = [v.strip() for v in vibe_list if v and v.strip()]
    if not vibes:
        vibes = ["Romantic", "Happy", "Calm / Peaceful", "Soulful"]

    vibe_query = " ".join(vibes) + " Indian Bollywood music songs"
    model = get_model()
    vibe_embedding = model.encode(vibe_query, convert_to_tensor=True)

    # Use cached song embeddings
    song_embeddings = get_cached_song_embeddings(songs, model=model)
    cosine_scores = compute_cosine_similarity(vibe_embedding, song_embeddings)[0].cpu().numpy()

    scored = []
    for idx, song in enumerate(songs):
        song_dict = dict(song)
        score = float(cosine_scores[idx])

        # Explicit vibe keyword boost
        song_meta = f"{song_dict.get('mood', '')} {song_dict.get('genre', '')} {song_dict.get('description', '')}"
        if _check_keyword_overlap(song_meta, vibes):
            score += 0.08

        scaled = int(round(55 + (max(0.0, score) / 0.52) * 40))
        percentage = int(np.clip(scaled, 50, 98))

        song_dict["match_percentage"] = percentage
        song_dict["similarity_score"] = round(score, 4)
        song_dict["dynamic_note"] = f"Curated for your vibe: {', '.join(vibes[:3])}"
        song_dict["model_used"] = MODEL_NAME
        scored.append((score, song_dict))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_k]]


def recommend_personalized(songs, user_history, top_k=6):
    """
    Generate personalized recommendations based on comprehensive interaction history:
    basic vibes, past mood searches, liked songs, 5-star ratings, and favourites
    (Section C: Personalized Recommendations).
    Uses the proposed MPNet multilingual model.
    """
    if not songs:
        return []

    history = user_history or {}
    vibe_prefs = history.get("vibe_preferences", [])
    past_prompts = history.get("past_prompts", [])
    liked_ids = set(history.get("liked_song_ids", []))
    favourite_ids = set(history.get("favourite_song_ids", []))
    disliked_ids = set(history.get("disliked_song_ids", []))
    skipped_ids = set(history.get("skipped_song_ids", []))
    ratings = history.get("ratings", {})
    played_ids = set(history.get("played_song_ids", []))

    # Construct composite taste text
    positive_elements = []
    if vibe_prefs:
        positive_elements.append(" ".join(vibe_prefs))
    if past_prompts:
        positive_elements.append(" ".join(past_prompts[:5]))

    # Add titles/moods of liked, 5-star, or favourited songs
    for song in songs:
        sid = song.get("song_id")
        if sid in favourite_ids or sid in liked_ids or ratings.get(sid, 0) >= 4:
            positive_elements.append(f"{song.get('title', '')} {song.get('mood', '')} {song.get('genre', '')}")

    if not positive_elements:
        return recommend_by_vibes(vibe_prefs, songs, top_k=top_k)

    composite_query = " ".join(positive_elements)
    model = get_model()
    taste_embedding = model.encode(composite_query, convert_to_tensor=True)

    # Use cached song embeddings
    song_embeddings = get_cached_song_embeddings(songs, model=model)
    cosine_scores = compute_cosine_similarity(taste_embedding, song_embeddings)[0].cpu().numpy()

    scored = []
    for idx, song in enumerate(songs):
        song_dict = dict(song)
        sid = song_dict.get("song_id")
        score = float(cosine_scores[idx])

        # Positive history bonuses
        if sid in favourite_ids:
            score += 0.06
        if sid in liked_ids:
            score += 0.05
        if ratings.get(sid, 0) == 5:
            score += 0.07
        elif ratings.get(sid, 0) == 4:
            score += 0.03

        # Negative history penalties
        if sid in disliked_ids:
            score -= 0.18
        if sid in skipped_ids and sid not in liked_ids and sid not in favourite_ids:
            score -= 0.03

        # Variety factor: slightly lower priority for songs already played recently
        if sid in played_ids:
            score -= 0.02

        scaled = int(round(52 + (max(0.0, score) / 0.52) * 42))
        percentage = int(np.clip(scaled, 50, 98))

        song_dict["match_percentage"] = percentage
        song_dict["similarity_score"] = round(score, 4)
        song_dict["dynamic_note"] = "Tailored from your listening history, ratings & favorites."
        song_dict["model_used"] = MODEL_NAME
        scored.append((score, song_dict))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_k]]
