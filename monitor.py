import requests
from bs4 import BeautifulSoup
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

URL = "https://logic-masters.de/Raetselportal/Benutzer/eingestellt.php?name=iEtsh"
STATE_FILE = "last_state.txt"


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
        print("Could not find any puzzles. State will NOT be changed.")
        return

    print(f"Found {len(current)} puzzles")

    old = load_old_state()

    print(f"Old state contains {len(old)} puzzles")

    changes = []

    for name, new_rating in current.items():
        old_rating = old.get(name)

        if old_rating is not None and old_rating != new_rating:
            changes.append(
                f"{name}'s rating changes from {old_rating}% to {new_rating}%."
            )

    if changes:
        print("Rating changes detected:")

        for change in changes:
            print(change)

        send_email(changes)
        print("Email sent successfully.")

    else:
        print("No rating changes.")

    save_state(current)
    print("State file updated successfully.")


if __name__ == "__main__":
    main()