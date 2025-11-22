import os
import requests
from gtts import gTTS
from moviepy.editor import ImageClip, VideoFileClip, concatenate_videoclips, AudioFileClip, vfx, CompositeVideoClip
from PIL import Image
from pexels_api import API as PexelsAPI
from pixabay import PixabayAPI
import random
import tempfile

# Google API for YouTube upload
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# ---------------------------
# Load API keys
# ---------------------------
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# ---------------------------
# Directories
# ---------------------------
CONTENT_DIR = "content"
IMAGES_DIR = os.path.join(CONTENT_DIR, "images")
VIDEOS_DIR = os.path.join(CONTENT_DIR, "videos")
AUDIO_DIR = os.path.join(CONTENT_DIR, "audio")
THUMB_DIR = os.path.join(CONTENT_DIR, "thumbnails")
FINAL_VIDEO = os.path.join(CONTENT_DIR, "final_video.mp4")

for folder in [IMAGES_DIR, VIDEOS_DIR, AUDIO_DIR, THUMB_DIR]:
    os.makedirs(folder, exist_ok=True)

# ---------------------------
# 1️⃣ Generate story automatically (example)
# ---------------------------
story = [
    "A mysterious shadow appears in the dark alley.",
    "The victim hears a whisper but no one is there.",
    "Suddenly, a chilling scream echoes in the night.",
    "Footsteps approach slowly, but vanish.",
    "The room turns cold as the lights flicker."
]

# ---------------------------
# 2️⃣ Fetch images/videos
# ---------------------------
pexels = PexelsAPI(PEXELS_API_KEY)
pixabay = PixabayAPI(PIXABAY_API_KEY)

def fetch_image_or_video(query):
    # Try Pexels photos
    try:
        pexels.search(query, page=1, results_per_page=1)
        entries = pexels.get_entries()
        if entries:
            url = getattr(entries[0], "original", entries[0].src['original'])
            return requests.get(url, timeout=10).content, "image"
    except:
        pass
    # Try Pixabay image/video
    try:
        res = pixabay.image_search(query=query)
        if res and 'hits' in res and len(res['hits'])>0:
            url = res['hits'][0]['largeImageURL']
            return requests.get(url, timeout=10).content, "image"
    except:
        pass
    # fallback black image
    img = Image.new("RGB", (1280, 720), (0,0,0))
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    img.save(tmp_file.name)
    with open(tmp_file.name, "rb") as f:
        return f.read(), "image"

image_files = []
video_files = []

for i, scene in enumerate(story):
    data, ftype = fetch_image_or_video("dark mysterious scene")
    if ftype=="image":
        path = os.path.join(IMAGES_DIR, f"img_{i}.jpg")
    else:
        path = os.path.join(VIDEOS_DIR, f"vid_{i}.mp4")
    with open(path, "wb") as f:
        f.write(data)
    if ftype=="image":
        image_files.append(path)
    else:
        video_files.append(path)

# ---------------------------
# 3️⃣ Generate TTS audio
# ---------------------------
tts_file = os.path.join(AUDIO_DIR, "voice.mp3")
tts = gTTS(" ".join(story))
tts.save(tts_file)

# ---------------------------
# 4️⃣ Create video
# ---------------------------
clips = []

# 5-10 sec per clip
duration = 7

# Images
for img_path in image_files:
    clip = ImageClip(img_path).set_duration(duration).fx(vfx.blackwhite)
    clip = clip.fx(vfx.zoom_in, 1.05)
    clips.append(clip)

# Videos
for vid_path in video_files:
    clip = VideoFileClip(vid_path).subclip(0, duration).fx(vfx.blackwhite)
    clips.append(clip)

final_clip = concatenate_videoclips(clips, method="compose")
audio = AudioFileClip(tts_file)
final_clip = final_clip.set_audio(audio)

final_clip.write_videofile(FINAL_VIDEO, fps=24)

# ---------------------------
# 5️⃣ Thumbnail
# ---------------------------
thumb_path = os.path.join(THUMB_DIR, "thumb.jpg")
im = Image.open(image_files[0])
im = im.resize((1280,720))
im.save(thumb_path)

# ---------------------------
# 6️⃣ Upload to YouTube
# ---------------------------
creds = Credentials(
    token=None,
    refresh_token=YOUTUBE_REFRESH_TOKEN,
    client_id=YOUTUBE_CLIENT_ID,
    client_secret=YOUTUBE_CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token"
)
youtube = build("youtube", "v3", credentials=creds)

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "Daily Horror Story",
            "description": "Automated story video",
            "tags": ["horror","story","daily"],
            "categoryId": "24"
        },
        "status": {
            "privacyStatus": "public"
        }
    },
    media_body=MediaFileUpload(FINAL_VIDEO)
)
response = request.execute()
print("✅ Uploaded:", response)
