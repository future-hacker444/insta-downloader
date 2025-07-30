import streamlit as st
import instaloader
import re
import os
import time
import requests
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Disable login prompt
loader = instaloader.Instaloader()
loader.login_prompt = False

# Create base folder
if not os.path.exists("downloads"):
    os.makedirs("downloads")

def get_content_type(url):
    if "/reel/" in url:
        return "reel"
    elif "/p/" in url:
        return "post"
    elif "/stories/" in url:
        return "story"
    return "unknown"

def download_post(url, choice):
    match = re.search(r"/p/([^/]+)/", url)
    if not match:
        st.error("❌ Invalid post URL")
        return

    shortcode = match.group(1)
    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        folder = os.path.join("downloads", "posts", post.owner_username)
        os.makedirs(folder, exist_ok=True)

        if choice in ["media", "both"]:
            loader.download_post(post, target=folder)

        if choice in ["caption", "both"]:
            caption_path = os.path.join(folder, f"{shortcode}_caption.txt")
            with open(caption_path, "w", encoding="utf-8") as f:
                f.write(post.caption or "")
        st.success("✅ Post downloaded!")
    except Exception as e:
        st.error(f"❌ Error: {e}")

def download_story(url):
    match = re.search(r"instagram\.com/stories/([^/]+)/", url)
    if not match:
        st.error("❌ Invalid story URL")
        return

    username = match.group(1)
    try:
        profile = instaloader.Profile.from_username(loader.context, username)
        stories = loader.get_stories(userids=[profile.userid])
        folder = os.path.join("downloads", "stories", username)
        os.makedirs(folder, exist_ok=True)

        found = False
        for story in stories:
            for item in story.get_items():
                loader.download_storyitem(item, target=folder)
                found = True

        if found:
            st.success("✅ Stories downloaded!")
        else:
            st.warning("⚠️ No active stories found.")
    except Exception as e:
        st.error(f"❌ Error: {e}")

def download_reel_with_selenium(url):
    try:
        folder = os.path.join("downloads", "reels")
        os.makedirs(folder, exist_ok=True)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        time.sleep(5)

        video_tag = driver.find_element("tag name", "video")
        video_url = video_tag.get_attribute("src")

        filename = os.path.basename(urlparse(video_url).path)
        save_path = os.path.join(folder, filename)

        response = requests.get(video_url, stream=True)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        driver.quit()
        st.success("✅ Reel downloaded!")
    except Exception as e:
        st.error(f"❌ Error downloading reel: {e}")

# Streamlit UI
st.title("📥 Instagram Downloader Bot")
st.markdown("Download **Reels**, **Posts**, **Stories**, and **Captions** from any Instagram link.")

url = st.text_input("🔗 Paste Instagram URL:")
choice = st.radio("Select what to download:", ["Media", "Caption", "Both"])
submit = st.button("Download")

if submit and url:
    content_type = get_content_type(url)
    if content_type == "post":
        download_post(url, choice.lower())
    elif content_type == "story":
        if choice.lower() in ["media", "both"]:
            download_story(url)
        else:
            st.warning("⚠️ Stories don't have captions.")
    elif content_type == "reel":
        if choice.lower() in ["media", "both"]:
            download_reel_with_selenium(url)
        else:
            st.warning("⚠️ Reels don't have separate captions.")
    else:
        st.error("❌ Unsupported or invalid link.")
