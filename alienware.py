import os, json, re, time, requests
from bs4 import BeautifulSoup

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

PAGE_URL = "https://in.alienwarearena.com/ucf/Giveaway"
BASE_URL = "https://in.alienwarearena.com"
SEEN_FILE = "alienware_seen.json"

FOOTER_TEXT = "Lone's AWA Notifier"
FOOTER_ICON = "https://i.imgur.com/4M34hi2.png"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return []
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def absolute_url(url):
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    return url


def clean_title(title):
    title = re.sub(r"\s+", " ", title).strip()
    title = title.replace("Get your key before they run out!", "")
    title = title.replace("Get your keys before they run out!", "")
    title = title.replace("Learn More", "")
    title = title.replace("LEARN MORE", "")
    return title.strip(" -|:")


def get_page_image(soup):
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        return absolute_url(meta["content"])

    meta = soup.find("meta", attrs={"name": "twitter:image"})
    if meta and meta.get("content"):
        return absolute_url(meta["content"])

    return None


def is_expired(text):
    text = text.lower()

    expired_phrases = [
        "all out",
        "there are no more keys left in this giveaway",
        "no more keys left",
        "out of keys",
        "giveaway has ended",
        "expired"
    ]

    return any(phrase in text for phrase in expired_phrases)


def get_giveaway_links():
    html = requests.get(PAGE_URL, headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "/ucf/show/" not in href or "/Giveaway/" not in href:
            continue

        title = clean_title(a.get_text(" ", strip=True))
        url = absolute_url(href)

        if title and url:
            links.append({"title": title, "url": url})

    unique = []
    used = set()

    for item in links:
        if item["url"] not in used:
            unique.append(item)
            used.add(item["url"])

    return unique


def fetch_detail(item):
    html = requests.get(item["url"], headers=HEADERS, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    expired = is_expired(text)
    image = get_page_image(soup)

    return {
        "title": item["title"],
        "url": item["url"],
        "image": image,
        "expired": expired
    }


def send_discord(giveaway):
    status = "Expired / All Out" if giveaway["expired"] else "Active - Keys Available"

    embed = {
        "author": {
            "name": "Alienware Arena - Giveaway",
            "icon_url": "https://i.imgur.com/9rZg6Yk.png"
        },
        "title": giveaway["title"],
        "url": giveaway["url"],
        "description": f"**Status:** {status}",
        "color": 0x7A35FF,
        "footer": {
            "text": FOOTER_TEXT,
            "icon_url": FOOTER_ICON
        }
    }

    if giveaway["image"]:
        embed["image"] = {"url": giveaway["image"]}

    requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=20).raise_for_status()


def main():
    seen = load_seen()
    links = get_giveaway_links()

    print("Found giveaway links:", len(links))

    new_links = [x for x in links if x["url"] not in seen]

    print("New giveaway links:", len(new_links))

    if not new_links:
        print("No new giveaways.")
        return

    successfully_handled = []

    for item in reversed(new_links):
        giveaway = fetch_detail(item)

        print(giveaway["title"], "=>", "EXPIRED" if giveaway["expired"] else "ACTIVE")

        # Change this to False if you want expired ones posted too
        POST_EXPIRED = True

        if giveaway["expired"] and not POST_EXPIRED:
            continue

        send_discord(giveaway)
        successfully_handled.append(giveaway["url"])
        print("Posted:", giveaway["title"])

    save_seen(seen + successfully_handled)


if __name__ == "__main__":
    main()