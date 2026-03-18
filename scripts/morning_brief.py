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

# ========== Configuration ==========
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
AGENT_EMAIL = os.environ.get("AGENT_EMAIL")
AGENT_EMAIL_APP_PASSWORD = os.environ.get("AGENT_EMAIL_APP_PASSWORD")
DISCORD_WEBHOOK_BRIEF = os.environ.get("DISCORD_WEBHOOK_BRIEF")

# Email recipient (Joshua's personal email)
JOSHUA_EMAIL = "jtmoorehead1@gmail.com"

# Curated motivational quotes
QUOTES = [
    # Marcus Aurelius
    "You have power over your mind - not outside events. Realize this, and you will find strength.",
    "The impediment to action advances action. What stands in the way becomes the way.",
    "Waste no more time arguing about what a good man should be. Be one.",
    "Very little is needed to make a happy life; it is all within yourself, in your way of thinking.",
    
    # David Goggins
    "The only way you gain mental toughness is to do things you're not happy doing.",
    "You are in danger of living a life so comfortable and soft, that you will die without ever realizing your true potential.",
    "Suffering is the true test of life.",
    
    # Paul Graham
    "The way to get startup ideas is not to try to think of startup ideas. It's to look for problems, preferably problems you have yourself.",
    "Make something people want.",
    "It's better to make a few people really happy than to make a lot of people semi-happy.",
    
    # Charlie Munger
    "Spend each day trying to be a little wiser than you were when you woke up.",
    "The best thing a human being can do is to help another human being know more.",
    "In my whole life, I have known no wise people who didn't read all the time — none, zero.",
    
    # Seneca
    "Luck is what happens when preparation meets opportunity.",
    "We suffer more often in imagination than in reality.",
    "It is not because things are difficult that we do not dare; it is because we do not dare that they are difficult.",
]

RSS_FEEDS = {
    "tech": [
        "https://ai.googleblog.com/feeds/posts/default",
        "https://www.anthropic.com/research.rss",
        "https://ai.meta.com/blog/rss/",
        "https://www.databricks.com/blog/category/engineering-blog/feed",
        "https://huyenchip.com/feed.xml",
        "https://www.deeplearning.ai/the-batch/rss/",
        "https://jack-clark.net/feed/",
        "https://openai.com/blog/rss/",
        "https://huggingface.co/blog/feed.xml",
    ],
    "business": [
        "https://techcrunch.com/tag/venture-capital/feed/",
        "https://techcrunch.com/tag/mergers-and-acquisitions/feed/",
    ],
    "politics": [
        "https://www.politico.com/rss/technology.xml",
    ],
    "markets": [
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",  # Markets
    ]
}

ARXIV_CATEGORIES = ["cs.LG", "cs.DC", "cs.DB", "cs.PF"]

# ========== Helper Functions ==========

def llm_explain(title, summary, context="", category=""):
    """Use Claude Haiku to explain why this matters to Joshua."""
    if not OPENROUTER_API_KEY:
        return summary[:200] + "..."
    
    category_prompts = {
        "politics": "Explain how this affects tech companies, AI policy, or engineering careers. Be opinionated about its importance.",
        "markets": "Explain the implications for tech stocks, AI investments, or the broader economy. Focus on what engineers should care about.",
        "tech": "Explain why this matters for ML infrastructure work. Be sharp and opinionated about its technical or career relevance.",
        "business": "Explain the strategic implications - M&A trends, funding signals, industry consolidation. What does this mean for the AI/ML landscape?",
    }
    
    base_prompt = f"""You are Marcus, Joshua's executive assistant. He's a CMU MS student focused on ML infrastructure (PyTorch, CUDA, distributed training, model serving).

Explain in 2-3 sentences why this matters to him. {category_prompts.get(category, 'Be sharp and opinionated about its importance.')}

Title: {title}
Summary: {summary}
{f'Context: {context}' if context else ''}"""
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-haiku-4-5",
                "messages": [{"role": "user", "content": base_prompt}],
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
            clothing += f" Bring an umbrella ({precip}% rain)."
        elif precip > 30:
            clothing += f" Rain possible ({precip}%)."
        
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


