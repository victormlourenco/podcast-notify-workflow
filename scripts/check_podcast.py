#!/usr/bin/env python3
import os
import json
import hashlib
import html
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

RSS_URL = os.environ.get("RSS_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS = [cid.strip() for cid in os.environ.get("TELEGRAM_CHAT_IDS", "").split(",") if cid.strip()]
STATE_FILE = Path("data/last_episode_hash.txt")

def strip_html_tags(text):
    """Remove HTML tags from text."""
    from html.parser import HTMLParser
    
    class MLStripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.reset()
            self.strict = False
            self.convert_charrefs = True
            self.text = []
        
        def handle_data(self, d):
            self.text.append(d)
        
        def get_data(self):
            return ''.join(self.text)
    
    stripper = MLStripper()
    stripper.feed(text)
    return stripper.get_data()

def fetch_rss_feed():
    with urlopen(RSS_URL, timeout=30) as response:
        return response.read().decode("utf-8")

def parse_latest_episode(rss_content):
    root = ET.fromstring(rss_content)
    channel = root.find("channel")
    if channel is None:
        return None
    
    item = channel.find("item")
    if item is None:
        return None
    
    return {
        "guid": item.findtext("guid", ""),
        "title": item.findtext("title", ""),
        "description": strip_html_tags(item.findtext("description", "")),
        "podcast_title": channel.findtext("title", "Podcast"),
    }

def get_episode_hash(episode):
    return hashlib.sha256(episode["guid"].encode()).hexdigest()

def load_last_hash():
    if not STATE_FILE.exists():
        return None
    try:
        return STATE_FILE.read_text().strip()
    except IOError:
        return None

def save_last_hash(episode_hash):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(episode_hash)

def send_telegram_notification(episode):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("Telegram credentials not configured. Skipping notification.")
        return
    
    message = (
        f"🎙️{episode['podcast_title']}\n\n"
        f"{episode['title']}\n\n"
        f"{episode['description']}"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    for chat_id in TELEGRAM_CHAT_IDS:
        payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        
        try:
            with urlopen(req, timeout=30) as response:
                print(f"Notification sent to {chat_id}")
        except URLError as e:
            print(f"Failed to send to {chat_id}: {e}")

def main():
    print("Fetching RSS feed...")
    
    try:
        rss_content = fetch_rss_feed()
    except URLError as e:
        print(f"Failed to fetch RSS feed: {e}")
        return
    
    latest_episode = parse_latest_episode(rss_content)
    
    if not latest_episode:
        print("Could not parse any episodes from the feed.")
        return
    
    print(f"Latest episode: {latest_episode['title']}")
    
    current_hash = get_episode_hash(latest_episode)
    last_hash = load_last_hash()
    
    if last_hash is None:
        print("First run - saving current episode hash as baseline.")
        save_last_hash(current_hash)
        return
    
    if current_hash != last_hash:
        print(f"New episode detected: {latest_episode['title']}")
        send_telegram_notification(latest_episode)
        save_last_hash(current_hash)
    else:
        print("No new episodes.")


if __name__ == "__main__":
    main()