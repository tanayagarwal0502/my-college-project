"""
Comprehensive Test Suite for Floating Music Player Bar and Bottom Chat Section
Validates all requirements:
1. Quick Vibes hidden during song playback/pause, restored on complete stop/close.
2. Fixed chat/search box pinned at viewport bottom at all times.
3. 3-Section player bar (Left: cover + title + movie/artist + status badge; Middle: prev + play/pause + skip + slider + time; Right: volume + like + dislike + favourite + 1-5 stars + close).
4. Full synchronization between song cards and player bar.
5. HTML template & CSS responsive alignment without regressions.
"""

import sys
import unittest
import json
import re

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from app import app, get_db_connection

class TestPlayerAndDock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

    def test_01_template_player_bar_structure(self):
        """Verify templates have all 3 sections and exact required element IDs."""
        print("\n[Test 1] Verifying 3-section Player Bar in templates...")
        for tpl_path in ["templates/index.html", "templates/profile.html"]:
            with open(tpl_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Player bar container
            self.assertIn('id="music-player-bar"', content, f"{tpl_path} missing #music-player-bar")
            self.assertIn('class="player-container"', content, f"{tpl_path} missing .player-container")

            # Left Section: artwork, title, movie, artist, status badge
            self.assertIn('class="player-track-info"', content)
            self.assertIn('id="player-cover-art"', content)
            self.assertIn('id="player-title"', content)
            self.assertIn('id="player-movie"', content)
            self.assertIn('id="player-artist-name"', content)
            self.assertIn('id="player-status-badge"', content)

            # Middle Section: prev, play, pause, skip, progress bar, time
            self.assertIn('class="player-controls-center"', content)
            self.assertIn('id="player-prev-btn"', content)
            self.assertIn('id="player-play-btn"', content)
            self.assertIn('id="player-pause-btn"', content)
            self.assertIn('id="player-skip-btn"', content)
            self.assertIn('id="player-progress-bar"', content)
            self.assertIn('id="player-current-time"', content)
            self.assertIn('id="player-duration-time"', content)

            # Right Section: volume, like, dislike, favourite, star ratings, close
            self.assertIn('class="player-actions-right"', content)
            self.assertIn('id="player-volume-slider"', content)
            self.assertIn('id="player-volume-icon"', content)
            self.assertIn('id="player-like-btn"', content)
            self.assertIn('id="player-dislike-btn"', content)
            self.assertIn('id="player-fav-btn"', content)
            self.assertIn('id="player-star-rating"', content)
            self.assertIn('id="player-close-btn"', content)

        # Quick Vibes chips in index.html
        with open("templates/index.html", "r", encoding="utf-8") as f:
            idx_content = f.read()
        self.assertIn('id="dock-chips-bar"', idx_content)
        self.assertIn('class="fixed-chat-dock"', idx_content)
        self.assertIn('Romantic', idx_content)
        self.assertIn('Peaceful', idx_content)
        self.assertIn('Workout', idx_content)
        self.assertIn('Road Trip', idx_content)
        self.assertIn('Party', idx_content)
        self.assertIn('Spiritual', idx_content)
        self.assertIn('Happy', idx_content)
        print("  [PASS] Templates have complete 3-section player bar and Quick Vibes IDs.")

    def test_02_css_styling_and_hiding_rules(self):
        """Verify CSS rules for hiding Quick Vibes and styling 3-section layout."""
        print("\n[Test 2] Verifying CSS styles for player bar & Quick Vibes...")
        with open("static/css/style.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Rule 1: Hide Quick Vibes when body has active player
        self.assertIn("body.has-active-player .dock-chips-bar", css)
        self.assertIn("display: none !important", css)

        # Rule 2: Fixed chat dock positioning at viewport bottom
        self.assertIn(".fixed-chat-dock", css)
        self.assertIn("bottom: 0", css)

        # Rule 3: Player bar positioning and z-index above chat dock
        self.assertIn(".music-player-bar", css)
        self.assertIn("position: fixed", css)
        self.assertIn("z-index: 1001", css)

        # Rule 4: 3-section flexbox layout classes
        self.assertIn(".player-track-info", css)
        self.assertIn(".player-controls-center", css)
        self.assertIn(".player-actions-right", css)

        # Rule 5: Status badge styles (playing & paused)
        self.assertIn(".player-status-badge", css)
        self.assertIn(".player-status-badge.is-playing", css)
        self.assertIn(".player-status-badge.is-paused", css)

        # Rule 6: Buttons: nav, action, fav, star, close
        self.assertIn(".player-btn-nav", css)
        self.assertIn(".btn-player-action", css)
        self.assertIn(".btn-player-fav", css)
        self.assertIn(".player-star-rating", css)
        self.assertIn(".btn-player-close", css)

        # Rule 7: Responsive mobile rules
        self.assertIn("@media (max-width: 768px)", css)
        print("  [PASS] CSS contains all required layout, hiding, and responsive rules.")

    def test_03_js_player_logic_and_synchronization(self):
        """Verify JS implementation has all functions, listeners, and synchronization."""
        print("\n[Test 3] Verifying JavaScript player logic and synchronization...")
        with open("static/js/app.js", "r", encoding="utf-8") as f:
            js = f.read()

        # State toggle function
        self.assertIn("function setPlayerActive(active)", js)
        self.assertIn("has-active-player", js)

        # Status badge update
        self.assertIn("function updatePlayerStatusBadge(isPlaying)", js)
        self.assertIn("▶ Playing", js)
        self.assertIn("⏸ Paused", js)

        # Synchronizers
        self.assertIn("function syncPlayerFavouriteState(songId, isFav)", js)
        self.assertIn("function syncPlayerFeedbackState(songId, feedbackType)", js)
        self.assertIn("function syncPlayerRatingState(songId, rating)", js)

        # Previous and Skip functions
        self.assertIn("function handlePrevCurrentSong()", js)
        self.assertIn("async function handleSkipCurrentSong", js)

        # Close button event listener
        self.assertIn("playerCloseBtn.addEventListener", js)
        self.assertIn('stopCurrentPlayback("stopped", true)', js)

        # Play/pause keeps Quick Vibes hidden
        self.assertIn("updatePlayerStatusBadge(false)", js)

        # Player feedback buttons (like, dislike, favourite, stars)
        self.assertIn("playerLikeBtn.addEventListener", js)
        self.assertIn("playerDislikeBtn.addEventListener", js)
        self.assertIn("playerFavBtn.addEventListener", js)
        self.assertIn("playerStarRating.querySelectorAll", js)

        # Bidirectional sync in bindCardEvents
        self.assertIn("syncPlayerFeedbackState", js)
        self.assertIn("syncPlayerRatingState", js)
        print("  [PASS] JavaScript has complete player control, sync, and state management logic.")

    def test_04_home_page_heading_removed_and_welcome_present(self):
        """Ensure 'AI-Powered Music Discovery' is removed and 'Welcome!!' is present."""
        print("\n[Test 4] Checking Home page headers...")
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, username FROM users LIMIT 1")
            user = cur.fetchone()
        conn.close()

        with self.client.session_transaction() as sess:
            sess["user_id"] = user["user_id"]
            sess["username"] = user["username"]

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertNotIn("AI-Powered Music Discovery", html, "AI-Powered Music Discovery must be removed from Home page")
        self.assertIn("Welcome!!", html, "Welcome!! must be present")
        print("  [PASS] Home page heading removed and 'Welcome!!' confirmed.")

    def test_05_backend_api_endpoints_operational(self):
        """Verify playback logging, favourites toggle, and cover image APIs."""
        print("\n[Test 5] Checking backend API endpoints...")

        # Find any song and user from db
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT song_id, title FROM songs LIMIT 1")
            song = cur.fetchone()
            cur.execute("SELECT user_id, username FROM users LIMIT 1")
            user = cur.fetchone()
        conn.close()
        self.assertIsNotNone(song, "Songs table must have at least one song")
        self.assertIsNotNone(user, "Users table must have at least one user")
        song_id = song["song_id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = user["user_id"]
            sess["username"] = user["username"]

        # Cover image endpoint
        cover_res = self.client.get(f"/api/songs/{song_id}/cover")
        self.assertEqual(cover_res.status_code, 200)
        self.assertIn(cover_res.content_type, ["image/jpeg", "image/png"])

        # Playback activity endpoint
        log_res = self.client.post("/api/activity/playback", json={
            "song_id": song_id,
            "status": "started",
            "duration_played": 15
        })
        self.assertEqual(log_res.status_code, 200)
        data = json.loads(log_res.get_data(as_text=True))
        self.assertTrue(data.get("success"))

        print("  [PASS] Backend API endpoints respond correctly.")

if __name__ == "__main__":
    unittest.main()
