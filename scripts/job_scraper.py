#!/usr/bin/env python3
"""
Job Scraper Module - Internships & Entry-Level Roles
Focuses on: ML Engineer, Software Engineer, Data Engineer, Data Infrastructure Engineer, 
            ML Systems Engineer, Platform Engineer
Target: Summer 2026, Fall 2026 internships + new grad roles
"""

import re
import os
import json
import requests
from urllib.parse import urlencode


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


def search_linkedin_jobs(search_queries, location="United States"):
    """
    Search LinkedIn Jobs for entry-level roles.
    
    Note: Returns search URLs for manual checking. LinkedIn heavily rate-limits scraping.
    
    Args:
        search_queries: List of job title search queries
        location: Location filter
    
    Returns:
        List of search result dicts with URLs to check manually
    """
    jobs = []
    
    for query in search_queries:
        try:
            params = {
                'keywords': query,
                'location': location,
                'f_E': '1,2',  # Entry level + Internship
                'f_TPR': 'r2592000',  # Posted in last 30 days
                'f_WT': '2',  # Remote option
            }
            
            url = f"https://www.linkedin.com/jobs/search?{urlencode(params)}"
            
            jobs.append({
                'company': 'LinkedIn',
                'title': f'{query} (Entry-Level / Internship)',
                'location': location,
                'url': url,
                'type': 'Search Results',
            })
        
        except Exception as e:
            print(f"⚠️ LinkedIn URL generation error for '{query}': {e}")
    
    return jobs


def search_indeed_jobs(search_queries, location="United States"):
    """
    Search Indeed for entry-level roles.
    
    Args:
        search_queries: List of job title search queries
        location: Location filter
    
    Returns:
        List of search result dicts with URLs
    """
    jobs = []
    
    for query in search_queries:
        try:
            params = {
                'q': query,
                'l': location,
                'fromage': '30',  # Last 30 days
                'sc': '0kf%3Aexplvl%28ENTRY_LEVEL%29%3B',  # Entry level filter
            }
            
            url = f"https://www.indeed.com/jobs?{urlencode(params)}"
            
            jobs.append({
                'company': 'Indeed',
                'title': f'{query} (Entry-Level)',
                'location': location,
                'url': url,
                'type': 'Search Results',
            })
        
        except Exception as e:
            print(f"⚠️ Indeed URL generation error for '{query}': {e}")
    
    return jobs


def aggregate_jobs():
    """
    Aggregate internships and entry-level roles from all sources.
    
    Returns:
        List of job dicts, sorted by relevance
    """
    all_jobs = []
    
    print("🔍 Scraping job boards for internships and entry-level roles...")
    
    # Define search queries for LinkedIn and Indeed
    search_queries = [
        "ML Engineer internship 2026",
        "Software Engineer new grad 2026",
        "Data Engineer entry level",
        "Data Infrastructure Engineer internship",
        "ML Systems Engineer new grad",
        "Platform Engineer entry level",
    ]
    
    # LinkedIn searches
    print("   📡 Generating LinkedIn search URLs...")
    linkedin_jobs = search_linkedin_jobs(search_queries)
    all_jobs.extend(linkedin_jobs)
    
    # Indeed searches
    print("   📡 Generating Indeed search URLs...")
    indeed_jobs = search_indeed_jobs(search_queries)
    all_jobs.extend(indeed_jobs)
    
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
    
    print(f"\n✅ Found {len(all_jobs)} job sources and listings")
    
    # Deduplicate by URL
    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        if job['url'] not in seen_urls:
            seen_urls.add(job['url'])
            unique_jobs.append(job)
    
    return unique_jobs


def post_jobs_to_discord(jobs, webhook_url):
    """
    Post job findings to Discord #jobs channel using rich embeds.
    
    Args:
        jobs: List of job dicts
        webhook_url: Discord webhook URL for #jobs channel
    
    Returns:
        True if successful, False otherwise
    """
    if not webhook_url:
        print("⚠️ Discord jobs webhook not configured")
        return False
    
    try:
        # Group jobs by type
        greenhouse_lever = [j for j in jobs if j['type'] in ['Internship', 'New Grad']]
        search_links = [j for j in jobs if j['type'] == 'Search Results']
        
        # Create embeds
        embeds = []
        
        # Direct job postings
        if greenhouse_lever:
            fields = []
            for job in greenhouse_lever[:10]:  # Limit to 10
                fields.append({
                    'name': f"{job['company']} - {job['title']}",
                    'value': f"📍 {job['location']} | {job['type']}\n[Apply Here]({job['url']})",
                    'inline': False
                })
            
            embeds.append({
                'title': '💼 New Job Postings',
                'description': 'Direct listings from company career pages:',
                'color': 0x5865F2,  # Discord blurple
                'fields': fields[:10],  # Discord limit: 25 fields per embed
            })
        
        # Search links
        if search_links:
            fields = []
            for job in search_links[:6]:  # Top 6 searches
                fields.append({
                    'name': f"{job['company']}: {job['title']}",
                    'value': f"[View Results]({job['url']})",
                    'inline': False
                })
            
            embeds.append({
                'title': '🔍 Job Board Searches',
                'description': 'Pre-filtered searches for entry-level roles:',
                'color': 0x57F287,  # Green
                'fields': fields,
            })
        
        # Send to Discord
        payload = {
            'embeds': embeds,
            'username': 'Morning Brief 🦅',
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 204:
            print(f"✅ Posted {len(jobs)} jobs to Discord #jobs")
            return True
        else:
            print(f"⚠️ Discord webhook failed: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Failed to post jobs to Discord: {e}")
        return False


if __name__ == "__main__":
    # Test the scraper
    jobs = aggregate_jobs()
    
    print("\n📋 Results:")
    for job in jobs[:15]:
        print(f"\n{job['company']} - {job['type']}")
        print(f"  {job['title']}")
        print(f"  📍 {job['location']}")
        print(f"  🔗 {job['url']}")
