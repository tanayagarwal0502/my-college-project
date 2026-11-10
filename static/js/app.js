/**
 * Music Suggestion System - Modern Client-Side JavaScript
 * Handles:
 * - Fixed bottom chat dock submission & example chips
 * - Vertical rectangular portrait song card rendering & interactive bindings
 * - Horizontal category scroll tracks navigation
 * - Single-track audio playback with local MP3s
 * - Functional recommendation queue progression on Skip
 * - Favourite toggling with persistent "Added to favorites"
 * - 1-5 Star rating & Like/Dislike feedback
 * - Real-time activity tracking to MySQL
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements - Fixed Chat Dock & Recommendation Area
    const promptInput = document.getElementById("user-prompt-input");
    const recommendBtn = document.getElementById("recommend-btn");
    const loadingSpinner = document.getElementById("loading-spinner");
    const resultsSection = document.getElementById("recommendation-results");
    const songsContainer = document.getElementById("recommended-songs-container");
    const queryEcho = document.getElementById("recommendation-query-echo");
    const exampleChips = document.querySelectorAll(".chip, .chip-btn");

    // DOM Elements - Bottom Music Player Bar (3-Section Modern Layout)
    const playerBar = document.getElementById("music-player-bar");
    const playerCoverArt = document.getElementById("player-cover-art");
    const playerArtPlaceholder = document.getElementById("player-art-placeholder");
    const playerStatusBadge = document.getElementById("player-status-badge");
    const playerTitle = document.getElementById("player-title");
    const playerArtist = document.getElementById("player-artist");
    const playerMovie = document.getElementById("player-movie");
    const playerArtistName = document.getElementById("player-artist-name");

    const playerPrevBtn = document.getElementById("player-prev-btn");
    const playerPlayBtn = document.getElementById("player-play-btn");
    const playerPauseBtn = document.getElementById("player-pause-btn");
    const playerSkipBtn = document.getElementById("player-skip-btn");
    const playerCurrentTime = document.getElementById("player-current-time");
    const playerDurationTime = document.getElementById("player-duration-time");
    const playerProgressBar = document.getElementById("player-progress-bar");
    const playerStatusMessage = document.getElementById("player-status-message");

    const playerVolumeSlider = document.getElementById("player-volume-slider");
    const playerVolumeIcon = document.getElementById("player-volume-icon");
    const playerLikeBtn = document.getElementById("player-like-btn");
    const playerDislikeBtn = document.getElementById("player-dislike-btn");
    const playerFavBtn = document.getElementById("player-fav-btn");
    const playerStarRating = document.getElementById("player-star-rating");
    const playerCloseBtn = document.getElementById("player-close-btn");
    const dockChipsBar = document.getElementById("dock-chips-bar");
    const toast = document.getElementById("toast");

    // Audio Playback & Active Queue State
    let currentAudio = null;
    let currentSong = null;
    let currentCardPlayBtn = null;
    let isSeeking = false;
    let currentPlayerRating = null;
    let currentPlayerFeedback = null;

    // Queue Tracking for Skip / Prev Functionality
    let activeQueue = [];
    let currentSongIndex = -1;

    // Helper: format seconds to M:SS
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return "0:00";
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    }

    // Helper: log playback activity to MySQL backend
    async function logPlaybackActivity(songId, status, duration = 0) {
        if (!songId) return;
        try {
            await fetch("/api/activity/playback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    song_id: songId,
                    status: status,
                    duration_played: Math.round(duration)
                })
            });
        } catch (e) {
            console.warn("Error logging playback activity:", e);
        }
    }

    // =========================================================================
    // STATE TOGGLE: Player Bar & Quick Vibes (Requirement 1 & 5)
    // Whenever a song is playing/paused, hide Quick Vibes completely.
    // When playback stops completely or is closed, restore Quick Vibes.
    // =========================================================================
    function setPlayerActive(active) {
        if (active) {
            document.body.classList.add("has-active-player");
            if (dockChipsBar) dockChipsBar.classList.add("hidden");
            if (playerBar) playerBar.classList.remove("hidden");
        } else {
            document.body.classList.remove("has-active-player");
            if (dockChipsBar) dockChipsBar.classList.remove("hidden");
            if (playerBar) playerBar.classList.add("hidden");
            currentSong = null;
            currentPlayerRating = null;
            currentPlayerFeedback = null;
        }
    }

    // Helper: update status badge ("▶ Playing" vs "⏸ Paused")
    function updatePlayerStatusBadge(isPlaying) {
        if (!playerStatusBadge) return;
        if (isPlaying) {
            playerStatusBadge.textContent = "▶ Playing";
            playerStatusBadge.className = "player-status-badge is-playing";
        } else {
            playerStatusBadge.textContent = "⏸ Paused";
            playerStatusBadge.className = "player-status-badge is-paused";
        }
    }

    // Helper: synchronize favourite state to Player Bar
    function syncPlayerFavouriteState(songId, isFav) {
        if (!currentSong || currentSong.song_id !== parseInt(songId, 10)) return;
        currentSong.is_favourite = Boolean(isFav);
        if (playerFavBtn) {
            const icon = playerFavBtn.querySelector(".player-fav-icon");
            const text = playerFavBtn.querySelector(".player-fav-text");
            if (isFav) {
                playerFavBtn.classList.add("is-favourite");
                if (icon) icon.textContent = "❤️";
                if (text) text.textContent = "Added to favorites";
                playerFavBtn.title = "Remove from favorites";
            } else {
                playerFavBtn.classList.remove("is-favourite");
                if (icon) icon.textContent = "🤍";
                if (text) text.textContent = "Favorite";
                playerFavBtn.title = "Add to favorites";
            }
        }
    }

    // Helper: synchronize like/dislike state to Player Bar
    function syncPlayerFeedbackState(songId, feedbackType) {
        if (!currentSong || currentSong.song_id !== parseInt(songId, 10)) return;
        currentPlayerFeedback = feedbackType;
        if (playerLikeBtn && playerDislikeBtn) {
            if (feedbackType === "like") {
                playerLikeBtn.classList.add("active");
                playerDislikeBtn.classList.remove("active");
            } else if (feedbackType === "dislike") {
                playerDislikeBtn.classList.add("active");
                playerLikeBtn.classList.remove("active");
            } else {
                playerLikeBtn.classList.remove("active");
                playerDislikeBtn.classList.remove("active");
            }
        }
    }

    // Helper: synchronize star ratings to Player Bar
    function syncPlayerRatingState(songId, rating) {
        if (!currentSong || currentSong.song_id !== parseInt(songId, 10)) return;
        currentPlayerRating = rating;
        if (playerStarRating) {
            const stars = playerStarRating.querySelectorAll(".player-star-btn");
            stars.forEach(s => {
                const r = parseInt(s.getAttribute("data-rating"), 10);
                if (rating && r <= rating) {
                    s.classList.add("active");
                } else {
                    s.classList.remove("active");
                }
            });
        }
    }

    // Stop currently playing song
    function stopCurrentPlayback(logStatus = null, closePlayer = false) {
        if (currentAudio) {
            try {
                if (logStatus && currentSong) {
                    logPlaybackActivity(currentSong.song_id, logStatus, currentAudio.currentTime || 0);
                }
                currentAudio.pause();
                currentAudio.currentTime = 0;
            } catch (e) {
                console.warn("Error stopping audio:", e);
            }
            currentAudio = null;
        }

        if (currentCardPlayBtn) {
            const isFav = currentCardPlayBtn.classList.contains("btn-fav-play");
            currentCardPlayBtn.innerHTML = isFav ? '<span class="icon">▶</span> Play' : '▶';
            currentCardPlayBtn.classList.remove("is-playing");
            currentCardPlayBtn = null;
        }

        // Remove playing highlight from all song cards
        document.querySelectorAll(".song-card.current-playing-card, .favourite-card.current-playing-card").forEach(el => {
            el.classList.remove("current-playing-card");
        });

        if (playerPlayBtn && playerPauseBtn) {
            playerPlayBtn.classList.remove("hidden");
            playerPauseBtn.classList.add("hidden");
        }

        if (playerProgressBar) playerProgressBar.value = 0;
        if (playerCurrentTime) playerCurrentTime.textContent = "0:00";

        if (closePlayer) {
            setPlayerActive(false);
        }
    }

    // Play/Pause toggle for a song
    function handlePlayClick(song, cardPlayBtn, cardEl, queue = null, queueIndex = -1) {
        const errorEl = cardEl && cardEl.querySelector ? cardEl.querySelector(".audio-error-msg") : null;
        if (errorEl) errorEl.classList.add("hidden");

        const isFavBtn = cardPlayBtn && cardPlayBtn.classList.contains("btn-fav-play");
        const playHtml = isFavBtn ? '<span class="icon">▶</span> Play' : '▶';
        const pauseHtml = isFavBtn ? '<span class="icon">⏸</span> Pause' : '⏸';

        // Update active recommendation queue
        if (queue && Array.isArray(queue) && queue.length > 0) {
            activeQueue = queue;
            currentSongIndex = queueIndex >= 0 ? queueIndex : activeQueue.findIndex(s => s.song_id === song.song_id);
        }

        // If clicking the same song that is currently selected
        if (currentAudio && currentSong && currentSong.song_id === song.song_id) {
            if (currentAudio.paused) {
                currentAudio.play().then(() => {
                    cardPlayBtn.innerHTML = pauseHtml;
                    cardPlayBtn.classList.add("is-playing");
                    if (cardEl) cardEl.classList.add("current-playing-card");
                    if (playerPlayBtn) playerPlayBtn.classList.add("hidden");
                    if (playerPauseBtn) playerPauseBtn.classList.remove("hidden");
                    if (playerStatusMessage) playerStatusMessage.classList.add("hidden");
                    updatePlayerStatusBadge(true);
                    logPlaybackActivity(song.song_id, "started", currentAudio.currentTime || 0);
                }).catch(err => {
                    console.error("Audio resume error:", err);
                    showAudioError(cardEl, "Audio unavailable for this song.");
                });
            } else {
                currentAudio.pause();
                cardPlayBtn.innerHTML = playHtml;
                cardPlayBtn.classList.remove("is-playing");
                if (cardEl) cardEl.classList.remove("current-playing-card");
                if (playerPlayBtn) playerPlayBtn.classList.remove("hidden");
                if (playerPauseBtn) playerPauseBtn.classList.add("hidden");
                updatePlayerStatusBadge(false);
                // Pausing a song does NOT restore Quick Vibes (Requirement 1)
                logPlaybackActivity(song.song_id, "stopped", currentAudio.currentTime || 0);
            }
            return;
        }

        // Stop any currently playing audio (without closing the player bar)
        stopCurrentPlayback("stopped", false);

        // Verify audio URL
        if (!song.audio_url || song.audio_url.trim() === "") {
            showAudioError(cardEl, "Audio unavailable for this song.");
            return;
        }

        // Ensure root-relative URL for local MP3
        const audioSrc = song.audio_url.startsWith("/") ? song.audio_url : "/" + song.audio_url;

        // Initialize Audio instance
        currentAudio = new Audio(audioSrc);
        currentAudio.volume = parseFloat(playerVolumeSlider ? playerVolumeSlider.value : 0.8);
        currentSong = song;
        currentCardPlayBtn = cardPlayBtn;

        // Activate Player Bar and automatically hide Quick Vibes!
        setPlayerActive(true);

        if (playerBar) {
            if (playerTitle) playerTitle.textContent = song.title;
            if (playerMovie) playerMovie.textContent = song.movie || "Single";
            if (playerArtistName) playerArtistName.textContent = song.artist || "Various";
            if (playerCurrentTime) playerCurrentTime.textContent = "0:00";
            if (playerDurationTime) playerDurationTime.textContent = "0:00";
            if (playerProgressBar) playerProgressBar.value = 0;
            if (playerStatusMessage) playerStatusMessage.classList.add("hidden");
            if (playerPlayBtn) playerPlayBtn.classList.add("hidden");
            if (playerPauseBtn) playerPauseBtn.classList.remove("hidden");
            updatePlayerStatusBadge(true);

            // Update player bar cover art with official song poster
            if (playerCoverArt) {
                playerCoverArt.src = song.cover_url || `/api/songs/${song.song_id}/cover`;
                playerCoverArt.classList.remove("hidden");
                if (playerArtPlaceholder) playerArtPlaceholder.classList.add("hidden");
            }

            // Sync initial favourite state
            const isFav = Boolean(song.is_favourite || (cardEl && cardEl.querySelector(".btn-fav-heart.is-favourite")));
            syncPlayerFavouriteState(song.song_id, isFav);

            // Sync initial feedback state from card if present
            let cardFeedback = null;
            if (cardEl) {
                if (cardEl.querySelector(".btn-like.active")) cardFeedback = "like";
                else if (cardEl.querySelector(".btn-dislike.active")) cardFeedback = "dislike";
            }
            syncPlayerFeedbackState(song.song_id, cardFeedback);

            // Sync initial star rating from card if present
            let cardRating = null;
            if (cardEl) {
                const activeStars = cardEl.querySelectorAll(".star-btn.active");
                if (activeStars.length > 0) {
                    cardRating = activeStars.length;
                }
            }
            syncPlayerRatingState(song.song_id, cardRating);
        }

        // Update card button and highlight
        cardPlayBtn.innerHTML = pauseHtml;
        cardPlayBtn.classList.add("is-playing");
        if (cardEl) cardEl.classList.add("current-playing-card");

        // Event listeners on audio instance
        currentAudio.addEventListener("loadedmetadata", () => {
            if (currentAudio.duration && !isNaN(currentAudio.duration) && playerDurationTime) {
                playerDurationTime.textContent = formatTime(currentAudio.duration);
            }
        });

        currentAudio.addEventListener("timeupdate", () => {
            if (!isSeeking && currentAudio && currentAudio.duration) {
                const progress = (currentAudio.currentTime / currentAudio.duration) * 100;
                if (playerProgressBar) playerProgressBar.value = isNaN(progress) ? 0 : progress;
                if (playerCurrentTime) playerCurrentTime.textContent = formatTime(currentAudio.currentTime);
            }
        });

        currentAudio.addEventListener("ended", () => {
            logPlaybackActivity(song.song_id, "completed", currentAudio.duration || 0);
            cardPlayBtn.innerHTML = playHtml;
            cardPlayBtn.classList.remove("is-playing");
            if (cardEl) cardEl.classList.remove("current-playing-card");

            if (playerPlayBtn) playerPlayBtn.classList.remove("hidden");
            if (playerPauseBtn) playerPauseBtn.classList.add("hidden");
            if (playerProgressBar) playerProgressBar.value = 0;
            if (playerCurrentTime) playerCurrentTime.textContent = "0:00";
            updatePlayerStatusBadge(false);
            if (playerStatusMessage) {
                playerStatusMessage.textContent = "Playback ended.";
                playerStatusMessage.classList.remove("hidden");
            }
        });

        currentAudio.addEventListener("error", (e) => {
            console.error("Audio failed to load:", audioSrc, e);
            showAudioError(cardEl, "Audio unavailable for this song.");
            stopCurrentPlayback("stopped", false);
        });

        // Start playback
        currentAudio.play().then(() => {
            logPlaybackActivity(song.song_id, "started", 0);
        }).catch(err => {
            console.error("Playback start error:", err);
            showAudioError(cardEl, "Audio unavailable for this song.");
            stopCurrentPlayback("stopped", false);
        });
    }

    // Show error message on card and player
    function showAudioError(cardEl, msg) {
        const errorEl = cardEl && cardEl.querySelector ? cardEl.querySelector(".audio-error-msg") : null;
        if (errorEl) {
            errorEl.textContent = msg;
            errorEl.classList.remove("hidden");
        }
        if (playerStatusMessage) {
            playerStatusMessage.textContent = msg;
            playerStatusMessage.classList.remove("hidden");
        }
        showToast(msg);
    }

    // =========================================================================
    // FUNCTIONAL PREVIOUS BUTTON (Requirement 3 & 4)
    // If playing > 3s, restarts current song. Otherwise navigates to prev track in queue.
    // =========================================================================
    function handlePrevCurrentSong() {
        if (currentAudio && currentAudio.currentTime > 3) {
            currentAudio.currentTime = 0;
            currentAudio.play().then(() => {
                updatePlayerStatusBadge(true);
                if (playerPlayBtn) playerPlayBtn.classList.add("hidden");
                if (playerPauseBtn) playerPauseBtn.classList.remove("hidden");
            });
            showToast("⏮ Restarted current track");
            return;
        }

        if (activeQueue && activeQueue.length > 0 && currentSongIndex > 0) {
            const prevIndex = currentSongIndex - 1;
            const prevSong = activeQueue[prevIndex];

            stopCurrentPlayback("stopped", false);

            const prevCard = document.querySelector(`[data-song-id="${prevSong.song_id}"]`);
            const prevPlayBtn = prevCard ? (prevCard.querySelector(".btn-play-card") || prevCard.querySelector(".btn-fav-play")) : null;

            handlePlayClick(prevSong, prevPlayBtn || document.createElement("button"), prevCard || document.body, activeQueue, prevIndex);

            if (prevCard) {
                prevCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
            showToast(`⏮ Playing previous: "${prevSong.title}"`);
        } else if (currentAudio) {
            currentAudio.currentTime = 0;
            currentAudio.play().then(() => {
                updatePlayerStatusBadge(true);
                if (playerPlayBtn) playerPlayBtn.classList.add("hidden");
                if (playerPauseBtn) playerPauseBtn.classList.remove("hidden");
            });
            showToast("⏮ Beginning of queue; restarted track");
        } else {
            showToast("No active track to play.");
        }
    }

    // =========================================================================
    // FUNCTIONAL SKIP BUTTON (Requirement 3 & 4)
    // Moves playback to the next song in the active queue
    // =========================================================================
    async function handleSkipCurrentSong(sourceSongId = null) {
        // 1. Record skip in MySQL activity
        const songToSkip = currentSong || (activeQueue.length > 0 && currentSongIndex >= 0 ? activeQueue[currentSongIndex] : null);
        const skipSongId = sourceSongId || (songToSkip ? songToSkip.song_id : null);

        if (skipSongId) {
            submitFeedback(skipSongId, "skip", null, null);
            logPlaybackActivity(skipSongId, "skipped", currentAudio ? currentAudio.currentTime : 0);
        }

        // 2. Validate active queue
        if (!activeQueue || activeQueue.length === 0) {
            showToast("No active recommendation queue to skip.");
            return;
        }

        // 3. Move to next song in the active recommendation queue
        const nextIndex = currentSongIndex + 1;

        if (nextIndex < activeQueue.length) {
            const nextSong = activeQueue[nextIndex];

            // Stop current song
            stopCurrentPlayback("skipped", false);

            // Locate next song elements on page if rendered
            const nextCard = document.querySelector(`[data-song-id="${nextSong.song_id}"]`);
            const nextPlayBtn = nextCard ? (nextCard.querySelector(".btn-play-card") || nextCard.querySelector(".btn-fav-play")) : null;

            // Automatically start playing next song in queue
            handlePlayClick(nextSong, nextPlayBtn || document.createElement("button"), nextCard || document.body, activeQueue, nextIndex);

            if (nextCard) {
                nextCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }

            showToast(`⏭ Skipped to: "${nextSong.title}"`);
        } else {
            // Reached the end of recommendations
            stopCurrentPlayback("stopped", false);
            const endMsg = "You've reached the end of your recommendations.";
            if (playerStatusMessage) {
                playerStatusMessage.textContent = endMsg;
                playerStatusMessage.classList.remove("hidden");
            }
            showToast(endMsg);
        }
    }

    // =========================================================================
    // WIRE PLAYER BAR CONTROLS (Prev, Play, Pause, Skip, Close, Like, Fav, Stars)
    // =========================================================================
    if (playerPrevBtn) {
        playerPrevBtn.addEventListener("click", () => {
            handlePrevCurrentSong();
        });
    }

    if (playerPlayBtn) {
        playerPlayBtn.addEventListener("click", () => {
            if (currentAudio && currentAudio.paused) {
                currentAudio.play().then(() => {
                    playerPlayBtn.classList.add("hidden");
                    playerPauseBtn.classList.remove("hidden");
                    updatePlayerStatusBadge(true);
                    if (currentCardPlayBtn) {
                        const isFav = currentCardPlayBtn.classList.contains("btn-fav-play");
                        currentCardPlayBtn.innerHTML = isFav ? '<span class="icon">⏸</span> Pause' : '⏸';
                        currentCardPlayBtn.classList.add("is-playing");
                    }
                    if (playerStatusMessage) playerStatusMessage.classList.add("hidden");
                });
            }
        });
    }

    if (playerPauseBtn) {
        playerPauseBtn.addEventListener("click", () => {
            if (currentAudio && !currentAudio.paused) {
                currentAudio.pause();
                playerPlayBtn.classList.remove("hidden");
                playerPauseBtn.classList.add("hidden");
                updatePlayerStatusBadge(false);
                // Pausing does NOT restore Quick Vibes (Requirement 1)
                if (currentCardPlayBtn) {
                    const isFav = currentCardPlayBtn.classList.contains("btn-fav-play");
                    currentCardPlayBtn.innerHTML = isFav ? '<span class="icon">▶</span> Play' : '▶';
                    currentCardPlayBtn.classList.remove("is-playing");
                }
            }
        });
    }

    if (playerSkipBtn) {
        playerSkipBtn.addEventListener("click", () => {
            handleSkipCurrentSong();
        });
    }

    if (playerCloseBtn) {
        playerCloseBtn.addEventListener("click", () => {
            // Completely stops playback and restores Quick Vibes (Requirement 1 & 4)
            stopCurrentPlayback("stopped", true);
            showToast("Player closed. Quick Vibes restored.");
        });
    }

    if (playerLikeBtn) {
        playerLikeBtn.addEventListener("click", async () => {
            if (!currentSong) return;
            const newFeedback = playerLikeBtn.classList.contains("active") ? null : "like";
            syncPlayerFeedbackState(currentSong.song_id, newFeedback);

            // Sync to any matching card on page
            document.querySelectorAll(`[data-song-id="${currentSong.song_id}"]`).forEach(c => {
                const lBtn = c.querySelector(".btn-like");
                const dBtn = c.querySelector(".btn-dislike");
                if (lBtn && dBtn) {
                    if (newFeedback === "like") {
                        lBtn.classList.add("active");
                        dBtn.classList.remove("active");
                    } else {
                        lBtn.classList.remove("active");
                    }
                }
            });

            await submitFeedback(currentSong.song_id, newFeedback || "neutral", currentPlayerRating, null);
        });
    }

    if (playerDislikeBtn) {
        playerDislikeBtn.addEventListener("click", async () => {
            if (!currentSong) return;
            const newFeedback = playerDislikeBtn.classList.contains("active") ? null : "dislike";
            syncPlayerFeedbackState(currentSong.song_id, newFeedback);

            // Sync to any matching card on page
            document.querySelectorAll(`[data-song-id="${currentSong.song_id}"]`).forEach(c => {
                const lBtn = c.querySelector(".btn-like");
                const dBtn = c.querySelector(".btn-dislike");
                if (lBtn && dBtn) {
                    if (newFeedback === "dislike") {
                        dBtn.classList.add("active");
                        lBtn.classList.remove("active");
                    } else {
                        dBtn.classList.remove("active");
                    }
                }
            });

            await submitFeedback(currentSong.song_id, newFeedback || "neutral", currentPlayerRating, null);
        });
    }

    if (playerFavBtn) {
        playerFavBtn.addEventListener("click", async () => {
            if (!currentSong) return;
            await toggleFavouriteSong(currentSong.song_id, playerFavBtn);
        });
    }

    if (playerStarRating) {
        playerStarRating.querySelectorAll(".player-star-btn").forEach(star => {
            star.addEventListener("click", async () => {
                if (!currentSong) return;
                const rating = parseInt(star.getAttribute("data-rating"), 10);
                syncPlayerRatingState(currentSong.song_id, rating);

                // Sync star rating to matching cards on page
                document.querySelectorAll(`[data-song-id="${currentSong.song_id}"]`).forEach(c => {
                    const cardStars = c.querySelectorAll(".star-btn");
                    cardStars.forEach(s => {
                        const r = parseInt(s.getAttribute("data-rating"), 10);
                        if (r <= rating) s.classList.add("active");
                        else s.classList.remove("active");
                    });
                });

                // Auto sync like/dislike based on star rating (1-2: dislike, 3-5: like)
                const feedbackType = rating <= 2 ? "dislike" : "like";
                syncPlayerFeedbackState(currentSong.song_id, feedbackType);
                document.querySelectorAll(`[data-song-id="${currentSong.song_id}"]`).forEach(c => {
                    const lBtn = c.querySelector(".btn-like");
                    const dBtn = c.querySelector(".btn-dislike");
                    if (lBtn && dBtn) {
                        if (feedbackType === "like") {
                            lBtn.classList.add("active");
                            dBtn.classList.remove("active");
                        } else {
                            dBtn.classList.add("active");
                            lBtn.classList.remove("active");
                        }
                    }
                });

                await submitFeedback(currentSong.song_id, feedbackType, rating, null);
            });
        });
    }

    if (playerProgressBar) {
        playerProgressBar.addEventListener("input", () => {
            isSeeking = true;
            if (currentAudio && currentAudio.duration) {
                const targetTime = (playerProgressBar.value / 100) * currentAudio.duration;
                if (playerCurrentTime) playerCurrentTime.textContent = formatTime(targetTime);
            }
        });

        playerProgressBar.addEventListener("change", () => {
            if (currentAudio && currentAudio.duration) {
                const targetTime = (playerProgressBar.value / 100) * currentAudio.duration;
                currentAudio.currentTime = targetTime;
            }
            isSeeking = false;
        });
    }

    if (playerVolumeSlider) {
        playerVolumeSlider.addEventListener("input", () => {
            const vol = parseFloat(playerVolumeSlider.value);
            if (currentAudio) {
                currentAudio.volume = vol;
            }
            if (playerVolumeIcon) {
                if (vol === 0) {
                    playerVolumeIcon.textContent = "🔇";
                } else if (vol < 0.5) {
                    playerVolumeIcon.textContent = "🔉";
                } else {
                    playerVolumeIcon.textContent = "🔊";
                }
            }
        });
    }

    // =========================================================================
    // FAVOURITE TOGGLE WITH "Added to favorites" (Requirement 2 & 4)
    // Synchronizes across all song cards and the player bar simultaneously
    // =========================================================================
    async function toggleFavouriteSong(songId, favBtn) {
        try {
            const res = await fetch("/api/favourites/toggle", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ song_id: parseInt(songId, 10) })
            });
            const data = await res.json();
            if (data.success) {
                // Update all song cards for this songId on the page
                document.querySelectorAll(`.btn-fav-heart[data-song-id="${songId}"]`).forEach(btn => {
                    const icon = btn.querySelector(".heart-icon");
                    const text = btn.querySelector(".heart-text");

                    if (data.is_favourite) {
                        btn.classList.add("is-favourite");
                        if (icon) icon.textContent = "❤️";
                        if (text) text.textContent = "Added to favorites";
                        btn.title = "Remove from favorites";
                    } else {
                        btn.classList.remove("is-favourite");
                        if (icon) icon.textContent = "🤍";
                        if (text) text.textContent = "Favorite";
                        btn.title = "Add to favorites";
                    }
                });

                // Synchronize Player Bar favourite button if this is the currently playing song
                syncPlayerFavouriteState(songId, data.is_favourite);

                if (data.is_favourite) {
                    showToast("Added to favorites");
                } else {
                    showToast("Removed from favorites");
                }
            } else {
                showToast(data.error || "Could not update favorites.");
            }
        } catch (e) {
            console.error("Favourite toggle error:", e);
            showToast("Error updating favorites.");
        }
    }

    // =========================================================================
    // CARD ACTION BINDING (Search Results & Static Category Rows)
    // Synchronizes with the Player Bar in real-time
    // =========================================================================
    function bindCardEvents(card, song, queue, queueIndex) {
        // Play Button
        const playBtn = card.querySelector(".btn-play-card") || card.querySelector(".btn-fav-play");
        if (playBtn) {
            playBtn.addEventListener("click", () => {
                handlePlayClick(song, playBtn, card, queue, queueIndex);
            });
        }

        // Skip Button on Card
        const skipBtn = card.querySelector(".btn-skip");
        if (skipBtn) {
            skipBtn.addEventListener("click", () => {
                handleSkipCurrentSong(song.song_id);
            });
        }

        // Favourite Button on Card
        const favBtn = card.querySelector(".btn-fav-heart");
        if (favBtn) {
            favBtn.addEventListener("click", () => {
                toggleFavouriteSong(song.song_id, favBtn);
            });
        }

        // Like / Dislike / Rating Feedback
        const likeBtn = card.querySelector(".btn-like");
        const dislikeBtn = card.querySelector(".btn-dislike");
        const starBtns = card.querySelectorAll(".star-btn");
        const statusEl = card.querySelector(".feedback-status");

        let currentRating = null;

        if (likeBtn) {
            likeBtn.addEventListener("click", async () => {
                if (dislikeBtn) dislikeBtn.classList.remove("active");
                likeBtn.classList.add("active");
                if (currentSong && currentSong.song_id === song.song_id) {
                    syncPlayerFeedbackState(song.song_id, "like");
                }
                await submitFeedback(song.song_id, "like", currentRating, statusEl);
            });
        }

        if (dislikeBtn) {
            dislikeBtn.addEventListener("click", async () => {
                if (likeBtn) likeBtn.classList.remove("active");
                dislikeBtn.classList.add("active");
                if (currentSong && currentSong.song_id === song.song_id) {
                    syncPlayerFeedbackState(song.song_id, "dislike");
                }
                await submitFeedback(song.song_id, "dislike", currentRating, statusEl);
            });
        }

        if (starBtns && starBtns.length > 0) {
            starBtns.forEach(star => {
                star.addEventListener("click", async () => {
                    const rating = parseInt(star.getAttribute("data-rating"), 10);
                    currentRating = rating;

                    starBtns.forEach(s => {
                        const r = parseInt(s.getAttribute("data-rating"), 10);
                        if (r <= rating) {
                            s.classList.add("active");
                        } else {
                            s.classList.remove("active");
                        }
                    });

                    const feedbackType = rating <= 2 ? "dislike" : "like";
                    if (likeBtn && dislikeBtn) {
                        if (feedbackType === "like") {
                            likeBtn.classList.add("active");
                            dislikeBtn.classList.remove("active");
                        } else {
                            dislikeBtn.classList.add("active");
                            likeBtn.classList.remove("active");
                        }
                    }

                    if (currentSong && currentSong.song_id === song.song_id) {
                        syncPlayerRatingState(song.song_id, rating);
                        syncPlayerFeedbackState(song.song_id, feedbackType);
                    }

                    await submitFeedback(song.song_id, feedbackType, currentRating, statusEl);
                });
            });
        }
    }

    // Helper: Initialize category row of cards
    function initCategoryRow(containerSelector, queueType) {
        const container = document.querySelector(containerSelector);
        if (!container) return;
        const cards = Array.from(container.querySelectorAll(".song-card, .favourite-card"));
        if (!cards || cards.length === 0) return;

        const queue = cards.map(c => {
            const btn = c.querySelector(".btn-play-card") || c.querySelector(".btn-fav-play");
            return {
                song_id: parseInt(c.getAttribute("data-song-id"), 10),
                title: btn ? btn.getAttribute("data-title") : "",
                artist: btn ? btn.getAttribute("data-artist") : "",
                movie: btn ? btn.getAttribute("data-movie") : "",
                audio_url: btn ? btn.getAttribute("data-audio-url") : ""
            };
        });

        cards.forEach((c, idx) => {
            bindCardEvents(c, queue[idx], queue, idx);
        });
    }

    // Initialize all pre-rendered horizontal category rows
    initCategoryRow("#vibe-songs-container", "vibe");
    initCategoryRow("#personalized-songs-container", "personalized");
    initCategoryRow("#romantic-songs-container", "romantic");
    initCategoryRow("#energetic-songs-container", "energetic");
    initCategoryRow("#calm-songs-container", "calm");
    initCategoryRow("#favourites-list", "favourites");

    // Horizontal Row Navigation Buttons (◀ / ▶)
    document.querySelectorAll(".btn-row-scroll").forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const dir = parseInt(btn.getAttribute("data-dir") || "1", 10);
            const container = document.getElementById(targetId);
            if (container) {
                container.scrollBy({ left: dir * 560, behavior: "smooth" });
            }
        });
    });

    // 1. Example Prompts Click Handling
    if (exampleChips && exampleChips.length > 0) {
        exampleChips.forEach(chip => {
            chip.addEventListener("click", () => {
                const promptText = chip.getAttribute("data-prompt");
                if (promptText && promptInput) {
                    promptInput.value = promptText;
                    promptInput.focus();
                }
            });
        });
    }

    // Keyboard support: Enter in bottom prompt input triggers recommendation
    if (promptInput && recommendBtn) {
        promptInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                recommendBtn.click();
            }
        });
    }

    // 2. Recommend Songs Button Click (Fixed Bottom Dock)
    if (recommendBtn) {
        recommendBtn.addEventListener("click", async () => {
            const text = promptInput ? promptInput.value.trim() : "";
            if (!text) {
                showToast("Please enter how you are feeling or what music you want.");
                if (promptInput) promptInput.focus();
                return;
            }

            stopCurrentPlayback("stopped");

            recommendBtn.disabled = true;
            if (loadingSpinner) loadingSpinner.classList.remove("hidden");
            if (resultsSection) resultsSection.classList.add("hidden");
            if (songsContainer) songsContainer.innerHTML = "";

            try {
                const response = await fetch("/api/recommend", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ request_text: text })
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || "Failed to generate recommendations.");
                }

                renderRecommendations(data.recommendations, text);
            } catch (error) {
                console.error("Recommendation Error:", error);
                showToast("Error: " + error.message);
            } finally {
                recommendBtn.disabled = false;
                if (loadingSpinner) loadingSpinner.classList.add("hidden");
            }
        });
    }

    // 3. Render Top Recommendations as Vertical Rectangular Cards
    function renderRecommendations(songs, queryText) {
        if (!songsContainer || !resultsSection) return;

        if (!songs || songs.length === 0) {
            songsContainer.innerHTML = `<div class="empty-state" style="padding: 2rem; color: var(--text-muted);">No songs matched your request. Please try another prompt.</div>`;
            resultsSection.classList.remove("hidden");
            return;
        }

        if (queryEcho) queryEcho.textContent = `Tailored for: "${queryText}"`;
        songsContainer.innerHTML = "";

        // Make the newly recommended songs the activeQueue
        activeQueue = songs;
        currentSongIndex = -1;

        songs.forEach((song, idx) => {
            const card = createSongCard(song, songs, idx);
            songsContainer.appendChild(card);
        });

        resultsSection.classList.remove("hidden");
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // 4. Construct Vertical Rectangular Song Card Component (Requirement 4)
    function createSongCard(song, queue, queueIndex) {
        const card = document.createElement("div");
        card.className = "song-card search-result-card";
        card.setAttribute("data-song-id", song.song_id);

        const isFav = Boolean(song.is_favourite);
        const coverSrc = song.cover_url || `/api/songs/${song.song_id}/cover`;

        card.innerHTML = `
            <div class="card-artwork-box">
                <img 
                    src="${coverSrc}" 
                    alt="${escapeHtml(song.title)} Poster" 
                    class="card-poster-img"
                    loading="lazy"
                    onerror="this.style.display='none'"
                >
                <div class="card-poster-overlay"></div>
                <span class="card-match-pill">✨ ${song.match_percentage || 95}% Match</span>
                <button class="btn-play-card" 
                    data-song-id="${song.song_id}" 
                    data-title="${escapeHtml(song.title)}" 
                    data-artist="${escapeHtml(song.artist || "")}" 
                    data-movie="${escapeHtml(song.movie || "")}" 
                    data-audio-url="${song.audio_url || ""}" 
                    title="Play ${escapeHtml(song.title)}">
                    ▶
                </button>
            </div>

            <div class="card-body">
                <div class="card-title-group">
                    <h3 class="song-card-title">${escapeHtml(song.title)}</h3>
                    <p class="song-card-meta">
                        <span class="movie-name">${escapeHtml(song.movie || "Single")}</span> • ${escapeHtml(song.artist || "Various")}
                    </p>
                </div>

                <div class="card-tags">
                    ${song.genre ? `<span class="tag tag-genre">${escapeHtml(song.genre)}</span>` : ""}
                    ${song.mood ? `<span class="tag tag-mood">${escapeHtml(song.mood)}</span>` : ""}
                </div>

                ${song.dynamic_note ? `<div class="dynamic-note">"${escapeHtml(song.dynamic_note)}"</div>` : ""}

                <div class="card-footer">
                    <div class="card-actions-row">
                        <button class="btn-feedback btn-like" title="Like">👍 Like</button>
                        <button class="btn-feedback btn-dislike" title="Dislike">👎 Dislike</button>
                        <button class="btn-feedback btn-skip" title="Skip to next song">⏭ Skip</button>
                    </div>

                    <button class="btn-fav-heart ${isFav ? 'is-favourite' : ''}" 
                        data-song-id="${song.song_id}" 
                        title="${isFav ? 'Remove from favorites' : 'Add to favorites'}">
                        <span class="heart-icon">${isFav ? '❤️' : '🤍'}</span>
                        <span class="heart-text">${isFav ? 'Added to favorites' : 'Favorite'}</span>
                    </button>

                    <div class="star-rating-row">
                        <span class="rating-label">Rate:</span>
                        <div class="star-rating">
                            <button class="star-btn" data-rating="1" title="1 Star">★</button>
                            <button class="star-btn" data-rating="2" title="2 Stars">★</button>
                            <button class="star-btn" data-rating="3" title="3 Stars">★</button>
                            <button class="star-btn" data-rating="4" title="4 Stars">★</button>
                            <button class="star-btn" data-rating="5" title="5 Stars">★</button>
                        </div>
                    </div>

                    <div class="audio-error-msg hidden">Audio unavailable for this song.</div>
                    <div class="feedback-status hidden"></div>
                </div>
            </div>
        `;

        bindCardEvents(card, song, queue, queueIndex);
        return card;
    }

    // Submit Feedback API Call
    async function submitFeedback(songId, feedbackType, rating, statusEl) {
        try {
            const response = await fetch("/api/feedback", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    song_id: songId,
                    feedback_type: feedbackType,
                    rating: rating
                })
            });

            const data = await response.json();

            if (data.success) {
                if (statusEl) {
                    statusEl.textContent = "Feedback recorded.";
                    statusEl.classList.remove("hidden");
                }
                if (feedbackType !== "skip") {
                    showToast("Feedback saved.");
                }
            } else {
                showToast("Error: " + (data.error || "Failed to save feedback."));
            }
        } catch (error) {
            console.error("Feedback submission error:", error);
            showToast("Failed to save feedback.");
        }
    }

    // Toast Notification Helper
    let toastTimeout = null;
    function showToast(message) {
        if (!toast) return;
        if (toastTimeout) {
            clearTimeout(toastTimeout);
        }
        toast.textContent = message;
        toast.classList.remove("hidden");

        toastTimeout = setTimeout(() => {
            toast.classList.add("hidden");
        }, 3000);
    }

    // Utility: Escape HTML
    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
