from __future__ import annotations

# Centralized runtime tuning (edit values below)

# Rate limiting for fetching posts (requests per time window in seconds)
RATE_LIMIT_MAX_REQUESTS = 3
RATE_LIMIT_TIME_WINDOW = 60  # seconds

# Network timeouts and limits
REQUEST_TIMEOUT_SECONDS = 30
IMAGE_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

# Discord attachment limits (MB)
DISCORD_ATTACHMENT_MAX_MB = 3.0

# AJAX extraction wait before issuing fetch (milliseconds)
AJAX_WAIT_MS = 2500

# Extraction method: "ajax_json" (default) or "mobile_dom"
EXTRACTION_METHOD = "ajax_json"


