-- Music Suggestion System Database Schema
CREATE DATABASE IF NOT EXISTS music_recommendation_db;
USE music_recommendation_db;

-- 1. users table
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(100) UNIQUE,
    email VARCHAR(150) UNIQUE,
    password_hash VARCHAR(255),
    profile_image VARCHAR(255) DEFAULT '/static/images/default_avatar.svg',
    profile_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. songs table
CREATE TABLE IF NOT EXISTS songs (
    song_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(150) NOT NULL,
    movie VARCHAR(150),
    artist VARCHAR(200),
    genre VARCHAR(100),
    mood VARCHAR(200),
    language VARCHAR(50),
    activity VARCHAR(200),
    description TEXT,
    audio_url VARCHAR(500),
    duration VARCHAR(20) NULL,
    cover_image MEDIUMBLOB NULL,
    cover_mime_type VARCHAR(50) DEFAULT 'image/jpeg'
);

-- 3. user_preferences table (user selected mood/vibe onboarding & profile preferences)
CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    mood_or_vibe VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 4. user_favourites table (user saved favourite songs)
CREATE TABLE IF NOT EXISTS user_favourites (
    favourite_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    song_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY user_song (user_id, song_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- 5. user_requests table
CREATE TABLE IF NOT EXISTS user_requests (
    request_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    request_text TEXT NOT NULL,
    recommendations_json TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 6. feedback table
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    song_id INT,
    feedback_type ENUM('like', 'dislike', 'skip', 'rating') NOT NULL,
    rating INT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- 7. user_profile table (aggregate profile metrics)
CREATE TABLE IF NOT EXISTS user_profile (
    profile_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE,
    preferred_moods TEXT,
    preferred_genres TEXT,
    preferred_languages TEXT,
    liked_songs TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 8. user_sessions table (login and logout tracking)
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    session_token VARCHAR(255),
    ip_address VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 9. user_playback_history table (tracks which songs were played, duration, and status)
CREATE TABLE IF NOT EXISTS user_playback_history (
    playback_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    song_id INT NOT NULL,
    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_played INT DEFAULT 0,
    status ENUM('started', 'completed', 'stopped', 'skipped') DEFAULT 'started',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- 10. user_favourite_activity table (tracks additions and removals of favorites over time)
CREATE TABLE IF NOT EXISTS user_favourite_activity (
    activity_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    song_id INT NOT NULL,
    action ENUM('added', 'removed') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- 11. recommendation_history table (tracks what recommendations were generated and their scores)
CREATE TABLE IF NOT EXISTS recommendation_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    song_id INT NOT NULL,
    recommendation_type ENUM('prompt_search', 'vibe_based', 'personalized') DEFAULT 'prompt_search',
    source_prompt TEXT NULL,
    rank_order INT NOT NULL,
    match_percentage INT NOT NULL,
    similarity_score FLOAT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

