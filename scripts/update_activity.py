import os
import requests
import re
from datetime import datetime

# GitHub credentials and settings
GITHUB_TOKEN = os.getenv("GH_TOKEN")
USERNAME = os.getenv("GH_USERNAME", "Nzettodess")

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

def get_recent_activity():
    if not GITHUB_TOKEN:
        print("GH_TOKEN is not set. Exiting.")
        return []
        
    url = f"https://api.github.com/users/{USERNAME}/events"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch activity: {response.status_code}")
        return []
        
    events = response.json()
    activity_lines = []
    
    # Process the most recent push events
    push_events = [e for e in events if e['type'] == 'PushEvent']
    
    for event in push_events[:5]: # Get top 5 recent pushes
        repo_name = event['repo']['name']
        is_public = event.get('public', True)
        
        # Check if repo is actually private (sometimes events API doesn't fully clarify without checking repo details)
        # We can do a quick check on the repo API, or just use the event's public flag.
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
            commit_msg = commits[0]['message'].split('\n')[0] # Get first line of latest commit
            if len(commit_msg) > 50:
                commit_msg = commit_msg[:47] + "..."
                
            activity_lines.append(f"- 📅 {date_str} - Pushed {commit_count} commit(s) to {display_repo}: `{commit_msg}`")
            
    return activity_lines

def update_readme(activity_lines):
    if not activity_lines:
        activity_lines = ["- No recent activity found or token missing."]
        
    activity_content = "\n".join(activity_lines)
    
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()
        
    # Replace content between tags
    pattern = re.compile(r"(<!-- START_SECTION:activity -->\n).*?(\n<!-- END_SECTION:activity -->)", re.DOTALL)
    new_readme = pattern.sub(rf"\g<1>{activity_content}\g<2>", readme)
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)

if __name__ == "__main__":
    lines = get_recent_activity()
    update_readme(lines)
    print("README updated successfully.")
