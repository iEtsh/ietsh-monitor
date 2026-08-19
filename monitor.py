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
    # بنجيب الجدول كامل اللي فيه الألغاز والتقييمات
    table = soup.find("table", {"class": "result"})
    if table:
        return str(table)
    return soup.get_text()

def send_email(change):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = os.environ["EMAIL_USER"]

    msg = MIMEText(change)
    msg["Subject"] = "🚨 تغيير في صفحة iEtsh"
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

def main():
    content = get_page_content()
    current_hash = hashlib.sha256(content.encode()).hexdigest()

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            old_hash = f.read().strip()
        if old_hash != current_hash:
            send_email(f"تغيير في التقييمات:\n{URL}")
    else:
        pass

    with open(STATE_FILE, "w") as f:
        f.write(current_hash)

if __name__ == "__main__":
    main()