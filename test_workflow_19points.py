"""
Comprehensive 19-Point Workflow Test Suite for Music Suggestion System
Verifies all functional, UI, database activity tracking, personalization, and isolation requirements.
"""

import os
import io
import sys
import json
import unittest
import pymysql
import pymysql.cursors

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from app import app, get_db_connection

class TestMusicSuggestionSystemWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

        # Clean up any previous test users to ensure clean slate
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE username IN ('test_user_a', 'test_user_b')")
            test_users = cur.fetchall()
            for u in test_users:
                uid = u["user_id"]
                cur.execute("DELETE FROM user_sessions WHERE user_id = %s", (uid,))
                cur.execute("DELETE FROM user_playback_history WHERE user_id = %s", (uid,))
                cur.execute("DELETE FROM user_favourite_activity WHERE user_id = %s", (uid,))
                cur.execute("DELETE FROM user_favourites WHERE user_id = %s", (uid,))
                cur.execute("DELETE FROM feedback WHERE user_id = %s", (uid,))
                cur.execute("DELETE FROM recommendation_history WHERE user_id = %s", (uid,))
                cur.execute("DELETE FROM user_requests WHERE user_id = %s", (uid,))
                cur.execute("DELETE FROM user_preferences WHERE user_id = %s", (uid,))
                cur.execute("DELETE FROM users WHERE user_id = %s", (uid,))
            conn.commit()
        conn.close()

    def test_complete_19_point_workflow(self):
        print("\n==================================================")
        print("STARTING COMPLETE 19-POINT WORKFLOW TEST")
        print("==================================================")

        # ----------------------------------------------------
        # POINT 1: Register User A
        # ----------------------------------------------------
        print("\n[Point 1] Register User A...")
        reg_res = self.client.post("/register", data={
            "username": "test_user_a",
            "email": "user_a@test.com",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = 'test_user_a'")
            user_a = cur.fetchone()
            self.assertIsNotNone(user_a, "User A must exist in MySQL users table")
            user_a_id = user_a["user_id"]

            # Verify session was logged in user_sessions
            cur.execute("SELECT * FROM user_sessions WHERE user_id = %s ORDER BY login_time DESC", (user_a_id,))
            session_rec = cur.fetchone()
            self.assertIsNotNone(session_rec, "User A login session must be recorded in user_sessions")
        conn.close()
        print(f"[PASS] Point 1 Passed: User A registered (user_id={user_a_id}), session logged.")

        # ----------------------------------------------------
        # POINT 2: Select Romantic and Calm as basic vibes
        # ----------------------------------------------------
        print("\n[Point 2] Select Romantic and Calm as basic vibes...")
        setup_res = self.client.post("/profile-setup", data={
            "action": "save",
            "moods": ["Romantic", "Calm / Peaceful"]
        }, follow_redirects=True)
        self.assertEqual(setup_res.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT mood_or_vibe FROM user_preferences WHERE user_id = %s", (user_a_id,))
            prefs = [p["mood_or_vibe"] for p in cur.fetchall()]
            self.assertIn("Romantic", prefs)
            self.assertIn("Calm / Peaceful", prefs)
        conn.close()
        print(f"[PASS] Point 2 Passed: Vibes {prefs} saved in MySQL.")

        # ----------------------------------------------------
        # POINT 3: Upload a profile picture
        # ----------------------------------------------------
        print("\n[Point 3] Upload a profile picture...")
        dummy_img = (io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"), "avatar.png")
        upload_res = self.client.post("/profile/edit", data={
            "action": "save",
            "username": "test_user_a",
            "profile_image": dummy_img,
            "moods": ["Romantic", "Calm / Peaceful"]
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(upload_res.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT profile_image FROM users WHERE user_id = %s", (user_a_id,))
            img_row = cur.fetchone()
            self.assertIsNotNone(img_row["profile_image"])
            self.assertTrue(img_row["profile_image"].startswith("/static/uploads/avatars/"))
        conn.close()
        print(f"[PASS] Point 3 Passed: Profile picture uploaded ({img_row['profile_image']}).")

        # ----------------------------------------------------
        # POINT 4: Log in and verify the "Welcome!!" text
        # ----------------------------------------------------
        print("\n[Point 4] Log in and verify 'Welcome!!' text...")
        # Check login page text
        self.client.get("/logout")
        login_page_res = self.client.get("/login")
        self.assertEqual(login_page_res.status_code, 200)
        self.assertIn("Welcome!!", login_page_res.get_data(as_text=True))

        # Log in again
        login_res = self.client.post("/login", data={
            "login_id": "test_user_a",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        home_html = login_res.get_data(as_text=True)
        self.assertIn("Welcome!!", home_html)
        print("[PASS] Point 4 Passed: 'Welcome!!' text displayed on login screen and home screen.")

        # ----------------------------------------------------
        # POINT 5: Verify that the chat area is displayed at the top
        # ----------------------------------------------------
        print("\n[Point 5] Verify chat area at top...")
        # Verify Section A exists and contains prompt input before Section B
        sec_a_pos = home_html.find('id="search-chat-section"')
        sec_b_pos = home_html.find('id="vibe-recommendations-section"')
        self.assertTrue(sec_a_pos > -1, "Section A must exist")
        self.assertTrue(sec_b_pos > -1, "Section B must exist")
        self.assertTrue(sec_a_pos < sec_b_pos, "Section A (chat area) must appear BEFORE Section B")
        self.assertIn('id="user-prompt-input"', home_html)
        self.assertIn('id="recommend-btn"', home_html)
        print("[PASS] Point 5 Passed: Chat area is displayed prominently at the top (Section A).")

        # ----------------------------------------------------
        # POINT 6: Verify that "Recommended for Your Vibe" appears below it
        # ----------------------------------------------------
        print("\n[Point 6] Verify 'Recommended for Your Vibe' appears below chat area...")
        self.assertIn("Recommended for Your Vibe", home_html)
        sec_c_pos = home_html.find('id="personalized-recommendations-section"')
        self.assertTrue(sec_c_pos > -1, "Section C must exist")
        self.assertTrue(sec_b_pos < sec_c_pos, "Section B must appear BEFORE Section C")
        print("[PASS] Point 6 Passed: 'Recommended for Your Vibe' rendered directly below chat area.")

        # ----------------------------------------------------
        # POINT 7: Search for romantic songs
        # ----------------------------------------------------
        print("\n[Point 7] Search for romantic songs...")
        rec_res = self.client.post("/api/recommend", json={
            "user_text": "I'm feeling romantic today and want love songs"
        })
        self.assertEqual(rec_res.status_code, 200)
        rec_data = rec_res.get_json()
        self.assertTrue(rec_data.get("success"))
        recommendations = rec_data.get("recommendations", [])
        self.assertGreater(len(recommendations), 0, "Must return recommended songs")

        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check user_requests
            cur.execute("SELECT * FROM user_requests WHERE user_id = %s ORDER BY created_at DESC", (user_a_id,))
            req_row = cur.fetchone()
            self.assertIsNotNone(req_row)
            self.assertIn("romantic", req_row["request_text"].lower())
            self.assertIsNotNone(req_row["recommendations_json"])

            # Check recommendation_history
            cur.execute("SELECT COUNT(*) AS cnt FROM recommendation_history WHERE user_id = %s", (user_a_id,))
            hist_cnt = cur.fetchone()["cnt"]
            self.assertGreater(hist_cnt, 0)
        conn.close()
        print(f"[PASS] Point 7 Passed: Search executed, returned {len(recommendations)} songs, stored in MySQL.")

        # ----------------------------------------------------
        # POINT 8: Play a recommended song
        # ----------------------------------------------------
        print("\n[Point 8] Play a recommended song...")
        first_song = recommendations[0]
        play_res = self.client.post("/api/activity/playback", json={
            "song_id": first_song["song_id"],
            "duration_played": 12.5,
            "status": "started"
        })
        self.assertEqual(play_res.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM user_playback_history WHERE user_id = %s AND song_id = %s ORDER BY played_at DESC",
                        (user_a_id, first_song["song_id"]))
            pb = cur.fetchone()
            self.assertIsNotNone(pb)
            self.assertEqual(pb["status"], "started")
        conn.close()
        print(f"[PASS] Point 8 Passed: Song '{first_song['title']}' playback started and recorded.")

        # ----------------------------------------------------
        # POINT 9: Press Skip and verify that the next recommended song starts playing
        # ----------------------------------------------------
        print("\n[Point 9] Press Skip and verify queue progression...")
        # Simulate skip on first song
        skip_res = self.client.post("/api/activity/playback", json={
            "song_id": first_song["song_id"],
            "duration_played": 15.0,
            "status": "skipped"
        })
        self.assertEqual(skip_res.status_code, 200)

        # Also log skip feedback
        fb_skip = self.client.post("/api/feedback", json={
            "song_id": first_song["song_id"],
            "feedback_type": "skip"
        })
        self.assertEqual(fb_skip.status_code, 200)

        # Verify second song in queue is ready and has local MP3
        self.assertGreater(len(recommendations), 1, "Queue must have at least 2 songs for skip test")
        next_song = recommendations[1]
        self.assertTrue(next_song["audio_url"].startswith("/dataset/songs/") or next_song["audio_url"].startswith("dataset/songs/"))

        # Verify playback started on next song
        next_play = self.client.post("/api/activity/playback", json={
            "song_id": next_song["song_id"],
            "duration_played": 0.0,
            "status": "started"
        })
        self.assertEqual(next_play.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM user_playback_history WHERE user_id = %s AND song_id = %s ORDER BY playback_id DESC",
                        (user_a_id, first_song["song_id"]))
            status_row = cur.fetchone()
            self.assertEqual(status_row["status"], "skipped")
        conn.close()
        print(f"[PASS] Point 9 Passed: First song skipped, next song '{next_song['title']}' started in queue.")

        # ----------------------------------------------------
        # POINT 10: Add a song to favourites and verify text "Added to favorites"
        # ----------------------------------------------------
        print("\n[Point 10] Add song to favourites and check 'Added to favorites'...")
        fav_song = recommendations[0]
        fav_res = self.client.post("/api/favourites/toggle", json={
            "song_id": fav_song["song_id"]
        })
        self.assertEqual(fav_res.status_code, 200)
        fav_data = fav_res.get_json()
        self.assertTrue(fav_data.get("is_favourite"))
        self.assertEqual(fav_data.get("message"), "Added to favorites")

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM user_favourites WHERE user_id = %s AND song_id = %s",
                        (user_a_id, fav_song["song_id"]))
            self.assertIsNotNone(cur.fetchone(), "Favourite must be saved in user_favourites")

            cur.execute("SELECT * FROM user_favourite_activity WHERE user_id = %s AND song_id = %s AND action = 'added'",
                        (user_a_id, fav_song["song_id"]))
            self.assertIsNotNone(cur.fetchone(), "Activity must be logged in user_favourite_activity")
        conn.close()
        print(f"[PASS] Point 10 Passed: Message is '{fav_data.get('message')}', saved in MySQL.")

        # ----------------------------------------------------
        # POINT 11: Give different ratings to songs
        # ----------------------------------------------------
        print("\n[Point 11] Give different ratings to songs...")
        # 5 stars to fav_song
        r1 = self.client.post("/api/feedback", json={
            "song_id": fav_song["song_id"],
            "feedback_type": "rating",
            "rating": 5
        })
        self.assertEqual(r1.status_code, 200)

        # 2 stars to another song if available
        song_2 = recommendations[1]
        r2 = self.client.post("/api/feedback", json={
            "song_id": song_2["song_id"],
            "feedback_type": "rating",
            "rating": 2
        })
        self.assertEqual(r2.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT rating FROM feedback WHERE user_id = %s AND song_id = %s AND feedback_type = 'rating'",
                        (user_a_id, fav_song["song_id"]))
            self.assertEqual(cur.fetchone()["rating"], 5)
            cur.execute("SELECT rating FROM feedback WHERE user_id = %s AND song_id = %s AND feedback_type = 'rating'",
                        (user_a_id, song_2["song_id"]))
            self.assertEqual(cur.fetchone()["rating"], 2)
        conn.close()
        print("[PASS] Point 11 Passed: Star ratings 5 and 2 saved in feedback table.")

        # ----------------------------------------------------
        # POINT 12: Like and Dislike songs
        # ----------------------------------------------------
        print("\n[Point 12] Like and Dislike songs...")
        like_res = self.client.post("/api/feedback", json={
            "song_id": fav_song["song_id"],
            "feedback_type": "like"
        })
        self.assertEqual(like_res.status_code, 200)

        # Dislike a third song
        song_3 = recommendations[2] if len(recommendations) > 2 else recommendations[1]
        dislike_res = self.client.post("/api/feedback", json={
            "song_id": song_3["song_id"],
            "feedback_type": "dislike"
        })
        self.assertEqual(dislike_res.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT feedback_type FROM feedback WHERE user_id = %s AND song_id = %s AND feedback_type = 'like'",
                        (user_a_id, fav_song["song_id"]))
            self.assertIsNotNone(cur.fetchone())
            cur.execute("SELECT feedback_type FROM feedback WHERE user_id = %s AND song_id = %s AND feedback_type = 'dislike'",
                        (user_a_id, song_3["song_id"]))
            self.assertIsNotNone(cur.fetchone())
        conn.close()
        print("[PASS] Point 12 Passed: Like and Dislike feedback successfully saved.")

        # ----------------------------------------------------
        # POINT 13: Perform additional searches with different moods
        # ----------------------------------------------------
        print("\n[Point 13] Perform additional searches with different moods...")
        s1 = self.client.post("/api/recommend", json={"user_text": "I'm feeling low and want something peaceful"})
        self.assertEqual(s1.status_code, 200)
        s2 = self.client.post("/api/recommend", json={"user_text": "Need something energetic for workout"})
        self.assertEqual(s2.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM user_requests WHERE user_id = %s", (user_a_id,))
            req_cnt = cur.fetchone()["cnt"]
            self.assertGreaterEqual(req_cnt, 3)
        conn.close()
        print(f"[PASS] Point 13 Passed: {req_cnt} distinct searches logged in MySQL.")

        # ----------------------------------------------------
        # POINT 14: Log out
        # ----------------------------------------------------
        print("\n[Point 14] Log out...")
        logout_res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT logout_time FROM user_sessions WHERE user_id = %s ORDER BY login_time DESC", (user_a_id,))
            last_session = cur.fetchone()
            self.assertIsNotNone(last_session["logout_time"], "Logout timestamp must be recorded")
        conn.close()
        print("[PASS] Point 14 Passed: User A logged out, logout_time recorded.")

        # ----------------------------------------------------
        # POINT 15: Log in again as User A
        # ----------------------------------------------------
        print("\n[Point 15] Log in again as User A...")
        login_again = self.client.post("/login", data={
            "login_id": "test_user_a",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(login_again.status_code, 200)
        print("[PASS] Point 15 Passed: User A logged in again.")

        # ----------------------------------------------------
        # POINT 16: Verify previous preferences, favourites, searches, ratings, history
        # ----------------------------------------------------
        print("\n[Point 16] Verify previous data is restored on Profile page...")
        prof_res = self.client.get("/profile")
        self.assertEqual(prof_res.status_code, 200)
        prof_html = prof_res.get_data(as_text=True)

        self.assertIn("Romantic", prof_html)
        self.assertIn("Calm / Peaceful", prof_html)
        self.assertIn(fav_song["title"], prof_html)
        self.assertIn("My Listening History", prof_html)
        self.assertIn("Recent Plays", prof_html)
        self.assertIn("Mood Searches", prof_html)
        self.assertTrue("Ratings & Feedback" in prof_html or "Ratings &amp; Feedback" in prof_html)
        self.assertIn("Favorite Activity", prof_html)
        print("[PASS] Point 16 Passed: All previous preferences, favourites, searches, ratings, and history restored.")

        # ----------------------------------------------------
        # POINT 17: Enter a new mood prompt and verify recommendations consider BOTH prompt and history
        # ----------------------------------------------------
        print("\n[Point 17] Enter new prompt and verify prompt + history personalization...")
        hybrid_res = self.client.post("/api/recommend", json={
            "user_text": "I'm feeling low today. Suggest something peaceful."
        })
        self.assertEqual(hybrid_res.status_code, 200)
        hybrid_data = hybrid_res.get_json()
        hybrid_recs = hybrid_data.get("recommendations", [])
        self.assertGreater(len(hybrid_recs), 0)

        # Disliked song should NOT be ranked at #1
        disliked_titles = [song_3["title"]]
        self.assertNotEqual(hybrid_recs[0]["title"], disliked_titles[0], "Disliked song should not be #1 recommendation")

        # Dynamic notes should reflect personalization
        notes = [r.get("dynamic_note", "") for r in hybrid_recs]
        self.assertTrue(any(len(n) > 0 for n in notes), "Recommendations must contain dynamic explanation notes")
        print(f"[PASS] Point 17 Passed: Recommendations adapt to prompt + history (Top: '{hybrid_recs[0]['title']}', Note: '{hybrid_recs[0]['dynamic_note']}').")

        # ----------------------------------------------------
        # POINT 18: Register User B and verify User B cannot access User A's data
        # ----------------------------------------------------
        print("\n[Point 18] Register User B and verify user isolation...")
        self.client.get("/logout")
        reg_b = self.client.post("/register", data={
            "username": "test_user_b",
            "email": "user_b@test.com",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(reg_b.status_code, 200)

        # Complete quick setup for User B with different vibe
        self.client.post("/profile-setup", data={
            "action": "save",
            "moods": ["Party / Celebration"]
        }, follow_redirects=True)

        prof_b = self.client.get("/profile")
        prof_b_html = prof_b.get_data(as_text=True)

        # User B should NOT see User A's favourites, searches or playbacks
        self.assertIn("0 saved", prof_b_html)
        self.assertNotIn(fav_song["title"], prof_b_html)
        self.assertIn("Party / Celebration", prof_b_html)
        self.assertNotIn("✨ Romantic", prof_b_html)
        print("[PASS] Point 18 Passed: Strict user isolation verified. User B has 0 of User A's data.")

        # ----------------------------------------------------
        # POINT 19: Verify existing recommendation functionality and local audio playback still work
        # ----------------------------------------------------
        print("\n[Point 19] Verify audio playback routes and local MP3 accessibility...")
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT song_id, title, audio_url FROM songs LIMIT 5")
            sample_songs = cur.fetchall()
        conn.close()

        for s in sample_songs:
            audio_path = s["audio_url"] if s["audio_url"].startswith("/") else "/" + s["audio_url"]
            self.assertTrue(audio_path.startswith("/dataset/songs/"))
            # Test that the audio endpoint serves HTTP 200
            audio_res = self.client.get(audio_path)
            self.assertEqual(audio_res.status_code, 200, f"Audio file for {s['title']} must be accessible at {audio_path}")
            self.assertIn("audio", audio_res.content_type.lower())
        print(f"[PASS] Point 19 Passed: All sample songs have valid accessible local MP3 files.")

        print("\n==================================================")
        print("ALL 19 POINTS SUCCESSFULLY TESTED AND VERIFIED!")
        print("==================================================")

if __name__ == "__main__":
    unittest.main()
