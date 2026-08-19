import requests
from bs4 import BeautifulSoup
import hashlib
import os
import smtplib
from email.mime.text import MIMEText

URL = "https://logic-masters.de/Raetselportal/Benutzer/eingestellt.php?name=iEtsh"
STATE_FILE = "last_state.txt"

def get_page_content():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"class": "result"})
    if not table:
        return {}
    rows = table.find_all("tr")
    puzzles = {}
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            name = cols[0].get_text(strip=True)
            rating_text = cols[1].get_text(strip=True)
            try:
                rating = int(rating_text.replace("%", "").strip())
            except:
                rating = rating_text
            puzzles[name] = rating
    return puzzles

def send_email(changes):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = os.environ["EMAIL_USER"]

    lines = "\n".join(changes)
    msg = MIMEText(lines)
    msg["Subject"] = "🚨 تغيير في تقييمات iEtsh"
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

def main():
    current = get_page_content()
    if not current:
        return

    old = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            for line in f:
                if "|" in line:
                    name, rating = line.strip().split("|", 1)
                    try:
                        old[name] = int(rating)
                    except:
                        old[name] = rating

    changes = []
    for name, new_rating in current.items():
        old_rating = old.get(name)
        if old_rating is not None and old_rating != new_rating:
            changes.append(f"{name}'s rating changes from {old_rating} to {new_rating}.")

    if changes:
        send_email(changes)

    with open(STATE_FILE, "w") as f:
        for name, rating in current.items():
            f.write(f"{name}|{rating}\n")

if __name__ == "__main__":
    main()
