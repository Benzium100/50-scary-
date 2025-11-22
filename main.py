import os
import requests
from gtts import gTTS
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from PIL import Image, ImageDraw, ImageFont
from pexels_api import API as PexelsAPI
from pixabay import PixabayAPI
import random

# ---------------------------
# Load API keys from env
# ---------------------------
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# ---------------------------
# Config
# ---------------------------
CONTENT_DIR = "content"
IMAGES_DIR = os.path.join(CONTENT_DIR, "images")
AUDIO_DIR = os.path.join(CONTENT_DIR, "audio")
THUMB_DIR = os.path.join(CONTENT_DIR, "thumbnails")
VIDEO_FILE = os.path.join(CONTENT_DIR, "final_video.mp4")

# Make sure folders exist
for folder in [IMAGES_DIR, AUDIO_DIR, THUMB_DIR]:
    os.makedirs(folder, exist_ok=True)

# ---------------------------
# 1️⃣ Generate story (fake example)
# ---------------------------
story = [
    "A mysterious shadow appears in the dark alley.",
    "The victim hears a whisper but no one is there.",
    "Suddenly, a chilling scream echoes in the night.",
    "Footsteps approach slowly, but vanish.",
    "The room turns cold as the lights flicker."
]

# ---------------------------
# 2️⃣ Fetch images from APIs
# ---------------------------
pexels = PexelsAPI(PEXELS_API_KEY)
pixabay = PixabayAPI(PIXABAY_API_KEY)

def fetch_image(query):
    # Try Pexels first
    try:
        pexels.search(query, page=1, results_per_page=1)
        photos = pexels.get_entries()
        if photos:
            url = photos[0].original
            return requests.get(url).content
    except:
        pass
    # Fallback to Pixabay
    try:
        results = pixabay.image_search(query=query)
        if results:
            url = results[0]['largeImageURL']
            return requests.get(url).content
    except:
        pass
    return None

image_files = []
for i, scene in enumerate(story):
    img_data = fetch_image("dark mysterious scene")  # generic for automation
    if img_data:
        img_path = os.path.join(IMAGES_DIR, f"img_{i}.jpg")
        with open(img_path, "wb") as f:
            f.write(img_data)
        image_files.append(img_path)

# ---------------------------
# 3️⃣ Generate TTS audio
# ---------------------------
tts_file = os.path.join(AUDIO_DIR, "voice.mp3")
tts = gTTS(" ".join(story))
tts.save(tts_file)

# ---------------------------
# 4️⃣ Create video clips
# ---------------------------
clips = []
duration_per_image = 5  # seconds per image

for img_path in image_files:
    clip = ImageClip(img_path).set_duration(duration_per_image)
    # Optional: Ken Burns effect
    clip = clip.fx(vfx.zoom_in, 1.05)
    clips.append(clip)

video = concatenate_videoclips(clips)
audio = AudioFileClip(tts_file)
video = video.set_audio(audio)

video.write_videofile(VIDEO_FILE, fps=24)

# ---------------------------
# 5️⃣ Generate thumbnail
# ---------------------------
thumb_path = os.path.join(THUMB_DIR, "thumb.jpg")
im = Image.open(image_files[0])
im.save(thumb_path)

print("Video and thumbnail generated!")