def get_daily_quote():
    """Get motivational quote (rotates daily)."""
    day_of_year = datetime.now().timetuple().tm_yday
    return QUOTES[day_of_year % len(QUOTES)]


def is_recent(published_date, max_hours=48):
    """Check if a feed item is from the last 48 hours."""
    try:
        if not published_date:
            return True  # Include if no date
        
        # Parse various date formats
        from email.utils import parsedate_to_datetime
        pub_dt = parsedate_to_datetime(published_date) if isinstance(published_date, str) else published_date
        
        age = datetime.now(pub_dt.tzinfo) - pub_dt
        return age.total_seconds() / 3600 <= max_hours
    except:
        return True  # Include if parsing fails


def fetch_news_by_category():
    """Fetch and categorize news from RSS feeds (last 48 hours only)."""
    news = {
        "politics": [],
        "markets": [],
        "tech": [],
        "business": [],
    }
    
    for category, feeds in RSS_FEEDS.items():
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:  # Check top 10
                    # Only include items from last 48 hours
                    if not is_recent(entry.get("published", None)):
                        continue
                    
                    news[category].append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.get("summary", "")[:500],
                        "source": feed.feed.get("title", "Unknown"),
                        "published": entry.get("published", ""),
                    })
            except Exception as e:
                print(f"⚠️ Failed to fetch {feed_url}: {e}")
    
    return news


def rank_and_explain_news(news_items, category, max_items=4):
    """Rank news by relevance and generate explanations."""
    # Filter for relevance based on category
    relevance_keywords = {
        "politics": ["ai", "tech", "policy", "regulation", "china", "semiconductor", "chip", "export"],
        "markets": ["stock", "market", "fed", "rate", "inflation", "tech", "nvidia", "earnings"],
        "tech": ["ai", "ml", "llm", "model", "training", "gpu", "cuda", "pytorch", "inference", "chip", "semiconductor"],
        "business": ["acquisition", "merger", "funding", "valuation", "ipo", "deal", "investment"],
    }
    
    keywords = relevance_keywords.get(category, [])
    
    # Score items by keyword match
    scored = []
    for item in news_items:
        text = (item["title"] + " " + item.get("summary", "")).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:  # Only keep relevant items
            scored.append((score, item))
    
    # Sort by score and take top N
    scored.sort(reverse=True, key=lambda x: x[0])
    top_items = [item for _, item in scored[:max_items]]
    
    # Generate explanations
    for item in top_items:
        item["explanation"] = llm_explain(
            item["title"],
            item.get("summary", ""),
            f"From {item['source']}",
            category=category
        )
    
    return top_items


def fetch_arxiv_papers():
    """Fetch recent arXiv papers (last 48 hours) and explain relevance."""
    cutoff = datetime.utcnow() - timedelta(hours=48)
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
                    # Check publish date
                    published = entry.find("atom:published", ns).text
                    pub_date = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                    
                    if pub_date < cutoff:
                        continue  # Skip old papers
                    
                    title = entry.find("atom:title", ns).text.strip()
                    link = entry.find("atom:id", ns).text.strip()
                    summary = entry.find("atom:summary", ns).text.strip()
                    authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
                    
                    # Filter for relevance
                    keywords = ["distributed", "training", "inference", "gpu", "cuda", "pytorch", 
                               "optimization", "serving", "mlops", "pipeline", "system", "parallel"]
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
    
    # Get top 3 and explain why they matter
    top_papers = papers[:3]
    for paper in top_papers:
        paper["explanation"] = llm_explain(
            paper["title"],
            paper["summary"],
            f"arXiv {paper['category']} paper by {paper['authors']}",
            category="tech"
        )
    
    return top_papers


