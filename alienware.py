import os, json, re, requests
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

    remove_parts = [
        "Get your key before they run out!",
        "Get your keys before they run out!",
        "LEARN MORE",
        "Learn More",
        "learn more",
    ]

    for part in remove_parts:
        title = title.replace(part, "")

    return title.strip(" -|:")


def has_keys(page_text):
    text = page_text.lower()

    if "get key" in text:
        return True

    return False


def get_page_image(soup):
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        return absolute_url(meta["content"])

    meta = soup.find("meta", attrs={"name": "twitter:image"})
    if meta and meta.get("content"):
        return absolute_url(meta["content"])

    imgs = soup.find_all("img")

    for img in imgs:
        src = img.get("data-src") or img.get("src")
        src = absolute_url(src)

        if src and "giveaway" in src.lower():
            return src

    for img in imgs:
        src = img.get("data-src") or img.get("src")
        src = absolute_url(src)

        if src and "alienwarearena" in src.lower():
            return src

    return None


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

        if not title or not url:
            continue

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

    if not has_keys(text):
        print("Skipped out of stock:", item["title"])
        return None

    
    title = item["title"]
    image = get_page_image(soup)

    return {
        "title": title,
        "url": item["url"],
        "image": image
    }


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

    if giveaway["image"]:
        embed["image"] = {"url": giveaway["image"]}

    requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=20).raise_for_status()


def main():
    seen = load_seen()
    links = get_giveaway_links()

    current_urls = [x["url"] for x in links]
    new_links = links

    if not new_links:
        print("No new Alienware giveaways.")
        return

    for item in reversed(new_links):
        giveaway = fetch_detail(item)

        if giveaway:
            send_discord(giveaway)
            print("Sent:", giveaway["title"])

    save_seen(current_urls)


if __name__ == "__main__":
    main()