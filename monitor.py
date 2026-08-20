import requests
from bs4 import BeautifulSoup
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import base64
import urllib.request
import json

URL = "https://logic-masters.de/Raetselportal/Benutzer/eingestellt.php?name=iEtsh"
STATE_FILE = "last_state.txt"
HISTORY_FILE = "rating_history.txt"
REPO = "iEtsh/ietsh-monitor"
TOKEN = os.environ.get("GH_TOKEN", "")
API = f"https://api.github.com/repos/{REPO}/contents/"


def get_page_content():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"class": "rp_raetselliste"})
    if not table:
        return {}
    puzzles = {}
    for row in table.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        name_tag = cols[1].find("a")
        if not name_tag:
            continue
        name = name_tag.get_text(strip=True)
        rating_tag = cols[3].find("span")
        if not rating_tag:
            continue
        rating_text = rating_tag.get_text(strip=True)
        try:
            rating = int(rating_text.replace("%", "").strip())
        except ValueError:
            continue
        puzzles[name] = rating
    return puzzles


def github_get(path):
    req = urllib.request.Request(API + path)
    req.add_header("Authorization", f"token {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            content = data.get("content", "")
            return base64.b64decode(content).decode("utf-8"), data.get("sha")
    except Exception:
        return None, None


def github_put(path, content, sha=None, message="update"):
    encoded = base64.b64encode(content.encode("utf-8")).decode()
    data = {"message": message, "content": encoded, "branch": "main"}
    if sha:
        data["sha"] = sha
    req = urllib.request.Request(API + path, data=json.dumps(data).encode(), method="PUT")
    req.add_header("Authorization", f"token {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"Upload failed for {path}: {e}")
        return False


def load_state_from_github():
    content, _ = github_get(STATE_FILE)
    if not content:
        return {}
    old = {}
    for line in content.splitlines():
        if "|" in line:
            name, rating = line.strip().split("|", 1)
            try:
                old[name] = int(rating)
            except ValueError:
                pass
    return old


def load_history_from_github():
    content, _ = github_get(HISTORY_FILE)
    if not content:
        return set()
    return set(line.strip() for line in content.splitlines() if line.strip())


def send_email(changes):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = sender
    lines = "\n".join(changes)
    msg = MIMEText(lines, "plain", "utf-8")
    msg["Subject"] = "🚨 Rating changes on iEtsh puzzles"
    msg["From"] = sender
    msg["To"] = receiver
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)


def main():
    print(f"=== Check at {datetime.now()} ===")
    current = get_page_content()
    if not current:
        print("No puzzles found")
        return

    old = load_state_from_github()
    history = load_history_from_github()

    changes = []
    for name, new_rating in current.items():
        old_rating = old.get(name)
        if old_rating is not None and old_rating != new_rating:
            change_key = f"{name}|{old_rating}->{new_rating}"
            if change_key not in history:
                changes.append(f"{name}'s rating changes from {old_rating}% to {new_rating}%.")
                history.add(change_key)

    state_content = "\n".join(f"{n}|{r}" for n, r in current.items()) + "\n"
    history_content = "\n".join(sorted(history)) + "\n"

    github_put(STATE_FILE, state_content, message="update state")
    github_put(HISTORY_FILE, history_content, message="update history")

    if changes:
      # send_email(changes)
        print("Email sent for changes:")
        for c in changes:
            print(c)
    else:
        print("No new rating changes.")


if __name__ == "__main__":
    main()