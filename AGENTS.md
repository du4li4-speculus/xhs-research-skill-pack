# AGENTS.md

## Objective

Use Xiaohongshu as a research source, especially when useful information is embedded in image posts.

## Rules

- Treat `xiaohongshu-mcp` as an external dependency; do not vendor it.
- Never claim an image was read merely because an image URL was returned.
- Download note images locally and inspect them with a vision-capable model.
- Prefer native multimodal vision over OCR; use OCR only as a fallback when necessary.
- Video transcription and frame extraction are off by default.
- Preserve author, timestamp, feed_id, media type, and evidence location.
- Distinguish complete source material from recollections, fragments, and comments.
- Do not invent missing exam text.
- Keep login cookies and credentials outside the repository.
