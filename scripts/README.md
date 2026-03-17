# Morning Brief Agent

Daily intelligence digest for ML research, jobs, weather, financial/political news, and sports.

## Features

### 📄 Research Scan
- **RSS Feeds:** Google AI Blog, Anthropic, Meta AI, Databricks, Chip Huyen, The Batch, Import AI, OpenAI, Hugging Face
- **arXiv Papers:** cs.LG, cs.DC, cs.DB, cs.PF (last 24 hours)
- **Hacker News:** Front page AI/ML stories
- **Keywords:** MLOps, distributed training, inference serving, feature store, data pipeline, systems ML, CUDA, PyTorch

### 💼 Job Scan
Companies monitored:
- Google, Meta, Anthropic, Databricks, NVIDIA
- Scale AI, Anyscale, Modal
- Edge Case Research, M Science, MERL

### 🌤️ Weather
- Pittsburgh forecast (high/low, conditions, precipitation)
- Clothing recommendation based on temperature

### 💰 Financial News
- Tech stocks and market movers
- VC funding rounds
- Fed announcements and macro trends

### 🗳️ Political News
- Tech policy and AI regulation
- Politico, Reuters, AP feeds

### 🏈 NFL
- Major updates (playoff results, trades, injuries)

## Output

1. **HTML Email** → marcus.agent.joshua@gmail.com
2. **Discord Notification** → Summary via webhook

## Schedule

Runs daily at **11:30 UTC (6:30 AM ET)** via GitHub Actions.

## Setup

### Required GitHub Secrets
- `OPENROUTER_API_KEY` - For Claude Haiku summarization
- `AGENT_EMAIL` - marcus.agent.joshua@gmail.com
- `AGENT_EMAIL_APP_PASSWORD` - Gmail app password
- `DISCORD_WEBHOOK_BRIEF` - Discord webhook URL

### Manual Test
```bash
export OPENROUTER_API_KEY="..."
export AGENT_EMAIL="marcus.agent.joshua@gmail.com"
export AGENT_EMAIL_APP_PASSWORD="..."
export DISCORD_WEBHOOK_BRIEF="..."

python scripts/morning_brief.py
```

## Dependencies
- `requests` - HTTP requests
- `feedparser` - RSS feed parsing

## Architecture

- **Workflow:** `.github/workflows/morning-brief.yml`
- **Script:** `scripts/morning_brief.py`
- **Deps:** `scripts/requirements.txt`

## Maintenance

- Add new RSS feeds in `RSS_FEEDS` list
- Add companies in `JOB_COMPANIES` list
- Adjust keywords in `KEYWORDS` list
- Modify clothing logic in `fetch_weather()`
