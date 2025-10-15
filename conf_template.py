# Configuration Template for Handshake automation
# Copy this file to conf.py and fill in your actual values
# This file contains all configuration settings for the job application bot

# Whether the configuration is valid and ready to use
# Set to True once you've filled in all required values
VALID = True

# Search URL with filters (will be sanitized)
# Replace YOUR_SEARCH_ID with your actual Handshake search URL
URL = "https://app.joinhandshake.com/job-search/YOUR_SEARCH_ID"

# Document IDs for application - REQUIRED
# You can find these IDs by inspecting your uploaded documents in Handshake
RESUME = 12345678        # Your resume document ID
COVER = 12345679         # Your cover letter document ID
TRANSCRIPT = 12345680    # Your transcript document ID
OTHER = None             # Optional other document ID

# Last run date (ISO format) - will be updated automatically
# Leave as "0" for first run
DATE = "0"

# Job keywords to look for (currently not used in code but reserved for future features)
JOB_KEYWORDS = [
    "data analyst",
    "data engineer",
    "business analyst",
    "analytics",
    "data science"
]

# Keywords to skip jobs with (currently not used in code but reserved for future features)
SKIP_KEYWORDS = [
    "physical therapist",
    "medical",
    "clinical",
    "nurse"
]

# Session cookies - REQUIRED for authentication
# You must obtain these cookies from your browser after logging into Handshake
# Use browser developer tools (F12) -> Network tab -> find requests to handshake
COOKIES = {
    "_trajectory_session": "YOUR_SESSION_COOKIE_HERE",
    "production_current_user": "YOUR_USER_ID",
    "hss-global": "YOUR_HSS_GLOBAL_COOKIE",
    "ajs_user_id": "YOUR_USER_ID",
    "_ga": "YOUR_GA_COOKIE",
    "__cf_bm": "YOUR_CLOUDFLARE_COOKIE"
}
