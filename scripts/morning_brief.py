#!/usr/bin/env python3
"""
Morning Brief Agent
Aggregates ML research, job postings, weather, financial/political news, and NFL updates.
Runs daily at 11:30 UTC (6:30 AM ET) via GitHub Actions.
"""

import os
import sys
import json
import requests
import feedparser
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import xml.etree.ElementTree as ET

# ========== Configuration ==========
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
AGENT_EMAIL = os.environ.get("AGENT_EMAIL")
AGENT_EMAIL_APP_PASSWORD = os.environ.get("AGENT_EMAIL_APP_PASSWORD")
DISCORD_WEBHOOK_BRIEF = os.environ.get("DISCORD_WEBHOOK_BRIEF")

RSS_FEEDS = [
    "https://ai.googleblog.com/feeds/posts/default",
    "https://www.anthropic.com/research.rss",
    "https://ai.meta.com/blog/rss/",
    "https://www.databricks.com/blog/category/engineering-blog/feed",
    "https://huyenchip.com/feed.xml",
    "https://www.deeplearning.ai/the-batch/rss/",
    "https://jack-clark.net/feed/",
    "https://openai.com/blog/rss/",
    "https://huggingface.co/blog/feed.xml",
]

ARXIV_CATEGORIES = ["cs.LG", "cs.DC", "cs.DB", "cs.PF"]

JOB_COMPANIES = [
    ("Google", "https://www.google.com/about/careers/applications/jobs/results/"),
    ("Meta", "https://www.metacareers.com/jobs/"),
    ("Anthropic", "https://boards.greenhouse.io/anthropic"),
    ("Databricks", "https://www.databricks.com/company/careers"),
    ("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"),
    ("Scale AI", "https://scale.com/careers"),
    ("Anyscale", "https://jobs.lever.co/anyscale"),
    ("Modal", "https://modal.com/careers"),
]

KEYWORDS = [
    "MLOps", "distributed training", "inference serving", "feature store",
    "data pipeline", "systems ML", "model serving", "edge computing",
    "CUDA", "PyTorch", "ML Infrastructure", "ML Systems Engineer"
]

# ========== Helper Functions ==========

def llm_summarize(text, max_words=50):
    """Summarize text using Claude Haiku via OpenRouter."""
    if not OPENROUTER_API_KEY:
        return text[:200] + "..."
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-haiku-4-5",
                "messages": [
                    {"role": "user", "content": f"Summarize this in {max_words} words or less:\n\n{text}"}
                ],
            },
            timeout=10
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ LLM summarization failed: {e}")
    
    return text[:200] + "..."


def fetch_rss_feeds():
    """Fetch and parse RSS feeds."""
    items = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:  # Top 3 from each feed
                items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "source": feed.feed.get("title", "Unknown"),
                    "summary": entry.get("summary", "")[:300],
                })
        except Exception as e:
            print(f"⚠️ Failed to fetch {feed_url}: {e}")
    return items


def fetch_arxiv_papers():
    """Fetch recent arXiv papers from specified categories."""
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")
    papers = []
    
    for category in ARXIV_CATEGORIES:
        try:
            query = f"cat:{category}"
            url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                
                for entry in root.findall("atom:entry", ns):
                    title = entry.find("atom:title", ns).text.strip()
                    link = entry.find("atom:id", ns).text.strip()
                    summary = entry.find("atom:summary", ns).text.strip()[:300]
                    authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
                    
                    papers.append({
                        "title": title,
                        "link": link,
                        "authors": ", ".join(authors[:3]),
                        "summary": summary,
                        "category": category,
                    })
        except Exception as e:
            print(f"⚠️ Failed to fetch arXiv {category}: {e}")
    
    return papers[:10]  # Top 10 overall


def fetch_hackernews():
    """Fetch Hacker News front page stories related to AI/ML."""
    try:
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        story_ids = response.json()[:30]  # Top 30 stories
        
        stories = []
        for story_id in story_ids:
            story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5)
            story = story_response.json()
            
            title = story.get("title", "").lower()
            if any(kw.lower() in title for kw in ["ai", "ml", "machine learning", "llm", "gpt", "model", "pytorch", "cuda"]):
                stories.append({
                    "title": story.get("title"),
                    "link": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                })
                if len(stories) >= 5:
                    break
        
        return stories
    except Exception as e:
        print(f"⚠️ Failed to fetch Hacker News: {e}")
        return []


