## 1. Publish-result normalization

- [x] 1.1 Normalize XHS publish results in `xiaohongshu_publisher.publish_content` so success/failure, reason codes, raw result, and recovered identifiers are returned consistently.
- [x] 1.2 Propagate normalized publish metadata through AI Daily API endpoints and MCP wrappers, including `note_url`, `post_id`, and explicit publish-status fields.
- [x] 1.3 Add diagnostics or metadata needed to distinguish stale-container suspicions from real publish/login-state failures in Docker-first troubleshooting.

## 2. Ranking card and image-persistence quality

- [x] 2.1 Redesign default ranking title-card inputs so the title card acts as a cover rather than a second ranking board.
- [x] 2.2 Replace fragile temporary/shared-volume image naming in XHS upload persistence with collision-resistant filenames and verify distinct cards cannot overwrite each other.
- [x] 2.3 Add regression checks for title-vs-ranking card distinctness and publish-time image uniqueness.

## 3. Ranking copy and hashtag cleanup

- [x] 3.1 Update `_default_ranking_content` to suppress repeated title/summary pairs and handle low-signal English summaries more gracefully.
- [x] 3.2 Refactor ranking hashtag generation so the publish body uses one normalized, deduplicated hashtag source instead of mixing hard-coded body hashtags with separate tags.
- [x] 3.3 Add tests covering duplicate-summary suppression, hashtag deduplication, and cleaner mixed-language ranking output.

## 4. End-to-end verification

- [x] 4.1 Verify API and MCP ranking publish responses for the same operation and confirm they expose aligned publish-result metadata.
- [x] 4.2 Run Docker-first ranking publish validation with real generated cards to confirm distinct images are uploaded and content quality improves.
- [x] 4.3 Document any upstream limitations that remain after the local fixes, especially around missing `note_url` / `post_id` when upstream does not return them.
