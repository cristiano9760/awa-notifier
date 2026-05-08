import os
import json
import re
import requests
from bs4 import BeautifulSoup

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

PAGE_URL = "https://in.alienwarearena.com/ucf/Giveaway"
BASE_URL = "https://in.alienwarearena.com"
SEEN_FILE = "alienware_seen.json"

FOOTER_TEXT = "Lone's AWA Notifier"
FOOTER_ICON = "https://i.imgur.com/4M34hi2.png"


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return []

    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def clean_title(title):
    bad_phrases = [
        "get your key before they run out",
        "get your keys before they run out",
        "learn more",
        "click here",
        "read more",
    ]

    title = re.sub(r"\s+", " ", title).strip()

    for phrase in bad_phrases:
        title = re.sub(phrase, "", title, flags=re.IGNORECASE)

    title = title.replace("  ", " ").strip(" -|:")

    return title


def absolute_url(url):
    if not url:
        return None

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return BASE_URL + url

    return url


def get_best_image(card):
    img = card.find("img")

    if not img:
        return None

    image = (
        img.get("data-src")
        or img.get("data-original")
        or img.get("data-lazy")
        or img.get("src")
    )

    return absolute_url(image)


def is_active_giveaway(card):
    text = card.get_text(" ", strip=True).lower()

    expired_words = [
        "expired",
        "ended",
        "no keys left",
        "out of keys",
        "out of stock",
        "all keys have been claimed",
        "this giveaway has ended",
        "keys are currently unavailable",
    ]

    for word in expired_words:
        if word in text:
            return False

    return True


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

        card = link.find_parent(["div", "article", "li", "section"])

        if not card:
            card = link.parent

        if not is_active_giveaway(card):
            continue

        title = clean_title(link.get_text(" ", strip=True))

        if not title:
            continue

        url = absolute_url(href)
        image = get_best_image(card)

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
            "icon_url": "https://i.imgur.com/9rZg6Yk.png"
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
        print("No new active Alienware giveaways.")
        return

    for giveaway in reversed(new_giveaways):
        send_discord(giveaway)
        print("Sent:", giveaway["title"])

    save_seen([g["url"] for g in giveaways])


if __name__ == "__main__":
    main()