#!/usr/bin/env python3
"""
Morning Brief Agent - Executive Intelligence Digest
Personalized daily briefing for Joshua Moorehead (CMU ECE MS, ML Systems focus)
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
from job_scraper import aggregate_jobs

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

# Joshua's profile for context
PROFILE = {
    "focus": "ML/Data Infrastructure, distributed systems, CUDA optimization",
    "interests": "MLOps, model serving, training pipelines, PyTorch internals",
    "career_goal": "ML Systems Engineer → Forward Deployed Engineer → technical leadership",
    "current": "CMU ECE MS (Spring 2026), coursework in ML, systems, robotics",
    "location": "Pittsburgh, PA",
}

# ========== Helper Functions ==========

def llm_explain(title, summary, context=""):
    """Use Claude Haiku to explain why this matters to Joshua."""
    if not OPENROUTER_API_KEY:
        return summary[:200] + "..."
    
    prompt = f"""You are Marcus, Joshua's executive assistant. He's a CMU MS student focused on ML infrastructure (PyTorch, CUDA, distributed training, model serving).

Explain in 2-3 sentences why this matters to him:

Title: {title}
Summary: {summary}
{f'Context: {context}' if context else ''}

Focus on: practical implications for ML systems work, career relevance, technical insights."""
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-haiku-4-5",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
            },
            timeout=15
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ LLM explanation failed: {e}")
    
    return summary[:200] + "..."


def fetch_weather():
    """Fetch Pittsburgh weather with clothing recommendation."""
    try:
        response = requests.get("https://wttr.in/Pittsburgh?format=j1", timeout=10)
        data = response.json()
        
        current = data["current_condition"][0]
        forecast = data["weather"][0]
        
        temp_f = int(current["temp_F"])
        high_f = int(forecast["maxtempF"])
        low_f = int(forecast["mintempF"])
        condition = current["weatherDesc"][0]["value"]
        precip = int(forecast["hourly"][0]["chanceofrain"])
        
        # Smart clothing recommendation
        if temp_f < 25:
            clothing = "Heavy winter coat, layers, gloves. It's brutal out there."
        elif temp_f < 35:
            clothing = "Warm coat + layers. Cold morning."
        elif temp_f < 45:
            clothing = "Jacket required. Chilly."
        elif temp_f < 55:
            clothing = "Light jacket or sweater."
        elif temp_f < 65:
            clothing = "Long sleeves, maybe a light layer."
        elif temp_f < 75:
            clothing = "T-shirt weather. Comfortable."
        else:
            clothing = "Light clothes. Warm day."
        
        if precip > 60:
            clothing += " Bring an umbrella ({}% rain).".format(precip)
        elif precip > 30:
            clothing += " Rain possible ({}%).".format(precip)
        
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


def fetch_arxiv_papers():
    """Fetch recent arXiv papers and explain relevance."""
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")
    papers = []
    
    for category in ARXIV_CATEGORIES:
        try:
            query = f"cat:{category}"
            url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=15&sortBy=submittedDate&sortOrder=descending"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                
                for entry in root.findall("atom:entry", ns):
                    title = entry.find("atom:title", ns).text.strip()
                    link = entry.find("atom:id", ns).text.strip()
                    summary = entry.find("atom:summary", ns).text.strip()
                    authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
                    
                    # Filter for relevance
                    keywords = ["distributed", "training", "inference", "gpu", "cuda", "pytorch", 
                               "optimization", "serving", "mlops", "pipeline", "system"]
                    if any(kw in title.lower() or kw in summary.lower() for kw in keywords):
                        papers.append({
                            "title": title,
                            "link": link,
                            "authors": ", ".join(authors[:3]),
                            "summary": summary,
                            "category": category,
                        })
        except Exception as e:
            print(f"⚠️ Failed to fetch arXiv {category}: {e}")
    
    # Get top 5 and explain why they matter
    top_papers = papers[:5]
    for paper in top_papers:
        paper["explanation"] = llm_explain(
            paper["title"],
            paper["summary"],
            f"arXiv {paper['category']} paper by {paper['authors']}"
        )
    
    return top_papers


def fetch_rss_feeds():
    """Fetch RSS feeds and explain relevance."""
    items = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:  # Top 2 from each
                items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "source": feed.feed.get("title", "Unknown"),
                    "summary": entry.get("summary", "")[:500],
                })
        except Exception as e:
            print(f"⚠️ Failed to fetch {feed_url}: {e}")
    
    # Explain top 5
    for item in items[:5]:
        item["explanation"] = llm_explain(item["title"], item["summary"], f"From {item['source']}")
    
    return items[:5]


def fetch_hackernews():
    """Fetch Hacker News AI/ML stories with explanations."""
    try:
        response = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        story_ids = response.json()[:30]
        
        stories = []
        for story_id in story_ids:
            story_response = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5)
            story = story_response.json()
            
            title = story.get("title", "").lower()
            if any(kw in title for kw in ["ai", "ml", "machine learning", "llm", "gpt", "model", "pytorch", "cuda", "training"]):
                stories.append({
                    "title": story.get("title"),
                    "link": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                })
                if len(stories) >= 3:
                    break
        
        return stories
    except Exception as e:
        print(f"⚠️ Failed to fetch Hacker News: {e}")
        return []


def fetch_financial_news():
    """Fetch financial news with PE/tech focus."""
    items = []
    feeds = [
        "https://techcrunch.com/tag/venture-capital/feed/",
        "https://www.bloomberg.com/feed/podcast/technology.xml",
    ]
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                summary = entry.get("summary", "")[:500]
                items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": summary,
                })
        except Exception as e:
            print(f"⚠️ Failed to fetch financial feed: {e}")
    
    # Explain top 3
    for item in items[:3]:
        item["explanation"] = llm_explain(
            item["title"],
            item["summary"],
            "Financial/VC news - focus on PE interest, tech valuations, funding trends"
        )
    
    return items[:3]


def fetch_political_news():
    """Fetch political news affecting tech/AI."""
    items = []
    feeds = [
        "https://www.politico.com/rss/technology.xml",
        "https://www.theverge.com/rss/tech/index.xml",
    ]
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:
                if any(kw in entry.title.lower() for kw in ["ai", "tech", "policy", "regulation", "china"]):
                    summary = entry.get("summary", "")[:500]
                    items.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": summary,
                    })
        except Exception as e:
            print(f"⚠️ Failed to fetch political feed: {e}")
    
    # Explain top 2
    for item in items[:2]:
        item["explanation"] = llm_explain(
            item["title"],
            item["summary"],
            "Tech policy - focus on AI regulation, industry impact"
        )
    
    return items[:2]


def fetch_nfl_news():
    """Fetch major NFL updates (in season only)."""
    try:
        feed = feedparser.parse("https://www.espn.com/espn/rss/nfl/news")
        items = []
        for entry in feed.entries[:3]:
            # Filter for major news only
            if any(kw in entry.title.lower() for kw in ["playoff", "trade", "championship", "super bowl", "injury"]):
                items.append({
                    "title": entry.title,
                    "link": entry.link,
                })
        return items
    except Exception as e:
        print(f"⚠️ Failed to fetch NFL news: {e}")
        return []


def fetch_jobs():
    """Scrape internships and entry-level roles from job boards."""
    try:
        jobs = aggregate_jobs()
        return jobs[:10]  # Top 10 most relevant
    except Exception as e:
        print(f"⚠️ Job scraping failed: {e}")
        # Fallback to career page links
        return [
            {
                "company": company,
                "title": f"{company} - Internships & Entry-Level",
                "location": "Various",
                "url": url,
                "type": "Career Page"
            }
            for company, url in JOB_COMPANIES[:5]
        ]


def generate_html_email(sections):
    """Generate sharp executive briefing email."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif; 
                max-width: 700px; 
                margin: 0 auto; 
                padding: 20px;
                line-height: 1.6;
                color: #1a1a1a;
            }}
            h1 {{ 
                color: #1a1a1a; 
                font-size: 28px;
                margin-bottom: 5px;
            }}
            .subtitle {{
                color: #6b7280;
                font-size: 14px;
                margin-bottom: 30px;
            }}
            h2 {{ 
                color: #2563eb; 
                margin-top: 35px; 
                margin-bottom: 15px;
                font-size: 20px;
                border-bottom: 2px solid #e5e7eb; 
                padding-bottom: 8px; 
            }}
            .item {{ 
                margin: 20px 0; 
                padding: 15px;
                background: #f9fafb;
                border-radius: 6px;
            }}
            .item-title {{ 
                font-weight: 600; 
                font-size: 16px;
                color: #1a1a1a; 
                margin-bottom: 8px;
            }}
            .item-explanation {{
                color: #374151;
                font-size: 14px;
                line-height: 1.5;
            }}
            .item-meta {{ 
                color: #6b7280; 
                font-size: 13px; 
                margin-top: 8px;
            }}
            a {{ 
                color: #2563eb; 
                text-decoration: none; 
            }}
            a:hover {{ 
                text-decoration: underline; 
            }}
            .weather {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px; 
                border-radius: 10px; 
                margin: 25px 0;
            }}
            .weather h2 {{
                color: white;
                border: none;
                margin-top: 0;
            }}
            .weather-main {{
                font-size: 18px;
                font-weight: 600;
                margin: 10px 0;
            }}
            .weather-detail {{
                font-size: 14px;
                opacity: 0.95;
            }}
            .priority {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                color: #6b7280;
                font-size: 13px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <h1>🦅 Morning Brief</h1>
        <div class="subtitle">{today}</div>
    """
    
    for section in sections:
        if section.get("is_weather"):
            html += f"""
            <div class="weather">
                <h2>{section['title']}</h2>
                <div class="weather-main">{section['main']}</div>
                <div class="weather-detail">{section['detail']}</div>
            </div>
            """
        else:
            html += f"\n<h2>{section['title']}</h2>\n"
            
            if section.get("priority"):
                html += f'<div class="priority"><strong>Priority:</strong> {section["priority"]}</div>'
            
            for item in section['items']:
                html += f"""
                <div class="item">
                    <div class="item-title"><a href="{item.get('link', '#')}">{item.get('title', 'Untitled')}</a></div>
                    <div class="item-explanation">{item.get('explanation', item.get('summary', ''))}</div>
                    {f"<div class='item-meta'>{item.get('meta', '')}</div>" if item.get('meta') else ""}
                </div>
                """
    
    html += """
        <div class="footer">
            Generated by Marcus 🦅 | Morning Brief Agent<br>
            Questions or feedback? Just reply to this email.
        </div>
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
        msg["Subject"] = f"🦅 Morning Brief - {datetime.now().strftime('%B %d, %Y')}"
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


def send_discord(weather, top_items):
    """Send concise summary to Discord."""
    if not DISCORD_WEBHOOK_BRIEF:
        print("⚠️ Discord webhook not configured")
        return False
    
    try:
        today = datetime.now().strftime("%B %d, %Y")
        content = f"**🦅 Morning Brief - {today}**\n\n"
        
        if weather:
            content += f"🌤️ **{weather['high']}°F/{weather['low']}°F** in Pittsburgh ({weather['condition']})\n"
            content += f"*{weather['clothing']}*\n\n"
        
        content += "**Top Items:**\n"
        for item in top_items[:3]:
            content += f"• [{item['title']}]({item['link']})\n"
        
        content += f"\n*Full brief sent to {AGENT_EMAIL}*"
        
        requests.post(DISCORD_WEBHOOK_BRIEF, json={"content": content}, timeout=10)
        print("✅ Discord notification sent")
        return True
    except Exception as e:
        print(f"❌ Discord failed: {e}")
        return False


# ========== Main ==========

def main():
    print(f"🦅 Morning Brief starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    sections = []
    all_items = []
    
    # 1. Weather (always first)
    print("📡 Fetching weather...")
    weather = fetch_weather()
    if weather:
        sections.append({
            "title": "🌤️ Weather & What to Wear",
            "is_weather": True,
            "main": f"{weather['high']}°F / {weather['low']}°F | {weather['condition']}",
            "detail": weather['clothing'],
        })
    
    # 2. Papers
    print("📡 Fetching arXiv papers...")
    papers = fetch_arxiv_papers()
    if papers:
        sections.append({
            "title": "📄 Papers Worth Reading",
            "items": [
                {
                    "title": p["title"],
                    "link": p["link"],
                    "explanation": p["explanation"],
                    "meta": f"{p['authors']} | {p['category']}"
                }
                for p in papers
            ]
        })
        all_items.extend(papers)
    
    # 3. ML/AI News
    print("📡 Fetching RSS feeds...")
    rss_items = fetch_rss_feeds()
    if rss_items:
        sections.append({
            "title": "📰 ML/AI News",
            "items": [
                {
                    "title": item["title"],
                    "link": item["link"],
                    "explanation": item["explanation"],
                    "meta": item["source"]
                }
                for item in rss_items
            ]
        })
        all_items.extend(rss_items)
    
    # 4. Hacker News
    print("📡 Fetching Hacker News...")
    hn = fetch_hackernews()
    if hn and sections:
        # Add to ML/AI News section
        sections[-1]["items"].extend([
            {
                "title": item["title"],
                "link": item["link"],
                "explanation": "Trending on Hacker News.",
                "meta": "Hacker News"
            }
            for item in hn
        ])
    
    # 5. Financial
    print("📡 Fetching financial news...")
    financial = fetch_financial_news()
    if financial:
        sections.append({
            "title": "💰 Finance & VC",
            "items": [
                {
                    "title": item["title"],
                    "link": item["link"],
                    "explanation": item["explanation"],
                }
                for item in financial
            ]
        })
        all_items.extend(financial)
    
    # 6. Political
    print("📡 Fetching political news...")
    political = fetch_political_news()
    if political:
        sections.append({
            "title": "🏛️ Tech Policy",
            "items": [
                {
                    "title": item["title"],
                    "link": item["link"],
                    "explanation": item["explanation"],
                }
                for item in political
            ]
        })
        all_items.extend(political)
    
    # 7. NFL (if in season)
    print("📡 Fetching NFL news...")
    nfl = fetch_nfl_news()
    if nfl:
        sections.append({
            "title": "🏈 NFL",
            "items": [
                {
                    "title": item["title"],
                    "link": item["link"],
                    "explanation": "Major NFL update.",
                }
                for item in nfl
            ]
        })
    
    # 8. Jobs (always last)
    print("📡 Fetching job postings...")
    jobs = fetch_jobs()
    if jobs:
        sections.append({
            "title": "💼 Internships & Entry-Level Roles",
            "items": [
                {
                    "title": f"{job['company']} - {job['title']}",
                    "link": job["url"],
                    "explanation": f"{job['type']} role in {job['location']}. Good fit for ML/infrastructure/data background with PyTorch, CUDA, or distributed systems experience.",
                    "meta": f"{job['type']} | {job['location']}"
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
    send_discord(weather, all_items)
    
    print("✅ Morning brief complete!")


if __name__ == "__main__":
    main()
