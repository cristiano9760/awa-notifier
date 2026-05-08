import os
import json
import requests
from bs4 import BeautifulSoup

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

PAGE_URL = "https://in.alienwarearena.com/ucf/Giveaway"
BASE_URL = "https://in.alienwarearena.com"
SEEN_FILE = "alienware_seen.json"

FOOTER_TEXT = "Subho's AWA Notifier"
FOOTER_ICON = "https://files.catbox.moe/qttqpy.png"


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return []

    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def fetch_giveaways():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(PAGE_URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    giveaways = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/ucf/show/" not in href or "/Giveaway/" not in href:
            continue

        url = href if href.startswith("http") else BASE_URL + href
        title = link.get_text(" ", strip=True)

        if not title:
            title = "Alienware Arena Giveaway"

        image = None

        parent = link.find_parent()
        if parent:
            img = parent.find("img")
            if img:
                image = img.get("src") or img.get("data-src")

        if image and image.startswith("/"):
            image = BASE_URL + image

        giveaways.append({
            "title": title,
            "url": url,
            "image": image
        })

    unique = []
    used_urls = set()

    for giveaway in giveaways:
        if giveaway["url"] not in used_urls:
            unique.append(giveaway)
            used_urls.add(giveaway["url"])

    return unique


def send_discord(giveaway):
    embed = {
        "author": {
            "name": "Alienware Arena - Giveaway",
            "icon_url": "https://files.catbox.moe/46sipy.png"
        },
        "title": giveaway["title"],
        "url": giveaway["url"],
        "color": 0x7A35FF,
        "footer": {
            "text": FOOTER_TEXT,
            "icon_url": FOOTER_ICON
        }
    }

    if giveaway.get("image"):
        embed["image"] = {
            "url": giveaway["image"]
        }

    payload = {
        "embeds": [embed]
    }

    r = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    r.raise_for_status()


def main():
    seen = load_seen()
    giveaways = fetch_giveaways()

    new_giveaways = [g for g in giveaways if g["url"] not in seen]

    if not new_giveaways:
        print("No new Alienware Arena giveaways.")
        return

    for giveaway in reversed(new_giveaways):
        send_discord(giveaway)
        print("Sent:", giveaway["title"])

    save_seen([g["url"] for g in giveaways])


if __name__ == "__main__":
    main()
