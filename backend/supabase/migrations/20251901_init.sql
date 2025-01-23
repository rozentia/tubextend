-- Drop tables if they exist to start fresh
DROP TABLE IF EXISTS podcast_videos;
DROP TABLE IF EXISTS generation_jobs;
DROP TABLE IF EXISTS podcasts;
DROP TABLE IF EXISTS transcripts;
DROP TABLE IF EXISTS source_videos;
DROP TABLE IF EXISTS source_channels;
DROP TABLE IF EXISTS videos;
DROP TABLE IF EXISTS channels;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS users;


--- 1. Users Table
CREATE TABLE users (
  id               TEXT PRIMARY KEY,  -- Firebase UID
  email            TEXT UNIQUE NOT NULL,
  display_name     TEXT,
  refresh_token    TEXT,              -- YouTube OAuth refresh token
  token_expires_at TIMESTAMPTZ,       -- Token expiration timestamp
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index example (Supabase automatically indexes PK)
CREATE INDEX ON users (email);

--- 2. Channels Table
CREATE TABLE channels (
  youtube_channel_id   TEXT PRIMARY KEY,
  title                TEXT,
  description          TEXT,
  channel_url          TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON channels (title);

--- 3. Sources Table (Unifying Channel Collections & Playlists)
CREATE TABLE sources (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             TEXT NOT NULL REFERENCES users(id),
  source_type         TEXT NOT NULL CHECK (source_type IN ('channel_collection', 'playlist')),
  name                TEXT NOT NULL,               -- e.g. "Stoicism Practices" or "Favorite Playlist"
  youtube_playlist_id TEXT,                        -- Null if channel_collection, populated if playlist
  preferences         JSONB NOT NULL DEFAULT '{}', -- TTS voice, summarization style, schedule, etc.
  last_processed_at   TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON sources (user_id);
CREATE INDEX ON sources (source_type);

--- 4. Source Channels Table (Linking Channels to Source for Channel Collections)
CREATE TABLE source_channels (
  source_id          UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  youtube_channel_id TEXT NOT NULL REFERENCES channels(youtube_channel_id),
  PRIMARY KEY (source_id, youtube_channel_id)
);

CREATE INDEX ON source_channels (source_id);
CREATE INDEX ON source_channels (youtube_channel_id);

--- 5. Videos Table
CREATE TABLE videos (
  youtube_video_id  TEXT PRIMARY KEY,
  title             TEXT,
  description       TEXT,
  url               TEXT,
  channel_id        TEXT NOT NULL REFERENCES channels(youtube_channel_id),  -- So we know which channel
  uploaded_at       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON videos (channel_id);
CREATE INDEX ON videos (uploaded_at);

--- 6. Source Videos Table (Linking Videos to Source - Marking Processed Status)
CREATE TABLE source_videos (
  source_id        UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  youtube_video_id TEXT NOT NULL REFERENCES videos(youtube_video_id) ON DELETE CASCADE,
  processed_at     TIMESTAMPTZ,  -- NULL if unprocessed, or the exact time it was processed
  PRIMARY KEY (source_id, youtube_video_id)
);

CREATE INDEX ON source_videos (source_id);
CREATE INDEX ON source_videos (youtube_video_id);
CREATE INDEX ON source_videos (processed_at);

--- 7. Transcripts Table
CREATE TABLE transcripts (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  youtube_video_id TEXT NOT NULL REFERENCES videos(youtube_video_id) UNIQUE,
  text             TEXT,        -- Full transcript text
  source           TEXT,        -- e.g. 'youtube_caption', 'whisper', etc.
  storage_url      TEXT,        -- Where the transcript file is stored
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

--- 8. Podcasts Table
CREATE TABLE podcasts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         TEXT NOT NULL REFERENCES users(id),
  source_id       UUID NOT NULL REFERENCES sources(id),    -- The collection or playlist from which content was derived
  transcript_id   UUID REFERENCES transcripts(id),         -- Transcript for the entire generated podcast (optional)
  storage_url     TEXT,                                    -- The location of the final audio
  title           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON podcasts (source_id);
CREATE INDEX ON podcasts (user_id);

--- 9. Podcast Videos Table (Linking Podcasts to Videos)
CREATE TABLE podcast_videos (
  podcast_id       UUID NOT NULL REFERENCES podcasts(id) ON DELETE CASCADE,
  youtube_video_id TEXT NOT NULL REFERENCES videos(youtube_video_id),
  PRIMARY KEY (podcast_id, youtube_video_id)
);

CREATE INDEX ON podcast_videos (podcast_id);
CREATE INDEX ON podcast_videos (youtube_video_id);

--- 10. Generation Jobs Table (Optional but Highly Recommended)
CREATE TABLE generation_jobs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       TEXT NOT NULL REFERENCES users(id),
  source_id     UUID REFERENCES sources(id),
  status        TEXT NOT NULL,  -- e.g. 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'
  config        JSONB NOT NULL DEFAULT '{}',
  error_message TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ
);

CREATE INDEX ON generation_jobs (user_id);
CREATE INDEX ON generation_jobs (source_id);
CREATE INDEX ON generation_jobs (status);