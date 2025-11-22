import os
import random
import requests
from gtts import gTTS
from moviepy.editor import (
    ImageClip, VideoFileClip, concatenate_videoclips,
    AudioFileClip, CompositeAudioClip, vfx
)
from PIL import Image
from pexels_api import API as PexelsAPI
from pixabay import PixabayAPI
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
import datetime

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()
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
# 1️⃣ Generate story automatically
# ---------------------------
def generate_story(scenes=50):
    base_scenes = [
        "A mysterious shadow appears in the dark alley.",
        "The victim hears a whisper but no one is there.",
        "Suddenly, a chilling scream echoes in the night.",
        "Footsteps approach slowly, but vanish.",
        "The room turns cold as the lights flicker."
    ]
    return [random.choice(base_scenes) for _ in range(scenes)]

story = generate_story(50)  # 50 scenes for 1hr+ video

# ---------------------------
# 2️⃣ Fetch images/videos (B&W)
# ---------------------------
pexels = PexelsAPI(PEXELS_API_KEY)
pixabay = PixabayAPI(PIXABAY_API_KEY)

def fetch_media(query, idx):
    """Return local path of either image or short video."""
    # Randomly choose image or video
    try:
        if random.random() < 0.5:  # 50% chance for image
            # Pexels image
            pexels.search(query, page=1, results_per_page=1)
            photos = pexels.get_entries()
            if photos:
                url = getattr(photos[0], "original", photos[0].src['original'])
                path = os.path.join(IMAGES_DIR, f"img_{idx}.jpg")
                data = requests.get(url, timeout=10).content
                with open(path, "wb") as f:
                    f.write(data)
                # Convert to B&W
                im = Image.open(path).convert("L")
                im.save(path)
                return path, "image"
        else:
            # Pixabay video fallback
            results = pixabay.video_search(query=query)
            if results and 'hits' in results and len(results['hits']) > 0:
                url = results['hits'][0]['videos']['medium']['url']
                path = os.path.join(VIDEOS_DIR, f"vid_{idx}.mp4")
                data = requests.get(url, timeout=15).content
                with open(path, "wb") as f:
                    f.write(data)
                return path, "video"
    except:
        pass
    # Fallback: black image placeholder
    path = os.path.join(IMAGES_DIR, f"placeholder_{idx}.jpg")
    img = Image.new("RGB", (1280, 720), color=(0,0,0))
    img.save(path)
    return path, "image"

media_files = [fetch_media("dark mysterious black and white scene", i) for i in range(len(story))]

# ---------------------------
# 3️⃣ Generate TTS
# ---------------------------
tts_file = os.path.join(AUDIO_DIR, "voice.mp3")
tts = gTTS(" ".join(story))
tts.save(tts_file)

# ---------------------------
# 4️⃣ Combine clips
# ---------------------------
clips = []
for path, mtype in media_files:
    duration = random.randint(5,10)
    if mtype == "image":
        clip = ImageClip(path).set_duration(duration)
        clip = clip.fx(vfx.zoom_in, 1.05)
    else:  # video
        clip = VideoFileClip(path)
        if clip.duration > duration:
            clip = clip.subclip(0, duration)
        # Convert to B&W
        clip = clip.fx(vfx.blackwhite)
    clips.append(clip)

video = concatenate_videoclips(clips, method="compose")
audio = AudioFileClip(tts_file)
video = video.set_audio(audio)
video.write_videofile(FINAL_VIDEO, fps=24)

# ---------------------------
# 5️⃣ Thumbnail
# ---------------------------
thumb_path = os.path.join(THUMB_DIR, "thumb.jpg")
im = Image.open(media_files[0][0]).resize((1280, 720))
im.save(thumb_path)

# ---------------------------
# 6️⃣ Upload to YouTube
# ---------------------------
def upload_youtube(title, description, file_path, thumb_path):
    creds = Credentials(
        None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )
    youtube = build("youtube", "v3", credentials=creds)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description, "categoryId":"27"},
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload(file_path)
    )
    response = request.execute()
    video_id = response["id"]
    youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
    print(f"✅ Uploaded video: https://youtu.be/{video_id}")

today = datetime.date.today().strftime("%B %d, %Y")
video_title = f"Mysterious Stories {today}"
video_desc = "Daily automated mysterious story in black & white with chilling audio and stock videos/images."
upload_youtube(video_title, video_desc, FINAL_VIDEO, thumb_path)

print("🎬 All done!")
