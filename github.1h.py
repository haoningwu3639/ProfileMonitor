#!/usr/bin/python3
# -*- coding: utf-8 -*-
# <xbar.title>GitHub Status Monitor</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Haoning Wu</xbar.author>
# <xbar.author.github>haoningwu3639</xbar.author.github>
# <xbar.desc>Displays your GitHub stats, recent activities, and repository stars</xbar.desc>
# <xbar.dependencies>python3,requests,python-dotenv</xbar.dependencies>

# Note: Remember to replace the first line with the correct python path in your system

import os
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Get script directory
script_dir = os.path.dirname(os.path.realpath(__file__))

# Create a cache directory under your home directory if it doesn't exist
cache_dir = os.path.join(os.path.expanduser("~"), ".github_cache")
if not os.path.exists(cache_dir):
    try:
        os.makedirs(cache_dir)
    except Exception:
        # Fall back to using /tmp if we can't create the directory
        cache_dir = "/tmp"

# Load environment variables
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)

# GitHub API Configuration
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "YourGithubUserNameHere") # Replace with your GitHub username
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YourGithubTokenHere")  # Personal Access Token with appropriate permissions
# List of repositories to monitor (format: "owner/repo")
MONITORED_REPOS = os.getenv("MONITORED_REPOS", "YourGithubRepositoryHere").split(",")

# API endpoints
GITHUB_API = "https://api.github.com"
USER_ENDPOINT = f"{GITHUB_API}/users/{GITHUB_USERNAME}"
REPOS_ENDPOINT = f"{GITHUB_API}/users/{GITHUB_USERNAME}/repos"
STARRED_ENDPOINT = f"{GITHUB_API}/users/{GITHUB_USERNAME}/starred"
FOLLOWING_ENDPOINT = f"{GITHUB_API}/users/{GITHUB_USERNAME}/following"
RECEIVED_EVENTS_ENDPOINT = f"{GITHUB_API}/users/{GITHUB_USERNAME}/received_events"

# Caching
CACHE_FILE = os.path.join(cache_dir, f"github_cache_{GITHUB_USERNAME}.json")
EVENTS_CACHE_FILE = os.path.join(cache_dir, f"github_events_cache_{GITHUB_USERNAME}.json")
# Cache expiration in seconds (1 hour to match refresh interval)
CACHE_EXPIRATION = 60 * 60

def make_github_request(url, params=None):
    """Make authenticated request to GitHub API"""
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Add token auth if available
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    
    # Check if rate limited
    if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
        if response.headers['X-RateLimit-Remaining'] == '0':
            reset_time = datetime.fromtimestamp(int(response.headers['X-RateLimit-Reset']))
            raise Exception(f"GitHub API rate limit exceeded. Resets at {reset_time}")
    
    response.raise_for_status()
    return response.json()

def load_cache(cache_file=CACHE_FILE):
    """Load cached data if available and not expired"""
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is expired
        if time.time() - cache_data.get("timestamp", 0) > CACHE_EXPIRATION:
            return None
        
        return cache_data.get("data")
    except Exception:
        return None