def fetch_weather():
    """Fetch Pittsburgh weather and clothing recommendation."""
    try:
        response = requests.get("https://wttr.in/Pittsburgh?format=j1", timeout=10)
        data = response.json()
        
        current = data["current_condition"][0]
        forecast = data["weather"][0]
        
        temp_f = int(current["temp_F"])
        high_f = int(forecast["maxtempF"])
        low_f = int(forecast["mintempF"])
        condition = current["weatherDesc"][0]["value"]
        precip = forecast["hourly"][0]["chanceofrain"]
        
        # Clothing recommendation
        if temp_f < 32:
            clothing = "Heavy coat, layers, gloves"
        elif temp_f < 50:
            clothing = "Jacket + layers"
        elif temp_f < 65:
            clothing = "Light jacket or sweater"
        else:
            clothing = "T-shirt or light layers"
        
        return {
            "temp": temp_f,
            "high": high_f,
            "low": low_f,
            "condition": condition,
            "precip": precip,
            "clothing": clothing,
        }
    except Exception as e:
        print(f"⚠️ Failed to fetch weather: {e}")
        return None


def fetch_financial_news():
    """Fetch financial news (tech stocks, Fed, VC funding)."""
    items = []
    feeds = [
        "https://www.bloomberg.com/feed/podcast/technology.xml",
        "https://techcrunch.com/tag/venture-capital/feed/",
    ]
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                items.append({
                    "title": entry.title,
                    "link": entry.link,
                })
        except Exception as e:
            print(f"⚠️ Failed to fetch financial feed: {e}")
    
    return items[:3]


def fetch_political_news():
    """Fetch political news (tech policy, AI regulation)."""
    items = []
    feeds = [
        "https://www.politico.com/rss/technology.xml",
        "https://www.theverge.com/rss/tech/index.xml",
    ]
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                if any(kw in entry.title.lower() for kw in ["ai", "tech", "policy", "regulation"]):
                    items.append({
                        "title": entry.title,
                        "link": entry.link,
                    })
        except Exception as e:
            print(f"⚠️ Failed to fetch political feed: {e}")
    
    return items[:2]


def fetch_nfl_news():
    """Fetch major NFL updates."""
    try:
        feed = feedparser.parse("https://www.espn.com/espn/rss/nfl/news")
        items = []
        for entry in feed.entries[:3]:
            items.append({
                "title": entry.title,
                "link": entry.link,
            })
        return items
    except Exception as e:
        print(f"⚠️ Failed to fetch NFL news: {e}")
        return []


def fetch_jobs():
    """Check job boards for ML/Data Infra roles (placeholder for now)."""
    # Note: Real scraping would require more sophisticated logic per company
    # For now, return placeholder links
    return [
        {"company": company, "link": url}
        for company, url in JOB_COMPANIES[:3]
    ]


def generate_html_email(sections):
    """Generate HTML email from sections."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #1a1a1a; }}
            h2 {{ color: #2563eb; margin-top: 30px; border-bottom: 2px solid #e5e7eb; padding-bottom: 5px; }}
            .item {{ margin: 15px 0; }}
            .item-title {{ font-weight: 600; color: #1a1a1a; }}
            .item-meta {{ color: #6b7280; font-size: 0.9em; }}
            a {{ color: #2563eb; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .weather {{ background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <h1>🦅 Morning Brief - {today}</h1>
    """
    
    for section in sections:
        html += f"\n<h2>{section['title']}</h2>\n"
        for item in section['items']:
            html += f"""
            <div class="item">
                <div class="item-title"><a href="{item.get('link', '#')}">{item.get('title', 'Untitled')}</a></div>
                {f"<div class='item-meta'>{item.get('meta', '')}</div>" if item.get('meta') else ""}
            </div>
            """
    
    html += """
    </body>
    </html>
    """
    
    return html


