import os
import requests
import re
from datetime import datetime, timedelta
from collections import defaultdict

# GitHub credentials and settings
GITHUB_TOKEN = os.getenv("GH_TOKEN")
USERNAME = os.getenv("GH_USERNAME", "Nzettodess")

headers = {
    "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else "",
    "Accept": "application/vnd.github.v3+json",
}

def get_repos():
    if not GITHUB_TOKEN:
        print("GH_TOKEN is not set. Fetching public repos only (rate limited).")
        
    url = f"https://api.github.com/user/repos?per_page=100&affiliation=owner"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch repos: {response.status_code}")
        return []
    return response.json()

def generate_stats_and_languages(repos):
    total_stars = 0
    total_forks = 0
    total_repos = len(repos)
    language_bytes = defaultdict(int)
    
    one_year_ago = datetime.now() - timedelta(days=365)
    
    for repo in repos:
        total_stars += repo.get('stargazers_count', 0)
        total_forks += repo.get('forks_count', 0)
        
        # Filter languages by repositories updated in the last 365 days
        updated_at_str = repo.get('updated_at')
        if updated_at_str:
            updated_at = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ")
            if updated_at > one_year_ago:
                lang_url = repo.get('languages_url')
                if lang_url:
                    lang_resp = requests.get(lang_url, headers=headers)
                    if lang_resp.status_code == 200:
                        langs = lang_resp.json()
                        for lang, bytes_count in langs.items():
                            language_bytes[lang] += bytes_count

    # Fetch Total Commits and Average per month (Last Year constraint)
    total_commits = 0
    search_headers = headers.copy()
    search_headers["Accept"] = "application/vnd.github.cloak-preview"
    
    # Calculate date for last year query
    last_year_date = one_year_ago.strftime("%Y-%m-%d")
    commit_url = f"https://api.github.com/search/commits?q=author:{USERNAME} committer-date:>{last_year_date}"
    commit_resp = requests.get(commit_url, headers=search_headers)
    if commit_resp.status_code == 200:
        total_commits = commit_resp.json().get('total_count', 0)
        
    # Get user creation date for Account Age
    account_age_str = "Unknown"
    user_url = f"https://api.github.com/users/{USERNAME}"
    user_resp = requests.get(user_url, headers=headers)
    if user_resp.status_code == 200:
        created_at_str = user_resp.json().get('created_at')
        if created_at_str:
            created_at = datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%SZ")
            days_active = (datetime.now() - created_at).days
            years = days_active // 365
            months = (days_active % 365) // 30
            account_age_str = f"{years} yrs, {months} mos"

    # Generate Stats Table
    stats_content = (
        f"| 📊 Metric | Count |\n"
        f"|---|---|\n"
        f"| 📦 Total Repositories | {total_repos} |\n"
        f"| ⭐ Total Stars Earned | {total_stars} |\n"
        f"| 💻 Commits (Last Year)| {total_commits} |\n"
        f"| ⏳ Account Age | {account_age_str} |"
    )
    
    # Generate Mermaid Pie Chart
    mermaid_lines = [
        "```mermaid",
        "%%{init: {'theme': 'dark', 'themeVariables': { 'pie1': '#FF0055', 'pie2': '#00E5FF', 'pie3': '#FFEA00', 'pie4': '#00E676', 'pie5': '#D500F9' }}}%%",
        "pie title Top Languages (Active Repos)"
    ]
    
    if language_bytes:
        total_bytes = sum(language_bytes.values())
        sorted_langs = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)
        
        other_percent = 0.0
        for lang, count in sorted_langs:
            percent = (count / total_bytes) * 100
            if percent >= 3.0:
                mermaid_lines.append(f'    "{lang}" : {percent:.2f}')
            else:
                other_percent += percent
                
        if other_percent > 0:
            mermaid_lines.append(f'    "Other" : {other_percent:.2f}')
    else:
        mermaid_lines.append('    "No Data" : 100')
        
    mermaid_lines.append("```")
    mermaid_content = "\n".join(mermaid_lines)
    
    return stats_content, mermaid_content

def get_recent_activity():
    url = f"https://api.github.com/users/{USERNAME}/events"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return ["- Failed to fetch recent activity."]
        
    events = response.json()
    activity_lines = []
    
    # Track recent stars instead of pushes!
    watch_events = [e for e in events if e['type'] == 'WatchEvent']
    
    for event in watch_events[:5]:
        repo_name = event['repo']['name']
        date_str = datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        display_repo = f"[{repo_name}](https://github.com/{repo_name})"
        activity_lines.append(f"- ⭐ Starred {display_repo} on {date_str}")
            
    if not activity_lines:
        return ["- No recent starred repositories found."]
    return activity_lines

def update_readme(stats_content, languages_content, activity_lines):
    activity_content = "\n".join(activity_lines)
    
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()
        
    # Replace contents between tags
    def replace_section(name, new_content, text):
        pattern = re.compile(rf"(<!-- START_SECTION:{name} -->\n).*?(\n<!-- END_SECTION:{name} -->)", re.DOTALL)
        return pattern.sub(rf"\g<1>{new_content}\g<2>", text)

    readme = replace_section("stats", stats_content, readme)
    readme = replace_section("languages", languages_content, readme)
    readme = replace_section("activity", activity_content, readme)
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)

if __name__ == "__main__":
    print("Fetching repos for stats and languages...")
    repos = get_repos()
    stats, langs = generate_stats_and_languages(repos)
    
    print("Fetching recent activity...")
    activity = get_recent_activity()
    
    print("Updating README.md...")
    update_readme(stats, langs, activity)
    print("Done!")