def find_top_story(all_news):
    """Use LLM to identify the single most important story."""
    if not all_news or not OPENROUTER_API_KEY:
        return None
    
    # Flatten all news
    stories = []
    for category, items in all_news.items():
        for item in items[:3]:  # Top 3 per category
            stories.append({
                "category": category,
                "title": item["title"],
                "summary": item.get("summary", "")[:300],
            })
    
    if not stories:
        return None
    
    prompt = f"""You are Marcus, analyzing the news for Joshua (CMU MS student, ML infrastructure focus).

From these stories, identify the SINGLE most important one for him to know about today. Consider:
- Impact on tech industry, AI/ML field, or his career
- Time sensitivity (does he need to know this NOW?)
- Strategic importance for someone entering ML systems roles

Stories:
{json.dumps(stories, indent=2)}

Reply with ONLY the exact title of the most important story. No explanation, just the title."""
    
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
                "max_tokens": 100,
            },
            timeout=15
        )
        if response.status_code == 200:
            top_title = response.json()["choices"][0]["message"]["content"].strip()
            
            # Find the full story
            for category, items in all_news.items():
                for item in items:
                    if item["title"] == top_title:
                        return {**item, "category": category}
    except Exception as e:
        print(f"⚠️ Failed to identify top story: {e}")
    
    return None


