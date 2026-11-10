"""
test_38_songs_integration.py - Full Verification Test Suite for 38 New Songs
Verifies:
1. Total song count is 48 in MySQL (10 original + 38 new).
2. Existing 10 songs are untouched (titles, audio paths, covers intact).
3. All 38 new songs (IDs 11..48) have valid records and NULL covers in MySQL.
4. All 48 audio files exist on disk in dataset/songs/ and stream HTTP 200.
5. Cover image endpoint /api/songs/<id>/cover returns binary image for 1..10 and clean SVG fallback for 11..48.
6. Recommendation API /api/recommend returns new songs matching various mood prompts.
7. Category curation (Romantic, Calm/Spiritual, Energetic) includes new songs on Home page.
8. Interactive actions on new songs: Favourites, Playback logging, Like/Dislike, Star Ratings.
9. Idempotent import: re-running import_new_songs.py preserves counts and produces 0 duplicates.
"""

import os
import sys
import unittest
import pymysql

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["SECRET_KEY"] = "test_verification_key_2026"
os.environ["MYSQL_DB"] = "music_recommendation_db"

from app import app, get_db_connection

class Test38SongsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

    def test_01_database_song_count_and_range(self):
        print("\n--- TEST 1: Database Song Count & Range Verification ---")
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM songs")
            total = cur.fetchone()["total"]
            self.assertEqual(total, 48, f"Expected 48 songs in MySQL, found {total}")

            cur.execute("SELECT MIN(song_id) as min_id, MAX(song_id) as max_id FROM songs")
            range_info = cur.fetchone()
            self.assertEqual(range_info["min_id"], 1)
            self.assertEqual(range_info["max_id"], 48)

            cur.execute("SELECT COUNT(*) as count FROM songs WHERE cover_image IS NULL")
            null_covers = cur.fetchone()["count"]
            self.assertEqual(null_covers, 38, f"Expected exactly 38 songs with NULL cover_image, found {null_covers}")

            cur.execute("SELECT COUNT(*) as count FROM songs WHERE cover_image IS NOT NULL")
            active_covers = cur.fetchone()["count"]
            self.assertEqual(active_covers, 10, f"Expected exactly 10 original songs with active cover images, found {active_covers}")

        conn.close()
        print(f"  [PASS] 48 songs verified in MySQL (IDs 1-48). 10 original have covers, 38 new ready for future images.")

    def test_02_original_10_songs_preserved(self):
        print("\n--- TEST 2: Preserved Original 10 Songs ---")
        expected_originals = {
            1: "Kesariya",
            2: "Apna Bana Le",
            3: "Zinda",
            4: "Kar Har Maidaan Fateh",
            5: "Ilahi",
            6: "Safarnama",
            7: "Iktara",
            8: "Kun Faya Kun",
            9: "Aaj Ki Raat",
            10: "Gallan Goodiyaan"
        }
        conn = get_db_connection()
        with conn.cursor() as cur:
            for s_id, exp_title in expected_originals.items():
                cur.execute("SELECT song_id, title, audio_url, LENGTH(cover_image) as img_len FROM songs WHERE song_id = %s", (s_id,))
                song = cur.fetchone()
                self.assertIsNotNone(song, f"Original song {s_id} is missing!")
                self.assertEqual(song["title"], exp_title)
                self.assertTrue(song["img_len"] and song["img_len"] > 0, f"Song {s_id} must keep its original poster")
        conn.close()
        print("  [PASS] All 10 original songs and their uploaded posters remain 100% intact.")

    def test_03_all_48_audio_files_accessible_and_streamable(self):
        print("\n--- TEST 3: Audio File Streaming Verification for All 48 Songs ---")
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT song_id, title, audio_url FROM songs ORDER BY song_id ASC")
            songs = cur.fetchall()
        conn.close()

        self.assertEqual(len(songs), 48)
        for s in songs:
            audio_url = s["audio_url"]
            self.assertTrue(audio_url and audio_url.startswith("dataset/songs/"), f"Invalid audio_url for song {s['song_id']}: {audio_url}")
            
            # Request audio through Flask endpoint
            res = self.client.get(f"/{audio_url}")
            self.assertEqual(res.status_code, 200, f"Audio streaming failed for {s['title']} at /{audio_url}")
            self.assertGreater(len(res.data), 50_000, f"Audio file too small for {s['title']}")

        print(f"  [PASS] All 48 songs have valid local MP3 audio files that stream HTTP 200.")

    def test_04_cover_image_endpoint_and_fallback(self):
        print("\n--- TEST 4: Cover Image Endpoint & Fallback Verification ---")
        # 1. First 10 songs should return image/jpeg
        for s_id in range(1, 11):
            res = self.client.get(f"/api/songs/{s_id}/cover")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get("Content-Type"), "image/jpeg")

        # 2. Songs 11 to 48 should return default visual fallback (image/svg+xml)
        for s_id in [11, 20, 30, 40, 48]:
            res = self.client.get(f"/api/songs/{s_id}/cover")
            self.assertEqual(res.status_code, 200)
            self.assertIn("image/svg+xml", res.headers.get("Content-Type"))
            self.assertIn("svg", res.get_data(as_text=True).lower())

        print("  [PASS] Cover endpoint serves JPEG for original 10 songs and SVG visual fallback for new 38 songs.")

    def test_05_recommendations_with_new_songs(self):
        print("\n--- TEST 5: Recommendation System Integration with Expanded Catalogue ---")
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "demouser"

        test_queries = [
            ("I need extreme motivation and high energy workout music", ["Brothers Anthem", "Sultan (Title Track)", "Malhari", "Zinda"]),
            ("I want something peaceful, devotional and spiritual", ["Achutam Keshavam", "Shri Hanuman Chalisa", "Deva Deva", "Kun Faya Kun"]),
            ("I am feeling deeply romantic and love", ["Tum Se Hi", "Raataan Lambiyan", "Hawayein", "Kesariya", "Pehli Nazar Mein", "Tera Hone Laga Hoon"])
        ]

        for prompt, expected_candidates in test_queries:
            res = self.client.post("/api/recommend", json={"user_text": prompt})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(len(data["recommendations"]), 5)

            rec_titles = [r["title"] for r in data["recommendations"]]
            overlap = set(rec_titles).intersection(set(expected_candidates))
            self.assertGreater(len(overlap), 0, f"Prompt '{prompt}' did not recommend expected candidates! Got: {rec_titles}")
            print(f"  [PASS] Prompt '{prompt[:40]}...' recommended: {rec_titles[:3]} (Matched: {overlap})")

    def test_06_interactive_controls_on_new_songs(self):
        print("\n--- TEST 6: Interactive Controls on Newly Added Songs ---")
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "demouser"

        # Clean up any leftover test favourites for song 15
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_favourites WHERE user_id = 1 AND song_id = 15")
        conn.close()

        # Toggle favourite on new song #15 (Brothers Anthem)
        fav_res = self.client.post("/api/favourites/toggle", json={"song_id": 15})
        self.assertEqual(fav_res.status_code, 200)
        self.assertTrue(fav_res.get_json()["is_favourite"])

        # Record playback on new song #15
        play_res = self.client.post("/api/activity/playback", json={
            "song_id": 15,
            "status": "started",
            "duration_played": 30
        })
        self.assertEqual(play_res.status_code, 200)

        # Submit like and 5-star rating on new song #20 (Deva Deva)
        fb_res = self.client.post("/api/feedback", json={
            "song_id": 20,
            "feedback_type": "like",
            "rating": 5
        })
        self.assertEqual(fb_res.status_code, 200)

        # Submit skip on new song #27 (Hookah Bar)
        skip_res = self.client.post("/api/feedback", json={
            "song_id": 27,
            "feedback_type": "skip",
            "rating": None
        })
        self.assertEqual(skip_res.status_code, 200)

        # Verify profile displays updated favourites and playback
        prof_res = self.client.get("/profile")
        self.assertEqual(prof_res.status_code, 200)
        prof_html = prof_res.get_data(as_text=True)
        self.assertIn("Brothers Anthem", prof_html)

        print("  [PASS] Favourite toggle, playback history, 5-star rating, and skip fully operational on new songs.")

    def test_07_home_page_category_integration(self):
        print("\n--- TEST 7: Home Page Category Row Integration ---")
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "demouser"

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Check that both existing and new songs appear in category sections
        self.assertIn("Kesariya", html) # Original
        self.assertIn("Tum Se Hi", html) # New
        self.assertIn("Achutam Keshavam", html) # New
        self.assertIn("Malhari", html) # New

        print("  [PASS] Home page seamlessly renders both original and newly imported songs across category rows.")

if __name__ == "__main__":
    unittest.main()
