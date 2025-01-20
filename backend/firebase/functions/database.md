# **Table Documentation**

1. **`users` Table:**
    * **Purpose:** This table stores the core user information, which is directly tied to their Firebase Authentication account.
    * **Columns:**
        * `id` (TEXT, PRIMARY KEY): The Firebase User ID (`uid`), ensuring each record is unique and directly linked to the Firebase authentication user id.
        * `email` (TEXT, UNIQUE NOT NULL): User's email address, stored for quick reference and internal processing (though it can also be retrieved from Firebase Auth); the unique constraint ensures only one record per user email.
        * `display_name` (TEXT, NULLABLE): The display name provided by the user or retrieved from Firebase Auth; allows for personalized user interfaces.
        * `created_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the user account was created, this allows for historical analysis.
        * `updated_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the user record was last updated, useful for tracking record changes and data integrity.
    * **Rationale:** Directly using the Firebase User ID (`uid`) prevents generating a new redundant id, simplifies user lookup and ensures direct relationship between the user record and its firebase auth instance.
    * **Use Case:** When a user logs in, the system uses the Firebase `uid` as a primary key, this allows for immediate retrieval of the user's profile data.

2. **`channels` Table:**
    * **Purpose:** This table stores metadata about individual YouTube channels, independent of users or collections.
    * **Columns:**
        * `youtube_channel_id` (TEXT, PRIMARY KEY): The unique YouTube channel ID, used as primary key for direct linking with data from YouTube API.
        * `title` (TEXT, NULLABLE): The title of the channel.
        * `description` (TEXT, NULLABLE): The description of the channel.
        * `channel_url` (TEXT, NULLABLE): The url of the channel in youtube.
        * `created_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the channel record was created.
    * **Rationale:** Store the essential information about YouTube channels, using its native youtube id, making the system more efficient and directly related to the YouTube data source.
    * **Use Case:** The system checks this table when a user adds channels to its collection, using the YouTube channel id to lookup the information.

3. **`sources` Table:**
    * **Purpose:** This table unifies the concept of content sources, handling both channel collections and playlists.
    * **Columns:**
        * `id` (UUID, PRIMARY KEY, DEFAULT `gen_random_uuid()`): A unique UUID for each source record, allowing for flexible management and referencing of the collection/playlist in the system.
        * `user_id` (TEXT, NOT NULL, REFERENCES `users(id)`): ID of the user who owns the source, the foreign key enforces data integrity.
        * `source_type` (TEXT, NOT NULL, CHECK `(source_type IN ('channel_collection', 'playlist'))`): Indicates whether the source is a channel collection or a playlist, with the check constraint ensuring valid values.
        * `name` (TEXT, NOT NULL): The name of the source, can be "Tech News" for a channel collection, or "My Favorite Music" for a playlist.
        * `youtube_playlist_id` (TEXT, NULLABLE): The YouTube playlist ID when the `source_type` is a playlist; this value is NULL when `source_type` is a `channel_collection`.
        * `preferences` (JSONB, NOT NULL, DEFAULT `{}`): A JSONB column to store preferences about processing (TTS voice, summarization style, schedule, etc.), enabling flexible configuration and customization of the data retrieval and podcast generation.
        * `last_processed_at` (TIMESTAMPTZ, NULLABLE): Timestamp of the last time the source was processed, useful for tracking the progress of periodic tasks.
        * `created_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the record was created.
    * **Rationale:** This table allows you to manage sources as an abstraction, handling both channel collections and playlists in a unified way. The JSONB allows for flexible preferences, and the `last_processed_at` column allows to efficiently retrieve the new videos since the last process.
    * **Use Case:** When a user adds a playlist to their system, the `source_type` is set to "playlist" and the `youtube_playlist_id` is populated. If the user adds a channel collection, `source_type` is set to "channel_collection" and `youtube_playlist_id` is NULL.