def send_email(html_content):
    """Send email via SMTP."""
    if not all([AGENT_EMAIL, AGENT_EMAIL_APP_PASSWORD]):
        print("⚠️ Email credentials not configured")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Morning Brief - {datetime.now().strftime('%Y-%m-%d')}"
        msg["From"] = AGENT_EMAIL
        msg["To"] = AGENT_EMAIL
        
        msg.attach(MIMEText(html_content, "html"))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(AGENT_EMAIL, AGENT_EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent successfully")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def send_discord(sections):
    """Send summary to Discord via webhook."""
    if not DISCORD_WEBHOOK_BRIEF:
        print("⚠️ Discord webhook not configured")
        return False
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        content = f"**🦅 Morning Brief - {today}**\n\n"
        
        for section in sections[:3]:  # First 3 sections only
            content += f"**{section['title']}**\n"
            for item in section['items'][:2]:  # Top 2 items per section
                content += f"• [{item.get('title', 'Untitled')}]({item.get('link', '#')})\n"
            content += "\n"
        
        content += f"*Full brief sent to {AGENT_EMAIL}*"
        
        requests.post(DISCORD_WEBHOOK_BRIEF, json={"content": content}, timeout=10)
        print("✅ Discord notification sent")
        return True
    except Exception as e:
        print(f"❌ Discord failed: {e}")
        return False


# ========== Main ==========

def main():
    print(f"🦅 Morning Brief Agent starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    sections = []
    
    # Weather
    print("📡 Fetching weather...")
    weather = fetch_weather()
    if weather:
        sections.append({
            "title": "🌤️ Weather (Pittsburgh)",
            "items": [{
                "title": f"{weather['high']}°F / {weather['low']}°F | {weather['condition']} | {weather['precip']}% rain",
                "meta": f"Wear: {weather['clothing']}",
                "link": "https://wttr.in/Pittsburgh"
            }]
        })
    
    # Papers
    print("📡 Fetching arXiv papers...")
    papers = fetch_arxiv_papers()
    if papers:
        sections.append({
            "title": "📄 Papers",
            "items": [
                {
                    "title": p["title"],
                    "link": p["link"],
                    "meta": f"{p['authors']} | {p['category']}"
                }
                for p in papers[:5]
            ]
        })
    
    # Financial
    print("📡 Fetching financial news...")
    financial = fetch_financial_news()
    if financial:
        sections.append({
            "title": "💰 Financial",
            "items": financial
        })
    
    # Political
    print("📡 Fetching political news...")
    political = fetch_political_news()
    if political:
        sections.append({
            "title": "🗳️ Political",
            "items": political
        })
    
    # Tech News (RSS)
    print("📡 Fetching RSS feeds...")
    rss_items = fetch_rss_feeds()
    if rss_items:
        sections.append({
            "title": "📰 Tech News",
            "items": [
                {
                    "title": item["title"],
                    "link": item["link"],
                    "meta": item["source"]
                }
                for item in rss_items[:5]
            ]
        })
    
    # Hacker News
    print("📡 Fetching Hacker News...")
    hn = fetch_hackernews()
    if hn:
        sections.append({
            "title": "🔥 Hacker News",
            "items": hn
        })
    
    # NFL
    print("📡 Fetching NFL news...")
    nfl = fetch_nfl_news()
    if nfl:
        sections.append({
            "title": "🏈 NFL",
            "items": nfl[:2]
        })
    
    # Jobs
    print("📡 Fetching job postings...")
    jobs = fetch_jobs()
    if jobs:
        sections.append({
            "title": "💼 Jobs",
            "items": [
                {
                    "title": f"{job['company']} Careers",
                    "link": job["link"]
                }
                for job in jobs
            ]
        })
    
    # Generate outputs
    print("📝 Generating email...")
    html = generate_html_email(sections)
    
    print("📧 Sending email...")
    send_email(html)
    
    print("💬 Sending Discord notification...")
    send_discord(sections)
    
    print("✅ Morning brief complete!")


if __name__ == "__main__":
    main()
