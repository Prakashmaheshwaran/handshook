# Handshook - Handshake Job Application Bot

A Python bot that automatically applies to jobs on Handshake. It works with both saved HTML job searches and live API queries.

## What It Does

1. **Finds Jobs**: Either from HTML files you save or by searching Handshake directly
2. **Filters Jobs**: Uses your keywords to find relevant positions
3. **Applies Automatically**: Submits applications with your resume, cover letter, and transcript
4. **Tracks Progress**: Saves applied jobs to avoid duplicates

## Quick Setup

### 1. Install Dependencies
```bash
pip3 install requests
```

### 2. Configure Your Settings

Copy `conf_template.json` to `conf.json` and fill in:

- **Document IDs**: Get from Handshake → Documents → Click each document → Copy ID from URL
- **Cookies**: Press F12 → Storage/Application tab → Copy cookies from `.joinhandshake.com`
- **Keywords**: Add job titles you want (optional)

### 3. Run the Bot
```bash
python3 handshake.py
```

## Two Ways to Use

### Option 1: Save HTML Jobs (Recommended for Specific Jobs)
1. Go to Handshake job search
2. Right-click → "Save Page As" → Save to `html/` folder
3. Run `python3 handshake.py`
4. Bot automatically extracts and applies to those jobs

### Option 2: Automatic Search (Bulk Applications)
1. Just run `python3 handshake.py`
2. Bot searches Handshake using your keyword filters
3. Applies to matching jobs automatically

## Files

- `conf.json` - Your personal configuration (cookies, document IDs, keywords)
- `conf_template.json` - Example configuration file
- `jobs.csv` - History of all applied jobs
- `new_jobs.csv` - Jobs extracted from HTML (auto-generated, auto-cleaned)
- `wait.json` - Jobs not yet open (will retry later)
- `html/` - Folder for saved HTML files (auto-cleaned after processing)

## Important Notes

- **Cookies expire** every few days - update them when you see authentication errors
- Only applies to jobs requiring resume, cover letter, or transcript
- Skips external application jobs automatically
- Run regularly to catch new postings (or set up a cron job)

## Troubleshooting

- **"Cookies not valid"** → Update cookies in `conf.json`
- **403 errors** → Normal, means you don't qualify for that job
- **No jobs applied** → Check your document IDs are correct

Happy job hunting! 🎯