def save_cache(data, cache_file=CACHE_FILE):
    """Save data to cache file"""
    try:
        cache_data = {
            "timestamp": time.time(),
            "data": data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    except Exception:
        # Silently fail if we can't write to cache
        pass

def fetch_user_data():
    """Fetch basic user information"""
    return make_github_request(USER_ENDPOINT)

def fetch_repos_data():
    """Fetch repositories data"""
    all_repos = []
    page = 1
    while True:
        params = {"page": page, "per_page": 100}
        repos = make_github_request(REPOS_ENDPOINT, params)
        if not repos:
            break
        all_repos.extend(repos)
        page += 1
    return all_repos

def fetch_stars_received():
    """Calculate total stars received across all repositories"""
    repos = fetch_repos_data()
    return sum(repo["stargazers_count"] for repo in repos)

def fetch_monitored_repos_data():
    """Fetch data for specifically monitored repositories"""
    result = []
    for repo_full_name in MONITORED_REPOS:
        if not repo_full_name.strip():
            continue
        try:
            repo_data = make_github_request(f"{GITHUB_API}/repos/{repo_full_name.strip()}")
            result.append({
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "url": repo_data["html_url"],
                "stars": repo_data["stargazers_count"],
                "forks": repo_data["forks_count"]
            })
        except Exception:
            continue
    return result

def fetch_recent_stars_by_following():
    """Fetch events where people you follow starred repos"""
    events = make_github_request(RECEIVED_EVENTS_ENDPOINT, {"per_page": 30})
    
    # Filter for WatchEvents (stars)
    star_events = []
    for event in events:
        if event["type"] == "WatchEvent":
            star_events.append({
                "actor": event["actor"]["login"],
                "repo_name": event["repo"]["name"],
                "repo_url": f"https://github.com/{event['repo']['name']}",
                "time": event["created_at"]
            })
            
            if len(star_events) >= 5:  # Limit to 5 most recent star events
                break
                
    return star_events

def fetch_github_data():
    """Fetch all required GitHub data with caching"""
    # Try to load from cache first
    cached_data = load_cache()
    if cached_data:
        return cached_data
    
    # If no valid cache, fetch from API
    user_data = fetch_user_data()
    stars_received = fetch_stars_received()
    monitored_repos = fetch_monitored_repos_data()
    recent_stars = fetch_recent_stars_by_following()
    
    result = {
        "username": user_data["login"],
        "name": user_data.get("name", user_data["login"]),
        "avatar_url": user_data["avatar_url"],
        "followers": user_data["followers"],
        "following": user_data["following"],
        "public_repos": user_data["public_repos"],
        "stars_received": stars_received,
        "monitored_repos": monitored_repos,
        "recent_stars": recent_stars,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    # Save the successful result to cache
    save_cache(result)
    
    return result

def format_xbar_output(github_data):
    """Format output for xbar display"""
    username = github_data["username"]
    name = github_data["name"]
    stars_received = github_data["stars_received"]
    followers = github_data["followers"]
    monitored_repos = github_data["monitored_repos"]
    recent_stars = github_data["recent_stars"]
    last_updated = github_data.get("last_updated", "Unknown")
    
    # Format top display with name and stars
    top_line = f"⭐ {name}: {stars_received} | color=#6e5494 size=14"
    
    # Format dropdown menu
    dropdown = [
        "---",
        f"👤 {name} (@{username}) | color=#000000 size=14",
        "---",
        f"📊 GitHub Statistics:",
        f"⭐ Total Stars Received: {stars_received} | color=#E3B341",
        f"👥 Followers: {followers} | color=#6e5494",
        f"🗂 Public Repositories: {github_data['public_repos']} | color=#238636",
        "---",
        f"📌 Monitored Repositories:"
    ]
    
    # Add monitored repos info
    for repo in monitored_repos:
        dropdown.append(f"• {repo['name']}: ⭐ {repo['stars']} | href={repo['url']} color=#0969DA")
    
    # Add recent stars section
    if recent_stars:
        dropdown.append("---")
        dropdown.append(f"🔔 Recently Starred by People You Follow:")
        for star in recent_stars:
            # Format timestamp to be more readable
            timestamp = datetime.strptime(star["time"], "%Y-%m-%dT%H:%M:%SZ")
            # Convert to local time
            time_diff = datetime.now() - timestamp
            
            if time_diff.days > 0:
                time_str = f"{time_diff.days}d ago"
            elif time_diff.seconds // 3600 > 0:
                time_str = f"{time_diff.seconds // 3600}h ago"
            else:
                time_str = f"{time_diff.seconds // 60}m ago"
                
            dropdown.append(f"• {star['actor']} → {star['repo_name']} ({time_str}) | href={star['repo_url']} color=#0969DA")
    
    # Add footer
    dropdown.extend([
        "---",
        f"🕒 Last Updated: {last_updated} | color=#7F7F7F size=12",
        "---",
        f"🔍 View Profile | href=https://github.com/{username}",
        "---",
        "🔄 Refresh Data | refresh=true"
    ])
    
    return "\n".join([top_line] + dropdown)

if __name__ == "__main__":
    try:
        github_data = fetch_github_data()
        print(format_xbar_output(github_data))
    except Exception as e:
        # Try to load from cache if request fails
        cached_data = load_cache()
        if cached_data:
            print(f"⭐ {cached_data['name']}: {cached_data['stars_received']} (cached) | color=#F4B400 size=14")
            print("---")
            print(f"⚠️ Using cached data | color=#F4B400")
            print(format_xbar_output(cached_data))
            print("---")
            print(f"❌ Error: {str(e)} | color=#DB4437")
        else:
            print(f"❌ GitHub | color=red")
            print("---")
            print(f"API Error: {str(e)} | color=#DB4437")
            print(f"Please check your configuration and network | color=#7F7F7F")
            print("---")
            print("🔄 Try Again | refresh=true")