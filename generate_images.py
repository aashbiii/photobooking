"""
Generates portfolio gallery images for the photography site.
Fetches high-resolution authentic stock photographs matching the content
and theme of each frame, crops and scales them to 1200x900 (4:3 aspect ratio).
Includes a procedural fallback in case internet connectivity is unavailable.
"""
import os, random, math, io
import urllib3
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

urllib3.disable_warnings()

random.seed(7)

OUT = os.path.join(os.path.dirname(__file__), "static", "images", "gallery")
HERO_PATH = os.path.join(os.path.dirname(__file__), "static", "images", "hero.jpg")
os.makedirs(OUT, exist_ok=True)

W, H = 1200, 900

# (filename, title, category, palette[start,end], mode, online_url)
PIECES = [
    ("frame-001.jpg", "The Kasavu Bride",        "Portrait",  (( 30, 24, 26), (201,164, 76)), "vignette",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3b/Bride_on_Wedding_Day.jpg/1280px-Bride_on_Wedding_Day.jpg"),
    ("frame-002.jpg", "A Kerala Wedding",        "Wedding",   (( 18, 20, 28), (176,142, 90)), "beam",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/39/Bride_and_groom_talking_and_walking_together.jpg/1280px-Bride_and_groom_talking_and_walking_together.jpg"),
    ("frame-003.jpg", "Vembanad Houseboat",      "Nature",    (( 46, 30, 20), (222,175, 96)), "beam",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d6/HouseBoat_from_Alappuzha_Vembanad_Kayal.jpg/1280px-HouseBoat_from_Alappuzha_Vembanad_Kayal.jpg"),
    ("frame-004.jpg", "Athirappilly Mist",       "Nature",    (( 15, 15, 18), (150,110, 70)), "vignette",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/12/Athirapilly_waterfalls.jpg/1280px-Athirapilly_waterfalls.jpg"),
    ("frame-005.jpg", "Munnar Tea Hills",        "Nature",    (( 12, 26, 30), ( 90,150,120)), "beam",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3b/Tea_Gardens_in_Munnar.jpg/1280px-Tea_Gardens_in_Munnar.jpg"),
    ("frame-006.jpg", "Grace of Mohiniyattam",   "Editorial", (( 22, 22, 22), (170,170,160)), "vignette",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/19/Mohiniyattam_at_Kerala_School_Kalolsavam_2019_02.jpg/1280px-Mohiniyattam_at_Kerala_School_Kalolsavam_2019_02.jpg"),
    ("frame-007.jpg", "Rhythm of Pooram",        "Event",     (( 24, 16, 26), (210,120,110)), "beam",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ea/Arattupuzha_Pooram_Festival%2C_Sree_Sastha_Temple%2C_Thrissur%2C_Kerala%2C_India_%282017%29.jpg/1280px-Arattupuzha_Pooram_Festival%2C_Sree_Sastha_Temple%2C_Thrissur%2C_Kerala%2C_India_%282017%29.jpg"),
    ("frame-008.jpg", "Backwater Boatman",       "Street",    (( 28, 24, 20), (200,150, 90)), "vignette",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/df/Boatman_on_Backwaters_of_Kerala_-_India.JPG/1280px-Boatman_on_Backwaters_of_Kerala_-_India.JPG"),
    ("frame-009.jpg", "Cheena Vala at Dusk",     "Nature",    (( 10, 22, 28), ( 70,140,150)), "beam",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/89/Kochi%2C_Fishing_nets%2C_Sunset%2C_Kerala%2C_India.jpg/1280px-Kochi%2C_Fishing_nets%2C_Sunset%2C_Kerala%2C_India.jpg"),
    ("frame-010.jpg", "Kathakali Expressions",   "Editorial", (( 20, 18, 22), (190,150,120)), "vignette",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/da/Kathakali_dance_01.jpg/1280px-Kathakali_dance_01.jpg"),
    ("frame-011.jpg", "The Great Snake Boat Race","Event",    (( 16, 14, 20), (200,140, 90)), "beam",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e8/Vallam_kali_boat_race.jpg/1280px-Vallam_kali_boat_race.jpg"),
    ("frame-012.jpg", "Flame of Theyyam",        "Event",     (( 20, 20, 24), (180,100, 90)), "vignette",
     "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/cf/Theyyam_fire_ritual_performance_Kerala_India.jpg/1280px-Theyyam_fire_ritual_performance_Kerala_India.jpg"),
]

HERO_URL = "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/89/Kochi%2C_Fishing_nets%2C_Sunset%2C_Kerala%2C_India.jpg/1280px-Kochi%2C_Fishing_nets%2C_Sunset%2C_Kerala%2C_India.jpg"

def crop_and_resize(img, target_w, target_h):
    if img.mode != "RGB":
        img = img.convert("RGB")
    orig_w, orig_h = img.size
    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        new_w = int(orig_h * target_ratio)
        left = (orig_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, orig_h))
    else:
        new_h = int(orig_w / target_ratio)
        top = (orig_h - new_h) // 2
        img = img.crop((0, top, orig_w, top + new_h))

    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def make_gradient(size, c1, c2, angle_deg):
    w, h = size
    base = Image.new("RGB", (w, h))
    px = base.load()
    rad = math.radians(angle_deg)
    dx, dy = math.cos(rad), math.sin(rad)
    diag = abs(w * dx) + abs(h * dy)
    for y in range(h):
        for x in range(0, w, 2):
            t = ((x * dx + y * dy) / diag + 1) / 2
            t = max(0, min(1, t))
            col = lerp(c1, c2, t)
            px[x, y] = col
            if x + 1 < w:
                px[x + 1, y] = col
    return base

def add_grain(img, amount=14):
    w, h = img.size
    noise = Image.effect_noise((w, h), amount).convert("L")
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img, noise_rgb, 0.06)

def vignette(img):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((-w * 0.25, -h * 0.25, w * 1.25, h * 1.25), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(140))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(img, dark, mask)

def light_beam(img, c2):
    w, h = img.size
    overlay = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(overlay)
    x0 = random.randint(int(w * 0.55), int(w * 0.85))
    d.polygon([(x0, -50), (x0 + 260, -50), (x0 - 120, h + 50), (x0 - 420, h + 50)], fill=140)
    overlay = overlay.filter(ImageFilter.GaussianBlur(90))
    glow = Image.new("RGB", (w, h), lerp(c2, (255, 255, 245), 0.6))
    return Image.composite(glow, img, overlay)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

for i, (fname, title, category, (c1, c2), mode, url) in enumerate(PIECES, start=1):
    success = False
    try:
        r = requests.get(url + "?width=1600&format=pjpg", headers=headers, verify=False, timeout=12)
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content))
            img = crop_and_resize(img, W, H)
            img.save(os.path.join(OUT, fname), quality=92, optimize=True)
            success = True
            print(f"Downloaded & saved {fname} ({title})")
    except Exception as e:
        print(f"Could not download {fname}: {e}")

    if not success:
        angle = random.choice([25, 65, 115, 155])
        img = make_gradient((W, H), c1, c2, angle)
        if mode == "beam":
            img = light_beam(img, c2)
        img = vignette(img)
        img = add_grain(img)
        img.save(os.path.join(OUT, fname), quality=90)
        print(f"Generated fallback gradient for {fname}")

# Hero image
hero_success = False
try:
    r = requests.get(HERO_URL + "?width=2000&format=pjpg", headers=headers, verify=False, timeout=12)
    if r.status_code == 200:
        hero = Image.open(io.BytesIO(r.content))
        hero = crop_and_resize(hero, 1920, 1080)
        hero.save(HERO_PATH, quality=92, optimize=True)
        hero_success = True
        print("Downloaded & saved hero.jpg")
except Exception as e:
    print(f"Could not download hero: {e}")

if not hero_success:
    hero = make_gradient((1920, 1080), (18, 16, 14), (150, 118, 62), 70)
    hero = light_beam(hero, (150, 118, 62))
    hero = vignette(hero)
    hero = add_grain(hero, 10)
    hero.save(HERO_PATH, quality=90)
    print("Generated fallback gradient for hero.jpg")

print("Finished processing all gallery frames + hero image")
