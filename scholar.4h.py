#!/usr/bin/python3
# -*- coding: utf-8 -*-
# <xbar.title>Google Scholar Citations</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Haoning Wu</xbar.author>
# <xbar.author.github>haoningwu3639</xbar.author.github>
# <xbar.desc>Displays your Google Scholar citations stats</xbar.desc>
# <xbar.dependencies>python3,requests,python-dotenv</xbar.dependencies>

# Note: Remember to replace the first line with the correct python path in your system

import os
import requests
import json
import time
from dotenv import load_dotenv
from datetime import datetime

# Get script directory
script_dir = os.path.dirname(os.path.realpath(__file__))

# Create a cache directory under your home directory if it doesn't exist
cache_dir = os.path.join(os.path.expanduser("~"), ".scholar_cache")
if not os.path.exists(cache_dir):
    try:
        os.makedirs(cache_dir)
    except Exception:
        # Fall back to using /tmp if we can't create the directory
        cache_dir = "/tmp"

# Load environment variables from script directory
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)

# You need to register for SERP API and get an API key: https://serpapi.com/
SERP_API_KEY = os.getenv("SERP_API_KEY", "YourSERPAPIKeyHere") # SERP API Key
SCHOLAR_ID = os.getenv("SCHOLAR_ID", "YourGoogleScholarIDHere")  # Google Scholar ID

# Path to cache file - now stored in a separate directory
CACHE_FILE = os.path.join(cache_dir, f"scholar_cache_{SCHOLAR_ID}.json")
# Cache expiration in seconds (8 hours to match refresh interval)
CACHE_EXPIRATION = 4 * 60 * 60

def load_cache():
    """Load cached scholar data if available and not expired"""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is expired
        if time.time() - cache_data.get("timestamp", 0) > CACHE_EXPIRATION:
            return None
        
        return cache_data.get("data")
    except Exception:
        return None

def save_cache(data):
    """Save scholar data to cache file"""
    try:
        cache_data = {
            "timestamp": time.time(),
            "data": data
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    except Exception:
        # Silently fail if we can't write to cache
        pass

def fetch_scholar_data():
    """Fetch academic data from Google Scholar with caching"""
    # Try to load from cache first
    cached_data = load_cache()
    if cached_data:
        return cached_data
    
    # If no valid cache, fetch from API
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_scholar_author",
        "author_id": SCHOLAR_ID,
        "api_key": SERP_API_KEY
    }
    
    # Disable proxies to avoid connection issues
    proxies = {
        "http": None,
        "https": None,
    }
    
    response = requests.get(url, params=params, proxies=proxies, timeout=30)
    data = response.json()
    
    # Handle error cases
    if "error" in data:
        raise Exception(f"SERP API Error: {data['error']}")
    
    result = {
        "name": "Unknown",
        "citations": 0,
        "h_index": 0,
        "i10_index": 0,
        "current_year_citations": 0,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    # Get author name
    if "author" in data and "name" in data["author"]:
        result["name"] = data["author"]["name"]
    
    # Get citation information
    if "cited_by" in data and "table" in data["cited_by"]:
        citation_table = data["cited_by"]["table"]
        
        # Get total citations
        if len(citation_table) > 0 and "citations" in citation_table[0]:
            result["citations"] = citation_table[0]["citations"]["all"]
        
        # Get h-index
        if len(citation_table) > 1 and "h_index" in citation_table[1]:
            result["h_index"] = citation_table[1]["h_index"]["all"]
        
        # Get i10-index
        if len(citation_table) > 2 and "i10_index" in citation_table[2]:
            result["i10_index"] = citation_table[2]["i10_index"]["all"]
    
    # Get current year citations
    current_year = datetime.now().year
    if "cited_by" in data and "graph" in data["cited_by"]:
        for year_data in data["cited_by"]["graph"]:
            if year_data.get("year") == current_year:
                result["current_year_citations"] = year_data.get("citations", 0)
                break
    
    # Save the successful result to cache
    save_cache(result)
    
    return result

def format_xbar_output(scholar_data):
    """Format output for xbar display"""
    name = scholar_data["name"]
    citations = scholar_data["citations"]
    h_index = scholar_data["h_index"]
    i10_index = scholar_data["i10_index"]
    current_year_citations = scholar_data["current_year_citations"]
    last_updated = scholar_data.get("last_updated", "Unknown")
    
    # Format top display with name and citations
    top_line = f"📚 {name}: {citations} | color=#4285F4 size=14"
    
    # Format dropdown menu
    dropdown = [
        "---",
        f"👤 {name} | color=#000000 size=14",
        "---",
        f"📊 Citation Statistics:",
        f"Total Citations: {citations} | color=#0F9D58",
        f"Citations This Year: {current_year_citations} | color=#F4B400",
        f"h-index: {h_index} | color=#DB4437",
        f"i10-index: {i10_index} | color=#4285F4",
        "---",
        f"🕒 Last Updated: {last_updated} | color=#7F7F7F size=12",
        "---",
        f"🔍 View on Google Scholar | href=https://scholar.google.com/citations?user={SCHOLAR_ID}",
        "---",
        "🔄 Refresh Data | refresh=true"
    ]
    
    return "\n".join([top_line] + dropdown)

if __name__ == "__main__":
    try:
        scholar_data = fetch_scholar_data()
        print(format_xbar_output(scholar_data))
    except Exception as e:
        # Try to load from cache if request fails
        cached_data = load_cache()
        if cached_data:
            # Update the cached display to also include the name
            print(f"👤 {cached_data['name']}: 📚 {cached_data['citations']} (cached) | color=#F4B400 size=14")
            print("---")
            print(f"⚠️ Using cached data | color=#F4B400")
            print(format_xbar_output(cached_data))
            print("---")
            print(f"❌ Error: {str(e)} | color=#DB4437")
        else:
            print(f"❌ Error | color=red")
            print("---")
            print(f"API Error: {str(e)} | color=#DB4437")
            print(f"Please Check Your Network | color=#7F7F7F")
            print("---")
            print("🔄 Try Again | refresh=true")