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


def get_page_content():
    r = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
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


def load_old_state():
    old = {}

    if not os.path.exists(STATE_FILE):
        return old

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "|" not in line:
                continue

            name, rating = line.strip().split("|", 1)

            try:
                old[name] = int(rating)
            except ValueError:
                continue

    return old


def save_state(current):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        for name, rating in current.items():
            f.write(f"{name}|{rating}\n")


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for item in history:
            f.write(f"{item}\n")


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


def upload_state():
    if not os.path.exists(STATE_FILE):
        return

    token = os.environ["GH_TOKEN"]
    url = "https://api.github.com/repos/iEtsh/ietsh-monitor/contents/"

    # رفع last_state.txt
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    encoded = base64.b64encode(content.encode()).decode()

    sha = None
    try:
        req = urllib.request.Request(url + "last_state.txt")
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            sha = data.get("sha")
    except Exception:
        pass

    data = {
        "message": "update state",
        "content": encoded,
        "branch": "main"
    }

    if sha:
        data["sha"] = sha

    req = urllib.request.Request(url + "last_state.txt", data=json.dumps(data).encode(), method="PUT")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        urllib.request.urlopen(req)
        print("State uploaded successfully")
    except Exception as e:
        print(f"Upload failed: {e}")

    # رفع rating_history.txt
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        encoded = base64.b64encode(content.encode()).decode()

        sha = None
        try:
            req = urllib.request.Request(url + "rating_history.txt")
            req.add_header("Authorization", f"token {token}")
            req.add_header("Accept", "application/vnd.github.v3+json")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
                sha = data.get("sha")
        except Exception:
            pass

        data = {
            "message": "update history",
            "content": encoded,
            "branch": "main"
        }

        if sha:
            data["sha"] = sha

        req = urllib.request.Request(url + "rating_history.txt", data=json.dumps(data).encode(), method="PUT")
        req.add_header("Authorization", f"token {token}")
        req.add_header("Accept", "application/vnd.github.v3+json")

        try:
            urllib.request.urlopen(req)
            print("History uploaded successfully")
        except Exception as e:
            print(f"Upload history failed: {e}")


def main():
    print(f"=== Check at {datetime.now()} ===")

    current = get_page_content()

    if not current:
        print("Could not find any puzzles. State will NOT be changed.")
        return

    print(f"Found {len(current)} puzzles")

    old = load_old_state()
    history = load_history()

    print(f"Old state contains {len(old)} puzzles")

    changes = []

    for name, new_rating in current.items():
        old_rating = old.get(name)

        if old_rating is not None and old_rating != new_rating:
            change_key = f"{name}|{old_rating}->{new_rating}"

            if change_key not in history:
                changes.append(
                    f"{name}'s rating changes from {old_rating}% to {new_rating}%."
                )
                history.add(change_key)

    save_state(current)
    save_history(history)
    print("State file updated successfully.")
    print("History updated successfully.")

    if changes:
        print("Rating changes detected:")

        for change in changes:
            print(change)

        send_email(changes)
        print("Email sent successfully.")

    else:
        print("No rating changes.")


if __name__ == "__main__":
    main()
    upload_state()