4. **`source_channels` Table:**
    * **Purpose:** This is a junction table to link channels to sources (channel collections only).
    * **Columns:**
        * `source_id` (UUID, NOT NULL, REFERENCES `sources(id)` ON DELETE CASCADE): ID of the source (channel collection), ensuring only existent sources are referenced, and that if the source is deleted, all linked channels are deleted as well.
        * `youtube_channel_id` (TEXT, NOT NULL, REFERENCES `channels(youtube_channel_id)`): The unique YouTube channel ID.
        * **PRIMARY KEY (`source_id`, `youtube_channel_id`)** This will prevent duplicates in the relation.
    * **Rationale:** Implements a many-to-many relationship between channel collections and channels, allowing a channel to belong to multiple collections.
    * **Use Case:** When a source is created and the `source_type` is `channel_collection` then multiple rows may be added to this table, creating a link between the source and all its related channels.

5. **`videos` Table:**
    * **Purpose:** Stores metadata about individual YouTube videos, independent of the user.
    * **Columns:**
        * `youtube_video_id` (TEXT, PRIMARY KEY): The unique YouTube video ID, which acts as the primary key and directly relates to data from YouTube API.
        * `title` (TEXT, NULLABLE): The title of the video.
        * `description` (TEXT, NULLABLE): The description of the video.
        * `url` (TEXT, NULLABLE): The URL of the video.
        * `channel_id` (TEXT, NOT NULL, REFERENCES `channels(youtube_channel_id)`): The unique YouTube channel id referencing the channel the video belongs to, enforcing data integrity and enabling easy lookup.
        * `uploaded_at` (TIMESTAMPTZ, NULLABLE): Timestamp of when the video was uploaded to YouTube.
        * `created_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the video entry was created in the system, providing historical information.
    * **Rationale:** Stores the base information of each video and the relation to its channel, making it independent of any user or collection/playlist.
    * **Use Case:** The system saves data in this table when a new video is discovered, from either a channel collection or a playlist.

6. **`source_videos` Table:**
    * **Purpose:** To link videos to sources and track their processing status for each specific source.
    * **Columns:**
        * `source_id` (UUID, NOT NULL, REFERENCES `sources(id)` ON DELETE CASCADE): ID of the source associated with the video, ensuring referential integrity with the sources table.
        * `youtube_video_id` (TEXT, NOT NULL, REFERENCES `videos(youtube_video_id)` ON DELETE CASCADE): ID of the video in relation with the source, ensuring data integrity.
        * `processed_at` (TIMESTAMPTZ, NULLABLE): Timestamp of when the video was processed by the source; NULL if the video has not been processed, allowing to track progress and prevent reprocessing of already consumed videos.
        * **PRIMARY KEY (`source_id`, `youtube_video_id`)**: this will prevent duplicates for videos and sources.
    * **Rationale:** Handles the many-to-many relationship between sources (channel collections or playlists) and videos. The `processed_at` field allows tracking if a video has been processed for a specific source.
    * **Use Case:** When the system creates a podcast based on the content of a source, the `processed_at` field is updated for every video used to generate such podcast. This will guarantee only videos that were not used in a previous podcast will be used in the future ones.

7. **`transcripts` Table:**
    * **Purpose:** To store the transcripts of the videos.
    * **Columns:**
        * `id` (UUID, PRIMARY KEY, DEFAULT `gen_random_uuid()`): A unique identifier for each transcript record, that guarantees uniqueness.
        * `youtube_video_id` (TEXT, NOT NULL, UNIQUE REFERENCES `videos(youtube_video_id)`): ID of the video the transcript belongs to, ensuring a one-to-one relation between videos and transcripts.
        * `text` (TEXT, NULLABLE): The full transcript text, allowing for the storage and processing of the data.
        * `source` (TEXT, NULLABLE): The source of the transcript (e.g. 'youtube_caption', 'whisper', etc.), giving context to the origin of the data.
        * `storage_url` (TEXT, NULLABLE):  The URL of the transcript file in Firebase Storage, ensuring traceability of the data in the storage.
        * `created_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the record was created.
    * **Rationale:** Store the video transcripts as text, and its reference in the cloud, with a unique constraint with the video table.
    * **Use Case:** The system creates a record in this table every time a transcript for a given video has been generated.