def generate_html_email(weather, quote, top_story, news, papers):
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
            .weather-box {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            .weather-temp {{
                font-size: 24px;
                font-weight: 700;
                margin: 10px 0;
            }}
            .weather-detail {{
                font-size: 15px;
                opacity: 0.95;
                line-height: 1.5;
            }}
            .quote-box {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 18px;
                margin: 25px 0;
                border-radius: 4px;
                font-style: italic;
                font-size: 15px;
                color: #92400e;
            }}
            .top-story {{
                background: #fee2e2;
                border-left: 4px solid #dc2626;
                padding: 20px;
                margin: 25px 0;
                border-radius: 4px;
            }}
            .top-story-title {{
                font-weight: 700;
                font-size: 18px;
                color: #991b1b;
                margin-bottom: 10px;
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
            .category-icon {{
                margin-right: 5px;
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
    
    # 1. Weather
    if weather:
        html += f"""
        <div class="weather-box">
            <div class="weather-temp">{weather['temp']}°F | {weather['condition']}</div>
            <div class="weather-detail">High: {weather['high']}°F | Low: {weather['low']}°F</div>
            <div class="weather-detail" style="margin-top: 10px; font-weight: 600;">{weather['clothing']}</div>
        </div>
        """
    
    # 2. Motivational Quote
    html += f"""
    <div class="quote-box">
        "{quote}"
    </div>
    """
    
    # 3. Top Story (if identified)
    if top_story:
        html += f"""
        <div class="top-story">
            <div style="font-size: 12px; text-transform: uppercase; color: #991b1b; font-weight: 600; margin-bottom: 8px;">
                ⚡ TOP STORY
            </div>
            <div class="top-story-title">
                <a href="{top_story['link']}" style="color: #991b1b;">{top_story['title']}</a>
            </div>
            <div style="color: #7f1d1d; font-size: 14px;">
                {top_story.get('explanation', '')}
            </div>
        </div>
        """
    
    # 4. News Categories
    category_config = {
        "politics": {"title": "🌍 Global Politics", "emoji": "🌍"},
        "markets": {"title": "📈 Markets", "emoji": "📈"},
        "tech": {"title": "💻 Tech", "emoji": "💻"},
        "business": {"title": "🏢 Business", "emoji": "🏢"},
    }
    
    html += "<h2>📰 News Briefing</h2>"
    
    for category in ["politics", "markets", "tech", "business"]:
        items = news.get(category, [])
        if not items:
            continue  # Skip empty categories
        
        config = category_config[category]
        html += f"<h3 style='font-size: 16px; color: #4b5563; margin-top: 25px;'>{config['title']}</h3>"
        
        for item in items:
            html += f"""
            <div class="item">
                <div class="item-title"><a href="{item['link']}">{item['title']}</a></div>
                <div class="item-explanation">{item['explanation']}</div>
            </div>
            """
    
    # 5. Papers
    if papers:
        html += "<h2>📄 Papers Worth Reading</h2>"
        html += "<p style='color: #6b7280; font-size: 14px; margin-top: 10px;'>Recent arXiv papers relevant to ML systems work:</p>"
        
        for paper in papers:
            html += f"""
            <div class="item">
                <div class="item-title"><a href="{paper['link']}">{paper['title']}</a></div>
                <div class="item-explanation">{paper['explanation']}</div>
                <div class="item-meta">{paper['authors']} | {paper['category']}</div>
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


def send_email(html_content, recipient_email):
    """Send email via SMTP."""
    if not all([AGENT_EMAIL, AGENT_EMAIL_APP_PASSWORD]):
        print("⚠️ Email credentials not configured")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🦅 Morning Brief - {datetime.now().strftime('%B %d, %Y')}"
        msg["From"] = AGENT_EMAIL
        msg["To"] = recipient_email
        
        msg.attach(MIMEText(html_content, "html"))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(AGENT_EMAIL, AGENT_EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def send_discord_brief(weather, top_story, news_summary):
    """Send concise summary to Discord #morning-brief."""
    if not DISCORD_WEBHOOK_BRIEF:
        print("⚠️ Discord brief webhook not configured")
        return False
    
    try:
        today = datetime.now().strftime("%B %d, %Y")
        
        embeds = []
        
        # Weather embed
        if weather:
            embeds.append({
                'title': f'🌤️ Weather - {weather["condition"]}',
                'description': f"**{weather['high']}°F / {weather['low']}°F** in Pittsburgh\n\n{weather['clothing']}",
                'color': 0x5865F2,
            })
        
        # Top story
        if top_story:
            embeds.append({
                'title': f'⚡ Top Story',
                'description': f"**[{top_story['title']}]({top_story['link']})**\n\n{top_story.get('explanation', '')}",
                'color': 0xED4245,  # Red
            })
        
        # News summary
        if news_summary:
            embeds.append({
                'title': f'📰 Morning Brief - {today}',
                'description': news_summary,
                'color': 0x57F287,
                'footer': {
                    'text': f'Full brief sent to {JOSHUA_EMAIL}'
                }
            })
        
        payload = {
            'embeds': embeds,
            'username': 'Morning Brief 🦅',
        }
        
        response = requests.post(DISCORD_WEBHOOK_BRIEF, json=payload, timeout=10)
        
        if response.status_code == 204:
            print("✅ Discord brief notification sent")
            return True
        else:
            print(f"⚠️ Discord webhook failed: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Discord brief failed: {e}")
        return False


# ========== Main ==========

def main():
    print(f"🦅 Morning Brief starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # 1. Weather
    print("📡 Fetching weather...")
    weather = fetch_weather()
    
    # 2. Daily quote
    quote = get_daily_quote()
    print(f"💬 Today's quote: {quote[:50]}...")
    
    # 3. Fetch all news by category (last 48 hours only)
    print("📡 Fetching news by category...")
    all_news_raw = fetch_news_by_category()
    
    # Rank and explain news per category
    news = {}
    for category, items in all_news_raw.items():
        print(f"📊 Ranking {category} news...")
        news[category] = rank_and_explain_news(items, category, max_items=4)
    
    # 4. Find top story
    print("🔍 Identifying top story...")
    top_story = find_top_story(news)
    
    # 5. Papers
    print("📡 Fetching arXiv papers...")
    papers = fetch_arxiv_papers()
    
    # Generate outputs
    print("📝 Generating email...")
    html = generate_html_email(weather, quote, top_story, news, papers)
    
    print(f"📧 Sending email to {JOSHUA_EMAIL}...")
    send_email(html, JOSHUA_EMAIL)
    
    # Discord summary
    news_summary = ""
    total_items = sum(len(items) for items in news.values())
    if total_items > 0:
        news_summary = f"**{total_items} news items** across politics, markets, tech, and business.\n"
    if papers:
        news_summary += f"**{len(papers)} research papers** from arXiv.\n"
    news_summary += f"\nFull brief with analysis sent to email."
    
    print("💬 Sending Discord brief notification...")
    send_discord_brief(weather, top_story, news_summary)
    
    print("✅ Morning brief complete!")


if __name__ == "__main__":
    main()
