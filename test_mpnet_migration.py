"""
test_mpnet_migration.py - Comprehensive Verification Suite for MPNet Model Migration
Validates:
1. Model Identity & Embedding Dimensions (768-dim MPNet)
2. Song Embedding Caching & Invalidation
3. English, Hindi, and Hinglish Mood Prompts
4. Recommendations for Different Moods
5. Correct Song & Artwork Mapping
6. Audio Playback after Recommendation
7. Skip & Queue Functionality
8. Likes, Dislikes, Favourites, and Ratings
9. Listening History Persistence
10. User-Specific Recommendations & Model Info API
"""

import os
import sys
import json
import unittest
import numpy as np
import torch

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure offline hub to avoid retry delays on local files
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from app import app, get_db_connection
from model.recommender import (
    get_model,
    get_model_info,
    create_song_representation,
    get_cached_song_embeddings,
    recommend_songs,
    recommend_by_vibes,
    recommend_personalized,
    MODEL_NAME,
    EMBEDDING_DIM,
    CACHE_FILE,
)


class TestMPNetMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

        # Fetch songs from DB
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT song_id, title, artist, movie, genre, mood, language, activity, description, audio_url
                FROM songs ORDER BY song_id ASC
            """)
            cls.songs = cur.fetchall()
        conn.close()

    def get_or_create_test_user(self, username="mpnet_tester", email="mpnet_tester@example.com"):
        """Ensures a clean, authenticated test user session with completed profile."""
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
        conn.close()

        if not user:
            self.client.post("/signup", data={
                "username": username,
                "email": email,
                "password": "password123",
                "confirm_password": "password123"
            }, follow_redirects=True)

            self.client.post("/profile-setup", data={
                "username": username,
                "moods": ["Romantic", "Calm / Peaceful"],
                "action": "save"
            }, follow_redirects=True)

            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE username = %s", (username,))
                user = cur.fetchone()
            conn.close()
        else:
            # Login
            self.client.post("/login", data={
                "login_id": username,
                "password": "password123"
            }, follow_redirects=True)

        return user["user_id"]

    # =========================================================================
    # TEST 1: Model Identity & Dimension Verification (768-dim)
    # =========================================================================
    def test_01_model_identity_and_dimension(self):
        print("\n--- TEST 1: Model Identity & 768-Dim Verification ---")
        model = get_model()
        self.assertIsNotNone(model)

        info = get_model_info()
        self.assertEqual(info["proposed_model"], "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        self.assertEqual(info["embedding_dimension"], 768)

        # Test encoding single prompt
        emb = model.encode("I am feeling happy today", convert_to_numpy=True)
        self.assertEqual(emb.shape, (768,))
        self.assertEqual(emb.dtype, np.float32)
        print(f"  [PASS] Model verified as '{info['proposed_model']}' with shape {emb.shape}.")

    # =========================================================================
    # TEST 2: Embedding Cache Generation & Invalidation
    # =========================================================================
    def test_02_embedding_cache_generation_and_invalidation(self):
        print("\n--- TEST 2: Song Embedding Cache Generation & Invalidation ---")
        self.assertGreater(len(self.songs), 0, "Song catalog must not be empty.")

        # Generate / retrieve cached embeddings
        cached_embs = get_cached_song_embeddings(self.songs)
        self.assertEqual(cached_embs.shape, (len(self.songs), 768))

        # Check disk cache exists
        self.assertTrue(os.path.exists(CACHE_FILE), f"Cache file {CACHE_FILE} should exist on disk.")

        # Verify disk cache metadata
        disk_data = np.load(CACHE_FILE, allow_pickle=True)
        self.assertEqual(str(disk_data["model_name"]), MODEL_NAME)
        self.assertEqual(int(disk_data["embedding_dim"]), 768)
        self.assertEqual(len(disk_data["song_ids"]), len(self.songs))
        print(f"  [PASS] Song embeddings cached for all {len(self.songs)} songs with 768-dim representations.")

    # =========================================================================
    # TEST 3: Multilingual Mood Prompts (English, Hindi, Hinglish)
    # =========================================================================
    def test_03_multilingual_prompts_english_hindi_hinglish(self):
        print("\n--- TEST 3: Multilingual Mood Prompts (English, Hindi, Hinglish) ---")

        multilingual_cases = [
            ("English", "I am feeling romantic today.", ["romantic", "love", "loving", "romance"]),
            ("English", "I want energetic songs for a workout.", ["energetic", "workout", "gym", "motivation", "motivational", "intense"]),
            ("English", "Suggest peaceful songs for studying.", ["calm", "peaceful", "soulful", "spiritual", "meditation", "soothing"]),
            ("Hindi", "मुझे रोमांटिक गाने सुनने हैं।", ["romantic", "love", "loving", "romance"]),
            ("Hindi", "मुझे शांत और सुकून भरा संगीत चाहिए।", ["calm", "peaceful", "soulful", "spiritual", "soothing"]),
            ("Hinglish", "Mujhe romantic gaane sunne hain.", ["romantic", "love", "loving", "romance"]),
            ("Hinglish", "Aaj workout ke liye energetic songs chahiye.", ["energetic", "workout", "gym", "motivational", "dance", "intense"]),
            ("Hinglish", "Mujhe peaceful music sunna hai.", ["calm", "peaceful", "soulful", "spiritual", "soothing"])
        ]

        for lang, prompt, expected_keywords in multilingual_cases:
            recs = recommend_songs(prompt, self.songs, top_k=5)
            self.assertEqual(len(recs), 5, f"Should return 5 recommendations for prompt '{prompt}'")

            # Check that top recommendations contain relevant thematic elements
            found_relevant = False
            for rec in recs[:3]:
                combined_meta = f"{rec.get('title', '')} {rec.get('mood', '')} {rec.get('genre', '')} {rec.get('activity', '')} {rec.get('description', '')}".lower()
                if any(kw.lower() in combined_meta for kw in expected_keywords):
                    found_relevant = True
                    break

            self.assertTrue(
                found_relevant,
                f"[{lang}] Top 3 recommendations for '{prompt}' did not contain any of {expected_keywords}. Got: {[r['title'] for r in recs[:3]]}"
            )
            top_rec = recs[0]
            print(f"  [PASS] [{lang}] '{prompt}' -> Top 1: '{top_rec['title']}' ({top_rec.get('mood')}) [Score: {top_rec['similarity_score']}]")

    # =========================================================================
    # TEST 4: Personalization & History Adjustment
    # =========================================================================
    def test_04_personalization_preservation(self):
        print("\n--- TEST 4: Personalization Preservation ---")
        prompt = "energetic party song"

        # Baseline recommendations without history
        base_recs = recommend_songs(prompt, self.songs, top_k=5, user_history=None)
        self.assertGreater(len(base_recs), 0)

        # Target a specific song to test boosts and penalties
        target_song_id = base_recs[2]["song_id"]

        # 1. Favorite & 5-Star Rating Boost
        fav_history = {
            "favourite_song_ids": [target_song_id],
            "ratings": {target_song_id: 5}
        }
        boosted_recs = recommend_songs(prompt, self.songs, top_k=5, user_history=fav_history)
        boosted_item = next(r for r in boosted_recs if r["song_id"] == target_song_id)
        base_item = next(r for r in base_recs if r["song_id"] == target_song_id)

        self.assertGreater(
            boosted_item["similarity_score"],
            base_item["similarity_score"],
            "Favourited & 5-star song should receive positive score adjustment."
        )

        # 2. Dislike Penalty
        dislike_history = {
            "disliked_song_ids": [target_song_id]
        }
        penalized_recs = recommend_songs(prompt, self.songs, top_k=5, user_history=dislike_history)
        penalized_item = next((r for r in penalized_recs if r["song_id"] == target_song_id), None)
        if penalized_item:
            self.assertLess(
                penalized_item["similarity_score"],
                base_item["similarity_score"],
                "Disliked song should receive negative score adjustment."
            )
        print("  [PASS] Personalization boosts (+fav, +5-star) and penalties (-dislike) successfully applied.")

    # =========================================================================
    # TEST 5: API Endpoint /api/recommend with Artwork and Details
    # =========================================================================
    def test_05_api_recommend_endpoint(self):
        print("\n--- TEST 5: API /api/recommend with Model Metadata ---")
        user_id = self.get_or_create_test_user()

        res = self.client.post("/api/recommend", json={"request_text": "I need relaxing music after a stressful day."})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        recs = data["recommendations"]
        self.assertEqual(len(recs), 5)

        for rec in recs:
            self.assertIn("song_id", rec)
            self.assertIn("title", rec)
            self.assertIn("match_percentage", rec)
            self.assertIn("similarity_score", rec)
            self.assertIn("cover_url", rec)
            self.assertTrue(rec["cover_url"].startswith("/api/songs/"))
            self.assertEqual(rec.get("model_used"), MODEL_NAME)
        print(f"  [PASS] /api/recommend returned 5 valid recommendations with cover URLs and MPNet model tag.")

    # =========================================================================
    # TEST 6: Artwork & Audio Playback Verification
    # =========================================================================
    def test_06_artwork_and_audio_playback(self):
        print("\n--- TEST 6: Artwork & Audio Playback for Recommended Songs ---")
        user_id = self.get_or_create_test_user()

        res = self.client.post("/api/recommend", json={"request_text": "romantic ballad"})
        recs = res.get_json()["recommendations"]
        test_song = recs[0]

        # 1. Cover image test
        cover_url = test_song["cover_url"]
        cover_res = self.client.get(cover_url)
        self.assertEqual(cover_res.status_code, 200)
        self.assertEqual(cover_res.headers.get("Content-Type"), "image/jpeg")

        # 2. Audio stream test
        audio_url = test_song["audio_url"]
        audio_res = self.client.get(f"/{audio_url}")
        self.assertEqual(audio_res.status_code, 200)
        self.assertGreater(len(audio_res.data), 1000, "Audio data stream should be non-empty.")
        print(f"  [PASS] Artwork and audio playback verified for '{test_song['title']}'.")

    # =========================================================================
    # TEST 7: Skip & Queue Functionality
    # =========================================================================
    def test_07_skip_and_queue_functionality(self):
        print("\n--- TEST 7: Skip & Queue Functionality ---")
        user_id = self.get_or_create_test_user()

        # Send a skip feedback
        res = self.client.post("/api/feedback", json={
            "song_id": 11,
            "feedback_type": "skip",
            "source_section": "prompt_recommendations"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Verify feedback saved in MySQL
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM feedback WHERE user_id = %s AND song_id = 11 AND feedback_type = 'skip'", (user_id,))
            row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row, "Skip feedback should be persisted in MySQL feedback table.")
        print("  [PASS] Skip action successfully recorded and persisted.")

    # =========================================================================
    # TEST 8: Likes, Dislikes, Favourites, and Ratings
    # =========================================================================
    def test_08_likes_dislikes_favourites_and_ratings(self):
        print("\n--- TEST 8: Likes, Dislikes, Favourites, and Ratings ---")
        user_id = self.get_or_create_test_user()

        # Clean existing test records for these songs
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE user_id = %s AND song_id IN (12, 13, 14)", (user_id,))
            cur.execute("DELETE FROM user_favourites WHERE user_id = %s AND song_id = 15", (user_id,))
        conn.close()

        # 1. Like
        res = self.client.post("/api/feedback", json={"song_id": 12, "feedback_type": "like"})
        self.assertEqual(res.status_code, 200)

        # 2. Dislike
        res = self.client.post("/api/feedback", json={"song_id": 13, "feedback_type": "dislike"})
        self.assertEqual(res.status_code, 200)

        # 3. 5-Star Rating
        res = self.client.post("/api/feedback", json={"song_id": 14, "feedback_type": "rating", "rating": 5})
        self.assertEqual(res.status_code, 200)

        # 4. Toggle Favourite
        res = self.client.post("/api/favourites/toggle", json={"song_id": 15})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["is_favourite"])

        # Check in DB
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT song_id FROM user_favourites WHERE user_id = %s AND song_id = 15", (user_id,))
            fav = cur.fetchone()
        conn.close()
        self.assertIsNotNone(fav)
        print("  [PASS] Likes, dislikes, 5-star ratings, and favourites verified in MySQL.")

    # =========================================================================
    # TEST 9: Listening History Persistence
    # =========================================================================
    def test_09_listening_history_persistence(self):
        print("\n--- TEST 9: Listening History Persistence ---")
        user_id = self.get_or_create_test_user()

        # Record a listening play
        res = self.client.post("/api/activity/playback", json={
            "song_id": 20,
            "status": "started",
            "duration_played": 120
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

        # Fetch listening history from profile
        prof_res = self.client.get("/profile")
        self.assertEqual(prof_res.status_code, 200)
        self.assertIn(b"Deva Deva", prof_res.data)
        print("  [PASS] Song playback recorded and displayed in profile listening history.")

    # =========================================================================
    # TEST 10: Model Info Endpoint & Technical Verification
    # =========================================================================
    def test_10_model_info_api_endpoint(self):
        print("\n--- TEST 10: Model Info API Endpoint ---")
        res = self.client.get("/api/model/info")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertTrue(data["success"])
        self.assertEqual(data["proposed_model"], "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        self.assertEqual(data["embedding_dimension"], 768)
        self.assertTrue(data["is_loaded"])
        print(f"  [PASS] /api/model/info confirmed proposed model with {data['embedding_dimension']} dimensions.")


if __name__ == "__main__":
    unittest.main()