8. **`podcasts` Table:**
    * **Purpose:** To store information about generated podcasts.
    * **Columns:**
        * `id` (UUID, PRIMARY KEY, DEFAULT `gen_random_uuid()`): A unique id for the podcast.
        * `user_id` (TEXT, NOT NULL, REFERENCES `users(id)`): The Firebase UID, referencing the user that created the podcast.
        * `source_id` (UUID, NOT NULL, REFERENCES `sources(id)`): The id of the source the podcast was derived from, establishing a clear relation with the source of the information.
        * `transcript_id` (UUID, REFERENCES `transcripts(id)`): Optional id referencing the transcript file associated to the podcast, useful if you want to save the transcription of the podcast itself.
        * `storage_url` (TEXT, NOT NULL): The location of the final audio file in Firebase Storage.
        * `title` (TEXT, NULLABLE): The title of the podcast.
        * `created_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the record was created.
    * **Rationale:** The `podcasts` table stores metadata for each podcast and the location of the generated audio. The `source_id` field is crucial for linking a podcast to its source, and the transcript id to link the podcast with the transcript of the generated podcast.
    * **Use Case:** Every time a podcast has been created for a given source the system will generate a record in this table.

9. **`podcast_videos` Table:**
    * **Purpose:** To handle the many-to-many relationship between podcasts and videos.
    * **Columns:**
        * `podcast_id` (UUID, NOT NULL, REFERENCES `podcasts(id)` ON DELETE CASCADE): ID of the podcast, ensuring only valid podcast ids can be present.
        * `youtube_video_id` (TEXT, NOT NULL, REFERENCES `videos(youtube_video_id)`): YouTube Video ID, allowing to create a relationship between the podcast and the videos that provided its content.
    * **PRIMARY KEY (`podcast_id`, `youtube_video_id`)**:  ensures that each record is unique.
    * **Rationale:** A junction table to support the many-to-many relationship between podcasts and videos, allowing each podcast to be derived from multiple videos and each video to be part of multiple podcasts.
    * **Use Case:** The system creates a record in this table for each video used to generate a podcast.

10. **`generation_jobs` Table:**
    * **Purpose:** To track asynchronous processes in the system and provide real-time status, debugging information and transparency of long running operations.
    * **Columns:**
        * `id` (UUID, PRIMARY KEY, DEFAULT `gen_random_uuid()`): A unique UUID for the job, ensuring tracking and referencing in the system.
        * `user_id` (TEXT, NOT NULL, REFERENCES `users(id)`): The Firebase User ID, referencing the user that generated such job.
        * `source_id` (UUID, REFERENCES `sources(id)`): ID of the source related to this job, allowing to relate processing to a given source.
        * `status` (TEXT, NOT NULL): Status of the job (e.g., 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'), allows for tracking the different stages of processing.
        * `config` (JSONB, NOT NULL, DEFAULT `{}`): A JSONB to store configuration details about the job (e.g., AI model, TTS voice, etc.), allowing for full traceability.
        * `error_message` (TEXT, NULLABLE): An error message if the job failed, very useful for debugging issues.
        * `created_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the record was created.
        * `updated_at` (TIMESTAMPTZ NOT NULL, DEFAULT `now()`): Timestamp of when the record was updated, very useful for tracking progress.
        * `started_at` (TIMESTAMPTZ, NULLABLE): Timestamp when the job started, allowing for tracking duration.
        * `finished_at` (TIMESTAMPTZ, NULLABLE): Timestamp when the job finished, allowing to know if a job was completed or failed.
    * **Rationale:** Track all background processes, status, and errors, using JSONB to store runtime parameters, enabling detailed monitoring and debugging of each process.
    * **Use Case:** The system creates a record in this table before beginning any long-running task (e.g., fetching new videos, creating a podcast), this allows the user to visualize in real-time progress and to debug in case any process fails.

This detailed rationale, combined with the DDL script, provides a complete picture of the database schema's design. Each table and its columns are meticulously crafted to support the requirements of TubeXtend, emphasizing flexibility, scalability, and robust data management.
