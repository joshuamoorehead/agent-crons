#!/usr/bin/env python3
"""
Job Scraper Module - Internships & Entry-Level Roles
Focuses on: ML, Infrastructure, Data, Software Engineering
Target: Summer 2026, Fall 2026 internships + new grad roles
"""

import re
import json
import requests
from html.parser import HTMLParser
from urllib.parse import urlencode, quote_plus


class JobHTMLParser(HTMLParser):
    """Simple HTML parser to extract job listings."""
    def __init__(self):
        super().__init__()
        self.jobs = []
        self.in_job = False
        self.current_job = {}
        
    def handle_starttag(self, tag, attrs):
        # Placeholder - can be customized per site
        pass
    
    def handle_data(self, data):
        # Placeholder - can be customized per site
        pass


def scrape_greenhouse_api(company_slug, keywords=None):
    """
    Scrape Greenhouse API for internships and entry-level roles.
    
    Args:
        company_slug: Greenhouse board slug (e.g., 'anthropic', 'databricks')
        keywords: List of keywords to filter by (default: internship/entry-level terms)
    
    Returns:
        List of job dicts with title, location, url, type
    """
    if keywords is None:
        keywords = ['intern', 'internship', 'new grad', 'university', 'entry level', 
                   'recent grad', 'early career', 'junior', 'associate']
    
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return []
        
        jobs_data = response.json().get('jobs', [])
        
        # Filter for internships/entry-level in ML/infra/data/software
        relevant_jobs = []
        for job in jobs_data:
            title = job.get('title', '').lower()
            
            # Check if it's an internship or entry-level role
            is_target_level = any(kw in title for kw in keywords)
            
            # Check if it's in the right field
            is_target_field = any(field in title for field in [
                'ml', 'machine learning', 'infrastructure', 'data', 'software',
                'backend', 'systems', 'platform', 'swe', 'engineer'
            ])
            
            if is_target_level and is_target_field:
                relevant_jobs.append({
                    'company': company_slug.title(),
                    'title': job.get('title'),
                    'location': job.get('location', {}).get('name', 'Remote'),
                    'url': job.get('absolute_url'),
                    'type': 'Internship' if 'intern' in title else 'New Grad',
                })
        
        return relevant_jobs
    
    except Exception as e:
        print(f"⚠️ Greenhouse API error for {company_slug}: {e}")
        return []


def scrape_lever_api(company_slug, keywords=None):
    """
    Scrape Lever API for internships and entry-level roles.
    
    Args:
        company_slug: Lever board slug (e.g., 'anyscale')
        keywords: List of keywords to filter by
    
    Returns:
        List of job dicts
    """
    if keywords is None:
        keywords = ['intern', 'internship', 'new grad', 'university', 'entry level', 
                   'recent grad', 'early career', 'junior', 'associate']
    
    try:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return []
        
        jobs_data = response.json()
        
        relevant_jobs = []
        for job in jobs_data:
            title = job.get('text', '').lower()
            
            is_target_level = any(kw in title for kw in keywords)
            is_target_field = any(field in title for field in [
                'ml', 'machine learning', 'infrastructure', 'data', 'software',
                'backend', 'systems', 'platform', 'swe', 'engineer'
            ])
            
            if is_target_level and is_target_field:
                location = job.get('categories', {}).get('location', 'Remote')
                relevant_jobs.append({
                    'company': company_slug.title(),
                    'title': job.get('text'),
                    'location': location,
                    'url': job.get('hostedUrl'),
                    'type': 'Internship' if 'intern' in title else 'New Grad',
                })
        
        return relevant_jobs
    
    except Exception as e:
        print(f"⚠️ Lever API error for {company_slug}: {e}")
        return []


