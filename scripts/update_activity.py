import os
import requests
import re
from datetime import datetime
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
    
    for repo in repos:
        total_stars += repo.get('stargazers_count', 0)
        total_forks += repo.get('forks_count', 0)
        
        # Fetch languages for this repo
        lang_url = repo.get('languages_url')
        if lang_url:
            lang_resp = requests.get(lang_url, headers=headers)
            if lang_resp.status_code == 200:
                langs = lang_resp.json()
                for lang, bytes_count in langs.items():
                    language_bytes[lang] += bytes_count

    # Fetch Total Commits using Search API
    total_commits = 0
    search_headers = headers.copy()
    search_headers["Accept"] = "application/vnd.github.cloak-preview" # Needed for commit search API
    commit_url = f"https://api.github.com/search/commits?q=author:{USERNAME}"
    commit_resp = requests.get(commit_url, headers=search_headers)
    if commit_resp.status_code == 200:
        total_commits = commit_resp.json().get('total_count', 0)

    # Generate Stats Table
    stats_content = (
        f"| 📊 Metric | Count |\n"
        f"|---|---|\n"
        f"| 📦 Total Repositories | {total_repos} |\n"
        f"| ⭐ Total Stars | {total_stars} |\n"
        f"| 🍴 Total Forks | {total_forks} |\n"
        f"| 💻 Total Commits | {total_commits} |"
    )
    
    # Generate Mermaid Pie Chart
    mermaid_lines = ["```mermaid", "pie title Top Languages"]
    
    if language_bytes:
        total_bytes = sum(language_bytes.values())
        # Sort by usage and take top 8
        sorted_langs = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:8]
        for lang, count in sorted_langs:
            percent = (count / total_bytes) * 100
            if percent > 0.5: # Only show languages > 0.5%
                mermaid_lines.append(f'    "{lang}" : {percent:.2f}')
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
    push_events = [e for e in events if e['type'] == 'PushEvent']
    
    for event in push_events[:5]:
        repo_name = event['repo']['name']
        
        repo_url = f"https://api.github.com/repos/{repo_name}"
        repo_resp = requests.get(repo_url, headers=headers).json()
        
        if repo_resp.get('private', False):
            display_repo = "🔒 private repo"
        else:
            display_repo = f"[{repo_name}](https://github.com/{repo_name})"
            
        commits = event['payload'].get('commits', [])
        commit_count = len(commits)
        
        if commit_count > 0:
            date_str = datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
            commit_msg = commits[0]['message'].split('\n')[0]
            if len(commit_msg) > 50:
                commit_msg = commit_msg[:47] + "..."
            activity_lines.append(f"- 📅 {date_str} - Pushed {commit_count} commit(s) to {display_repo}: `{commit_msg}`")
            
    if not activity_lines:
        return ["- No recent push activity found."]
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