def scrape_linkedin_jobs(keywords="ML internship 2026", location="United States"):
    """
    Scrape LinkedIn Jobs (limited without authentication).
    
    Note: LinkedIn heavily rate-limits and blocks scraping. This is a best-effort
    attempt using their public job search page.
    
    Args:
        keywords: Search query
        location: Location filter
    
    Returns:
        List of job dicts (may be empty if blocked)
    """
    try:
        params = {
            'keywords': keywords,
            'location': location,
            'f_E': '1,2',  # Entry level + Internship
            'f_TPR': 'r2592000',  # Posted in last 30 days
        }
        
        url = f"https://www.linkedin.com/jobs/search?{urlencode(params)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"⚠️ LinkedIn blocked or unavailable (status: {response.status_code})")
            return []
        
        # Very basic parsing - LinkedIn HTML is complex and changes frequently
        # This is a placeholder approach
        jobs = []
        
        # Look for job card patterns in HTML
        # Note: This is fragile and may break; consider it a fallback only
        matches = re.findall(r'<h3[^>]*>([^<]+)</h3>', response.text)
        
        for match in matches[:5]:  # Limit to top 5
            if any(kw in match.lower() for kw in ['intern', 'ml', 'software', 'data']):
                jobs.append({
                    'company': 'LinkedIn Search',
                    'title': match.strip(),
                    'location': location,
                    'url': url,
                    'type': 'See LinkedIn',
                })
        
        if not jobs:
            print("⚠️ LinkedIn: No jobs parsed (likely requires authentication)")
        
        return jobs
    
    except Exception as e:
        print(f"⚠️ LinkedIn scraping error: {e}")
        return []


def scrape_indeed_jobs(query="ML internship", location="Pittsburgh, PA"):
    """
    Scrape Indeed jobs (best-effort, Indeed blocks aggressive scraping).
    
    Args:
        query: Search query
        location: Location filter
    
    Returns:
        List of job dicts
    """
    try:
        params = {
            'q': query,
            'l': location,
            'fromage': '30',  # Last 30 days
            'jt': 'internship',  # Job type: internship
        }
        
        url = f"https://www.indeed.com/jobs?{urlencode(params)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"⚠️ Indeed blocked or unavailable (status: {response.status_code})")
            return []
        
        # Basic pattern matching (Indeed HTML is complex)
        jobs = []
        
        # Look for job title patterns
        title_matches = re.findall(r'<h2[^>]*>.*?<span[^>]*>([^<]+)</span>', response.text, re.DOTALL)
        
        for title in title_matches[:5]:
            title = re.sub(r'\s+', ' ', title).strip()
            if any(kw in title.lower() for kw in ['intern', 'ml', 'software', 'data', 'engineer']):
                jobs.append({
                    'company': 'Indeed Search',
                    'title': title,
                    'location': location,
                    'url': url,
                    'type': 'See Indeed',
                })
        
        if not jobs:
            print("⚠️ Indeed: No jobs parsed (may require different parsing)")
        
        return jobs
    
    except Exception as e:
        print(f"⚠️ Indeed scraping error: {e}")
        return []


def aggregate_jobs():
    """
    Aggregate internships and entry-level roles from all sources.
    
    Returns:
        List of job dicts, sorted by relevance
    """
    all_jobs = []
    
    print("🔍 Scraping job boards for internships and entry-level roles...")
    
    # Greenhouse companies
    greenhouse_companies = ['anthropic', 'databricks', 'scale', 'openai']
    for company in greenhouse_companies:
        print(f"   📡 Checking {company.title()} (Greenhouse)...")
        jobs = scrape_greenhouse_api(company)
        all_jobs.extend(jobs)
    
    # Lever companies
    lever_companies = ['anyscale']
    for company in lever_companies:
        print(f"   📡 Checking {company.title()} (Lever)...")
        jobs = scrape_lever_api(company)
        all_jobs.extend(jobs)
    
    # LinkedIn (best-effort)
    print("   📡 Checking LinkedIn...")
    linkedin_jobs = scrape_linkedin_jobs(
        keywords="ML software data infrastructure internship 2026",
        location="United States"
    )
    all_jobs.extend(linkedin_jobs)
    
    # Indeed (best-effort)
    print("   📡 Checking Indeed...")
    indeed_jobs = scrape_indeed_jobs(
        query="ML software data internship summer 2026",
        location="Pittsburgh, PA"
    )
    all_jobs.extend(indeed_jobs)
    
    print(f"\n✅ Found {len(all_jobs)} relevant jobs")
    
    # Deduplicate by URL
    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        if job['url'] not in seen_urls:
            seen_urls.add(job['url'])
            unique_jobs.append(job)
    
    return unique_jobs


if __name__ == "__main__":
    # Test the scraper
    jobs = aggregate_jobs()
    
    print("\n📋 Results:")
    for job in jobs[:10]:
        print(f"\n{job['company']} - {job['type']}")
        print(f"  {job['title']}")
        print(f"  📍 {job['location']}")
        print(f"  🔗 {job['url']}")
