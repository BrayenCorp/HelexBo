"""Стартовые категории, шаблоны, баннер и пакеты кредитов Nolla AI.

Всё это потом меняется в админ-панели без правки кода. Обложки категорий и превью шаблонов
пустые: пока вы не загрузите свои примеры работ, приложение показывает фирменные градиенты.
Цены и пакеты — условные, задайте свои.
"""
from __future__ import annotations

from .db import Database, now

SEED_VERSION = "7"

# (slug, название)
CATEGORIES = [
    ("fashion", "Fashion-фотосессии"),
    ("women", "Женские образы"),
    ("men", "Мужские образы"),
    ("kids", "Детские фотосессии"),
    ("kids-cartoons", "Детские фото с мультперсонажами"),
    ("love-story", "Love Story и парные фотосессии"),
    ("wedding", "Свадебные фото и видео"),
    ("birthday", "День рождения"),
    ("seasonal", "Сезонные фотосессии"),
    ("ai-video", "AI-видео"),
    ("trends", "Тренды и новинки"),
]

KEEP = "keep the face recognizable, natural skin, tasteful, no text on the image"
KID = "keep the face recognizable, age-appropriate, fully clothed, friendly"

# (slug, название, описание, категория, тип, модель, промпт, цена, популярное, тренд)
TEMPLATES = [
    ("fashion-editorial", "Глянцевая обложка", "Editorial-съёмка в духе модного журнала", "fashion", "photo", "image-default",
     f"High-fashion editorial photoshoot of the person from the photo, studio light, magazine look, {KEEP}", 2, 1, 0),
    ("fashion-street", "Street style", "Городской образ с естественным светом", "fashion", "photo", "image-default",
     f"Street style fashion photo of the person from the photo in a modern city, soft daylight, {KEEP}", 2, 0, 0),
    ("fashion-bw", "Чёрно-белый портрет", "Графичный fashion-портрет с мягкими тенями", "fashion", "photo", "image-default",
     f"Black and white fashion portrait of the person from the photo, soft shadows, film grain, {KEEP}", 2, 0, 1),
    ("women-soft", "Утончённый портрет", "Нежный свет и мягкая палитра", "women", "photo", "image-default",
     f"Elegant soft-light portrait of the woman from the photo, powder pink tones, {KEEP}", 2, 1, 0),
    ("women-evening", "Вечерний образ", "Вечернее платье и тёплый свет", "women", "photo", "image-default",
     f"Evening look portrait of the woman from the photo in a refined dress, warm light, {KEEP}", 2, 0, 0),
    ("women-flowers", "Романтика в цветах", "Образ среди живых цветов", "women", "photo", "image-default",
     f"Romantic portrait of the woman from the photo surrounded by fresh flowers, natural light, {KEEP}", 2, 0, 0),
    ("men-business", "Деловой портрет", "Строгий костюм и чистый фон", "men", "photo", "image-default",
     f"Professional business portrait of the man from the photo in a tailored suit, clean background, {KEEP}", 2, 1, 0),
    ("men-casual", "Casual в городе", "Стильный повседневный образ", "men", "photo", "image-default",
     f"Casual stylish city portrait of the man from the photo, golden hour, {KEEP}", 2, 0, 0),
    ("men-cinema", "Кинопортрет", "Атмосферный кадр как из фильма", "men", "photo", "image-default",
     f"Cinematic portrait of the man from the photo, moody light, shallow depth of field, {KEEP}", 2, 0, 1),
    ("fairy-prince", "Сказочный принц или принцесса", "Королевский наряд и волшебный замок", "kids", "photo", "image-default",
     f"The child from the photo as a fairy tale royal in a storybook castle, warm light, {KID}", 2, 1, 0),
    ("fairy-forest", "Лесной волшебник", "Добрый герой волшебного леса со светлячками", "kids", "photo", "image-default",
     f"The child from the photo as a friendly forest wizard with fireflies, storybook style, {KID}", 2, 0, 0),
    ("job-astronaut", "Юный космонавт", "Скафандр, звёзды и космический корабль", "kids", "photo", "image-default",
     f"The child from the photo as an astronaut on a spaceship, bright illustration, {KID}", 2, 0, 0),
    ("job-doctor", "Доктор", "Белый халат и добрая улыбка", "kids", "photo", "image-default",
     f"The child from the photo as a kind doctor in a cheerful clinic, soft colors, {KID}", 2, 0, 0),
    ("cartoon-hero", "Мультяшный герой", "Ребёнок как герой яркого мультфильма", "kids-cartoons", "photo", "image-default",
     f"Stylized 3D cartoon portrait of the child from the photo, bright friendly colors, {KID}", 1, 1, 0),
    ("cartoon-sticker", "Забавный стикер", "Мультяшный стикер с весёлым выражением", "kids-cartoons", "photo", "image-default",
     f"Flat vector sticker illustration of the child from the photo, thick outline, cheerful, {KID}", 1, 0, 0),
    ("cartoon-friend", "Друг-мультперсонаж", "Ребёнок рядом с добрым оригинальным персонажем", "kids-cartoons", "photo", "image-default",
     f"The child from the photo next to a friendly original cartoon character, playful scene, {KID}", 2, 0, 0),
    ("love-sunset", "Love Story на закате", "Тёплый закат и нежные объятия", "love-story", "photo", "image-default",
     f"Romantic couple photoshoot of the two people from the photo at sunset, warm golden light, {KEEP}", 3, 1, 0),
    ("love-city", "Прогулка по городу вдвоём", "Городской love story в мягком свете", "love-story", "photo", "image-default",
     f"Couple walking in an old European city street, soft light, film look, people from the photo, {KEEP}", 3, 0, 0),
    ("wedding-portrait", "Свадебный портрет", "Элегантный свадебный кадр", "wedding", "photo", "image-default",
     f"Elegant wedding portrait of the people from the photo, refined attire, soft natural light, {KEEP}", 3, 0, 0),
    ("wedding-video", "Свадебное видео", "Фото оживает: лёгкое движение и свет", "wedding", "video", "video-default",
     "Gently animate the wedding photo: soft movement, drifting light, cinematic, keep the faces unchanged", 8, 0, 0),
    ("birthday-confetti", "Праздничный образ", "Шарики, конфетти и яркий свет", "birthday", "photo", "image-default",
     f"Birthday celebration portrait of the person from the photo with balloons and confetti, {KEEP}", 2, 0, 0),
    ("holiday-birthday", "Именинный торт", "Свечи, торт и тёплая атмосфера", "birthday", "photo", "image-default",
     f"The person from the photo at a birthday party with a cake and candles, warm light, {KEEP}", 2, 0, 0),
    ("holiday-newyear", "Новогодняя сказка", "Праздничный наряд и ёлка с огоньками", "seasonal", "photo", "image-default",
     f"The person from the photo next to a decorated tree, warm festive light, {KEEP}", 2, 1, 0),
    ("season-autumn", "Осень в золоте", "Листопад и мягкое осеннее солнце", "seasonal", "photo", "image-default",
     f"Autumn photoshoot of the person from the photo among golden leaves, soft sunlight, {KEEP}", 2, 0, 0),
    ("season-summer", "Лето у моря", "Лёгкий образ у воды на рассвете", "seasonal", "photo", "image-default",
     f"Summer seaside photoshoot of the person from the photo at dawn, airy light, {KEEP}", 2, 0, 0),
    ("video-alive", "Оживающее фото", "Фото оживает: улыбка, моргание, лёгкое движение", "ai-video", "video", "video-default",
     "Gently animate the photo: natural blinking, a smile, slight head movement, keep the face unchanged", 5, 1, 0),
    ("video-cloud", "Полёт на облаке", "Герой летит на облаке над сказочной страной", "ai-video", "video", "video-default",
     "The person from the photo flying on a fluffy cloud above a colorful fairy land, smooth camera movement", 5, 0, 0),
    ("video-cinematic", "Кинопортрет в движении", "Кинематографичное движение камеры", "ai-video", "video", "video-default",
     "Cinematic slow camera move around the person from the photo, soft light, keep the face unchanged", 6, 1, 1),
    ("video-premium-adventure", "Приключение (премиум)", "Кинематографичное видео-приключение", "ai-video", "video", "seedance-2.5",
     "Cinematic short adventure featuring the person from the photo, magical forest, smooth motion", 10, 0, 0),
    ("trend-film90", "Плёнка 90-х", "Фото как со старой плёнки", "trends", "photo", "image-default",
     f"90s film camera look photo of the person from the photo, flash, grain, nostalgic, {KEEP}", 2, 0, 1),
    ("trend-3d", "Объёмный 3D-портрет", "Современный глянцевый 3D-стиль", "trends", "photo", "image-default",
     f"Glossy modern 3D-style portrait of the person from the photo, soft pastel background, {KEEP}", 2, 1, 1),
    ("trend-dance", "Танцующий портрет", "Портрет оживает в ритме музыки", "trends", "video", "video-default",
     "Animate the portrait: light rhythmic movement as if dancing, keep the face unchanged", 6, 0, 1),
]

PACKAGES = [
    ("p10", "Стартовый", 10, 50, 10),
    ("p30", "Семейный", 30, 130, 20),
    ("p100", "Большой", 100, 400, 30),
]

DEFAULT_SETTINGS = {
    "banner_title": "Создавай реальность без границ",
    "banner_text": "Фото и видео с помощью искусственного интеллекта",
    "banner_button": "Создать сейчас",
    "banner_image_url": "",
    "video_title": "Создать AI-видео",
    "video_text": "Волшебные истории для ваших детей",
    "video_image_url": "",
    "support_url": "",
    "welcome_bonus": "0",  # 0 — стартовый бонус выключен
    "max_variants": "4",
}
OLD_DEFAULT_SETTINGS = {  # прежние тексты (R STUDIO, Luma): заменяем только если их не меняли
    "banner_title": ["Ваши лучшие кадры — с помощью AI", "Создавай красивые моменты с AI"],
    "banner_text": ["Выберите образ, загрузите фото и получите съёмку в стиле глянцевого журнала.", "Волшебные образы для вас и ваших близких"],
    "banner_button": ["Выбрать образ", "Создать фотосессию"],
}

# Старые категории → новые (для баз, созданных первой версией проекта).
LEGACY_CATEGORY_MAP = {"cartoon": "kids-cartoons", "fairy": "kids", "professions": "kids", "holidays": "seasonal", "trends": "ai-video"}

# ---------- версия 3: дизайн Luma (прежний) ----------
# (slug, название, описание, порядок)
CATEGORIES_V3 = [
    ("kids", "Детские фотосессии", "Волшебные образы для ваших детей. Сказочные, стильные и трогательные фотосессии, которые останутся в памяти навсегда.", 10),
    ("fairy", "Сказочные образы", "Принцы, принцессы и герои любимых сказок — в красивых нарядах и волшебных декорациях.", 20),
    ("professions", "Профессии", "Космонавт, врач, повар, пилот: кем мечтают стать ваши дети.", 30),
    ("family", "Семейные фото", "Тёплые семейные кадры: вместе, в красивых образах и с настроением.", 40),
    ("birthday", "Праздники и дни рождения", "Шарики, торт, конфетти и праздничное настроение.", 50),
    ("seasonal", "Сезонные фотосессии", "Осень, зима, весна и лето — в красивых сезонных образах.", 60),
    ("ai-video", "AI-видео", "Короткие волшебные видео из одной фотографии.", 70),
    ("trends", "Популярные тренды", "То, что сейчас выбирают чаще всего.", 80),
    ("kids-cartoons", "Детские фото с мультперсонажами", "Дети рядом с добрыми мультяшными героями.", 90),
    ("fashion", "Fashion-фотосессии", "Глянцевые съёмки в духе модного журнала.", 100),
    ("women", "Женские образы", "Нежные и выразительные женские портреты.", 110),
    ("men", "Мужские образы", "Стильные мужские портреты на любой случай.", 120),
    ("love-story", "Love Story и парные фотосессии", "Романтические кадры для двоих.", 130),
    ("wedding", "Свадебные фото и видео", "Элегантные свадебные образы и оживающие фото.", 140),
]
OLD_TITLES = {"birthday": "День рождения", "trends": "Тренды и новинки"}  # меняем название, только если его не правили
OLD_SORT = {cid: (i + 1) * 10 for i, (cid, _) in enumerate(CATEGORIES)}

MOVES = {  # слаг шаблона → новая категория (только если он всё ещё в «kids»)
    "fairy-prince": "fairy", "fairy-forest": "fairy", "job-astronaut": "professions", "job-doctor": "professions",
}

# (slug, название, описание, категория, тип, модель, промпт, цена, популярное, тренд)
TEMPLATES_V3 = [
    ("kid-prince", "Маленький принц", "Волшебная фотосессия в стиле маленького принца. Нежные образы, тёплая атмосфера и настоящая сказка.", "fairy", "photo", "image-default",
     f"The child from the photo as a little prince in a golden royal costume with a cape and crown, castle background, warm light, {KID}", 3, 1, 0),
    ("kid-princess", "Принцесса в замке", "Нарядное платье, корона и сказочный замок.", "fairy", "photo", "image-default",
     f"The child from the photo as a little princess in a fairy tale castle, soft pastel light, {KID}", 3, 1, 1),
    ("kid-clouds", "Малыш в облаках", "Мягкие облака и нежное небо.", "kids", "photo", "image-default",
     f"The child from the photo among soft fluffy clouds in a bright blue sky, dreamy light, {KID}", 2, 0, 0),
    ("kid-soft", "Портрет в мягком свете", "Тёплый студийный портрет.", "kids", "photo", "image-default",
     f"Warm studio portrait of the child from the photo, soft window light, neutral background, {KID}", 2, 0, 0),
    ("job-chef", "Маленький повар", "Поварской колпак и уютная кухня.", "professions", "photo", "image-default",
     f"The child from the photo as a little chef in a cozy kitchen, chef hat, warm light, {KID}", 2, 0, 0),
    ("job-pilot", "Юный пилот", "Лётная форма и самолёт.", "professions", "photo", "image-default",
     f"The child from the photo as a young pilot next to a vintage airplane, warm light, {KID}", 2, 0, 0),
    ("family-session", "Семейная фотосессия", "Тёплый семейный портрет в красивых образах.", "family", "photo", "image-default",
     f"Warm family portrait of the people from the photo, coordinated outfits, soft natural light, {KEEP}", 3, 1, 0),
    ("family-story", "Семейная история", "Семейное фото оживает.", "family", "video", "video-default",
     "Gently animate the family photo: soft smiles, light movement, warm cinematic mood, keep the faces unchanged", 8, 0, 0),
    ("video-journey", "Сказочное путешествие", "Короткое видео-путешествие по волшебной стране.", "ai-video", "video", "video-default",
     "The person from the photo on a magical journey through a fairy land, smooth camera movement, warm colors", 6, 0, 0),
    ("video-magic", "Волшебное превращение", "Образ меняется на глазах.", "ai-video", "video", "video-default",
     "The person from the photo magically transforms into a fairy tale character with sparkles, smooth transition", 6, 0, 1),
]

DEFAULT_STYLES = [
    {"id": "classic", "title": "Классический", "prompt": ""},
    {"id": "soft", "title": "Мягкий свет", "prompt": "soft warm light, gentle tones"},
    {"id": "vivid", "title": "Яркий", "prompt": "vivid saturated colors, joyful mood"},
    {"id": "cinema", "title": "Кинематографичный", "prompt": "cinematic lighting, shallow depth of field"},
]


def _replace_old_texts(conn) -> None:
    for key, olds in OLD_DEFAULT_SETTINGS.items():
        for old in olds:
            conn.execute("UPDATE settings SET value = ? WHERE key = ? AND value = ?", (DEFAULT_SETTINGS[key], key, old))


def _seed_v2(conn, ts: str) -> None:
    for i, (cid, title) in enumerate(CATEGORIES):
        conn.execute("INSERT OR IGNORE INTO categories (id, title, sort_order, created_at) VALUES (?, ?, ?, ?)",
                     (cid, title, (i + 1) * 10, ts))
    for old, new in LEGACY_CATEGORY_MAP.items():  # перенос шаблонов из первой версии
        conn.execute("UPDATE templates SET category = ? WHERE category = ?", (new, old))
    for i, (slug, title, desc, cat, kind, model, prompt, price, popular, trend) in enumerate(TEMPLATES):
        exists = conn.execute("SELECT id FROM templates WHERE slug = ?", (slug,)).fetchone()
        if exists:
            conn.execute("UPDATE templates SET category = ?, is_trend = ? WHERE id = ?", (cat, trend, exists["id"]))
        else:
            conn.execute(
                "INSERT INTO templates (slug, title, description, category, kind, model, prompt, emoji, price_credits, "
                "is_published, is_popular, is_trend, sort_order, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, '✦', ?, 1, ?, ?, ?, ?, ?)",
                (slug, title, desc, cat, kind, model, prompt, price, popular, trend, (i + 1) * 10, ts, ts),
            )


def _seed_v3(conn, ts: str) -> None:
    import json

    for cid, title, desc, sort in CATEGORIES_V3:
        row = conn.execute("SELECT title, sort_order, description FROM categories WHERE id = ?", (cid,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO categories (id, title, description, sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
                         (cid, title, desc, sort, ts))
            continue
        if cid in OLD_TITLES and row["title"] == OLD_TITLES[cid]:
            conn.execute("UPDATE categories SET title = ? WHERE id = ?", (title, cid))
        if row["sort_order"] == OLD_SORT.get(cid):
            conn.execute("UPDATE categories SET sort_order = ? WHERE id = ?", (sort, cid))
        if not row["description"]:
            conn.execute("UPDATE categories SET description = ? WHERE id = ?", (desc, cid))
    for slug, cat in MOVES.items():
        conn.execute("UPDATE templates SET category = ? WHERE slug = ? AND category = 'kids'", (cat, slug))
    base = conn.execute("SELECT COALESCE(MAX(sort_order), 0) AS m FROM templates").fetchone()["m"]
    for i, (slug, title, desc, cat, kind, model, prompt, price, popular, trend) in enumerate(TEMPLATES_V3):
        if conn.execute("SELECT 1 FROM templates WHERE slug = ?", (slug,)).fetchone() is None:
            conn.execute(
                "INSERT INTO templates (slug, title, description, category, kind, model, prompt, emoji, price_credits, "
                "is_published, is_popular, is_trend, sort_order, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, '✦', ?, 1, ?, ?, ?, ?, ?)",
                (slug, title, desc, cat, kind, model, prompt, price, popular, trend, base + (i + 1) * 10, ts, ts),
            )
    # Стили («Параметры» при создании) — для фото-шаблонов, где их ещё нет.
    conn.execute("UPDATE templates SET styles = ? WHERE kind = 'photo' AND styles = '[]'", (json.dumps(DEFAULT_STYLES, ensure_ascii=False),))
    conn.execute("UPDATE packages SET badge = 'Популярный' WHERE id = 'p30' AND badge = ''")
    conn.execute("UPDATE packages SET badge = 'Лучший выбор' WHERE id = 'p100' AND badge = ''")
    _replace_old_texts(conn)


# ---------- версия 4: Nolla AI ----------
# Шесть категорий витрины «Создать». Прежние категории скрываются, их образы переносятся.
CATEGORIES_V4 = [
    ("trends", "Тренды", "Популярные стили и идеи", 10),
    ("men", "Мужские", "Реалистичные и стильные образы", 20),
    ("women", "Женские", "Портреты, мода и разные стили", 30),
    ("kids", "Детские", "Милые и естественные образы", 40),
    ("family", "Семейные", "Тёплые моменты с близкими", 50),
    ("ai-video", "Видео", "Генерация видео по описанию", 60),
]
CATEGORY_MOVES_V4 = {  # старая категория → новая
    "fairy": "kids", "professions": "kids", "kids-cartoons": "kids", "birthday": "family", "wedding": "family",
    "seasonal": "trends", "love-story": "trends", "fashion": "women",
}
LABELS_V4 = {  # подкатегория («стиль») внутри категории
    "women-soft": "Portrait", "women-evening": "Fashion", "women-flowers": "Lifestyle", "fashion-editorial": "Editorial",
    "fashion-street": "Street", "fashion-bw": "Studio", "men-business": "Studio", "men-casual": "Lifestyle", "men-cinema": "Cinematic",
    "kid-soft": "Портрет", "kid-clouds": "Портрет", "fairy-prince": "Сказки", "fairy-forest": "Сказки", "kid-prince": "Сказки",
    "kid-princess": "Сказки", "job-astronaut": "Профессии", "job-doctor": "Профессии", "job-chef": "Профессии", "job-pilot": "Профессии",
    "cartoon-hero": "Мультфильм", "cartoon-sticker": "Мультфильм", "cartoon-friend": "Мультфильм",
    "family-session": "Портрет", "family-story": "Видео", "birthday-confetti": "Праздник", "holiday-birthday": "Праздник",
    "wedding-portrait": "Свадьба", "wedding-video": "Свадьба", "love-sunset": "Love Story", "love-city": "Love Story",
    "holiday-newyear": "Сезонные", "season-autumn": "Сезонные", "season-summer": "Сезонные",
    "trend-film90": "Ретро", "trend-3d": "3D", "trend-dance": "Оживление",
}
# (slug, название, описание, категория, тип, модель, промпт, цена, популярное, тренд, подкатегория)
TEMPLATES_V4 = [
    ("w-cinematic", "Cinematic", "Кадр как из фильма: глубина, мягкий контраст", "women", "photo", "image-default",
     f"Cinematic portrait of the woman from the photo, moody light, shallow depth of field, film look, {KEEP}", 2, 0, 1, "Cinematic"),
    ("w-beauty", "Beauty", "Чистая кожа, крупный план, мягкий свет", "women", "photo", "image-default",
     f"Beauty close-up portrait of the woman from the photo, soft glow, clean skin, {KEEP}", 2, 1, 0, "Beauty"),
    ("m-portrait", "Portrait", "Классический мужской портрет", "men", "photo", "image-default",
     f"Classic portrait of the man from the photo, soft side light, neutral background, {KEEP}", 2, 1, 0, "Portrait"),
    ("m-fashion", "Fashion", "Стильный образ в духе модного журнала", "men", "photo", "image-default",
     f"Men's fashion editorial of the man from the photo, tailored outfit, studio light, {KEEP}", 2, 0, 0, "Fashion"),
    ("m-street", "Street", "Городской характер и естественный свет", "men", "photo", "image-default",
     f"Street style photo of the man from the photo in a city at golden hour, {KEEP}", 2, 0, 0, "Street"),
    ("m-editorial", "Editorial", "Графичный редакционный кадр", "men", "photo", "image-default",
     f"Editorial photo of the man from the photo, bold composition, matte tones, {KEEP}", 2, 0, 1, "Editorial"),
    ("m-beauty", "Beauty", "Аккуратный образ, крупный план", "men", "photo", "image-default",
     f"Grooming close-up portrait of the man from the photo, natural skin, soft light, {KEEP}", 2, 0, 0, "Beauty"),
]
SYSTEM_TEMPLATES = [  # скрытые шаблоны «свободной» генерации (цена и модель — в админке)
    ("__free_photo", "Свободное фото", "photo", "image-default", 2),
    ("__free_video", "Свободное видео", "video", "video-default", 6),
]


def _seed_v4(conn, ts: str) -> None:
    import json

    for cid, title, desc, sort in CATEGORIES_V4:
        if conn.execute("SELECT 1 FROM categories WHERE id = ?", (cid,)).fetchone():
            conn.execute("UPDATE categories SET title = ?, description = ?, sort_order = ?, is_published = 1 WHERE id = ?", (title, desc, sort, cid))
        else:
            conn.execute("INSERT INTO categories (id, title, description, sort_order, created_at) VALUES (?, ?, ?, ?, ?)", (cid, title, desc, sort, ts))
    for old, new in CATEGORY_MOVES_V4.items():
        conn.execute("UPDATE templates SET category = ? WHERE category = ?", (new, old))
        conn.execute("UPDATE categories SET is_published = 0 WHERE id = ?", (old,))  # скрыта, не удалена — можно вернуть в админке
    for slug, label in LABELS_V4.items():
        conn.execute("UPDATE templates SET style_label = ? WHERE slug = ? AND style_label = ''", (label, slug))
    base = conn.execute("SELECT COALESCE(MAX(sort_order), 0) AS m FROM templates").fetchone()["m"]
    for i, (slug, title, desc, cat, kind, model, prompt, price, popular, trend, label) in enumerate(TEMPLATES_V4):
        if conn.execute("SELECT 1 FROM templates WHERE slug = ?", (slug,)).fetchone() is None:
            conn.execute(
                "INSERT INTO templates (slug, title, description, category, kind, model, prompt, emoji, price_credits, "
                "is_published, is_popular, is_trend, style_label, sort_order, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, '✦', ?, 1, ?, ?, ?, ?, ?, ?)",
                (slug, title, desc, cat, kind, model, prompt, price, popular, trend, label, base + (i + 1) * 10, ts, ts),
            )
    conn.execute("UPDATE templates SET styles = ? WHERE kind = 'photo' AND styles = '[]' AND is_system = 0",
                 (json.dumps(DEFAULT_STYLES, ensure_ascii=False),))
    for slug, title, kind, model, price in SYSTEM_TEMPLATES:
        if conn.execute("SELECT 1 FROM templates WHERE slug = ?", (slug,)).fetchone() is None:
            conn.execute(
                "INSERT INTO templates (slug, title, description, category, kind, model, prompt, emoji, price_credits, "
                "is_published, is_system, sort_order, created_at, updated_at) "
                "VALUES (?, ?, 'Свободная генерация по описанию', 'trends', ?, ?, '', '✦', ?, 1, 1, 9999, ?, ?)",
                (slug, title, kind, model, price, ts, ts),
            )
    _replace_old_texts(conn)


# ---------- версия 5: токены, модели, способы оплаты, FAQ ----------
MODELS_V5 = [  # (название, тип, описание, назначение, кому подходит, provider_key, цена, активна)
    ("Фото · реализм", "photo", "Для создания максимально реалистичных фотографий, портретов и lifestyle-контента.",
     "Реалистичные фото и портреты", "фотографам, блогерам, бизнесу, создателям контента", "image-default", 2, 1),
    ("Видео · стандарт", "video", "Короткие AI-видео по описанию или из вашей фотографии.", "Короткие видео",
     "блогерам, бизнесу, создателям контента", "video-default", 6, 1),
    ("Видео · премиум", "video", "Видео повышенного качества. Включите после подключения провайдера.", "Премиальные видео",
     "создателям контента", "seedance-2.5", 10, 0),
]
FAQ_V5 = [
    ("Что такое токены?", "Токены — внутренняя валюта Nolla AI. Они списываются за создание фото и видео."),
    ("Сколько стоит генерация?", "Стоимость показывается перед созданием и зависит от выбранной модели или стиля. Первое фото и первое видео бесплатны."),
    ("Какие модели используются?", "Актуальный список моделей и их назначение показаны на главной странице в разделе «Какие AI-модели мы используем»."),
    ("Можно ли создавать видео?", "Да. Видео доступно в разделе «Создать» и через кнопку «+» → «Видео»."),
    ("Как купить токены?", "Откройте «Профиль» → баланс → «Купить токены», выберите пакет и способ оплаты."),
    ("Какие способы оплаты доступны?", "Доступные способы показаны на странице покупки токенов. Список обновляется по мере подключения новых."),
    ("Можно ли вернуть токены при ошибке?", "Да. Если генерация завершилась ошибкой, токены автоматически возвращаются на баланс."),
    ("Как работает PRO?", "PRO — тариф с расширенными возможностями. Сейчас он назначается администратором, оформление подписки появится позже."),
]
METHODS_V5 = [  # (код, название, описание, статус)
    ("stars", "Telegram Stars", "Оплата звёздами прямо в Telegram", "on", 10),
    ("sbp", "СБП", "Оплата через Систему быстрых платежей", "off", 20),
    ("card", "Банковская карта", "Оплата банковской картой", "off", 30),
    ("test", "Тестовая оплата", "Только для проверки, без реальных денег", "on", 90),
]


def _seed_v5(conn, ts: str) -> None:
    for i, (name, kind, desc, purpose, aud, key, price, active) in enumerate(MODELS_V5):
        if conn.execute("SELECT 1 FROM ai_models WHERE name = ?", (name,)).fetchone() is None:
            conn.execute("INSERT INTO ai_models (name, kind, description, purpose, audience, provider_key, price_credits, is_active, sort_order, created_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (name, kind, desc, purpose, aud, key, price, active, (i + 1) * 10, ts))
    if conn.execute("SELECT COUNT(*) FROM faq").fetchone()[0] == 0:
        for i, (q, a) in enumerate(FAQ_V5):
            conn.execute("INSERT INTO faq (question, answer, sort_order) VALUES (?, ?, ?)", (q, a, (i + 1) * 10))
    for code, title, desc, status, sort in METHODS_V5:
        conn.execute("INSERT OR IGNORE INTO payment_methods (code, title, description, status, sort_order) VALUES (?, ?, ?, ?, ?)", (code, title, desc, status, sort))
    _replace_old_texts(conn)


# ---------- версия 6: платформа (модели, эффекты, тренды, фотосессии, промпты, маркетинг, аватары, аудио) ----------
def _seed_v6(conn, ts: str) -> None:
    import json

    from . import catalog_data as cd

    # Прежние три «модели» (версия 5) скрываются, а не удаляются: на них могут ссылаться старые заказы.
    conn.execute("UPDATE ai_models SET is_active = 0 WHERE slug = '' AND name IN ('Фото · реализм', 'Видео · стандарт', 'Видео · премиум')")
    for i, (slug, name, kind, tags, desc, purpose, aud, key, price) in enumerate(cd.MODELS):
        if conn.execute("SELECT 1 FROM ai_models WHERE slug = ?", (slug,)).fetchone():
            continue
        all_tags = list(tags)
        if slug in cd.MODEL_NEEDS_IMAGE:
            all_tags.append("in:image")
        if slug in cd.MODEL_TEXT_ONLY:
            all_tags.append("in:text")
        conn.execute(
            "INSERT INTO ai_models (name, slug, kind, tags, description, purpose, audience, provider_key, price_credits, is_active, sort_order, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (name, slug, kind, json.dumps(all_tags), desc, purpose, aud, key, price, (i + 1) * 10, ts))

    def put(slug, title, desc, section, tag, kind, model, prompt, price, popular=0, tool="", required=(), supported=(), trend=0, order=0):
        if conn.execute("SELECT 1 FROM templates WHERE slug = ?", (slug,)).fetchone():
            return
        conn.execute(
            "INSERT INTO templates (slug, title, description, category, kind, model, prompt, emoji, price_credits, is_published, is_popular, is_trend, "
            "section, tag, tool, required, supported_models, sort_order, created_at, updated_at) "
            "VALUES (?, ?, ?, 'trends', ?, ?, ?, '✦', ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (slug, title, desc, kind, model, prompt, price, popular, trend, section, tag, tool, json.dumps(list(required)),
             json.dumps(list(supported), ensure_ascii=False), order, ts, ts))

    prov = {"photo": "image-default", "video": "video-default", "audio": "audio-default"}
    for i, (slug, title, desc, tag, kind, tool, req, price, pop) in enumerate(cd.EFFECTS):
        put(slug, title, desc, "effect", tag, kind, prov[kind], cd.EFFECT_PROMPTS[tool], price, pop, tool, req, order=(i + 1) * 10)
    for i, (slug, title, desc, tag, kind, prompt, price, pop) in enumerate(cd.TRENDS):
        put(slug, title, desc, "trend", tag, kind, prov[kind], prompt, price, pop, required=["person"], trend=1, order=(i + 1) * 10)
    for i, (slug, title, desc, tag, prompt, price, pop) in enumerate(cd.PHOTOSHOOTS):
        put(slug, title, desc, "photoshoot", tag, "photo", "image-default", prompt, price, pop, required=["person"], order=(i + 1) * 10)
    for i, (slug, title, tag, text, models) in enumerate(cd.PROMPTS):
        put(slug, title, text, "prompt", tag, "photo", "image-default", text, 0, 0, supported=models, order=(i + 1) * 10)
    for i, (slug, title, desc, tag, kind, req, price, fmt) in enumerate(cd.MARKETING_TOOLS):
        put(slug, title, desc, "mtool", tag, kind, prov[kind], desc, price, 0, "marketing:" + fmt, req, order=(i + 1) * 10)
    for i, (slug, title, desc, tag, kind, prompt, price) in enumerate(cd.MARKETING_TEMPLATES):
        put(slug, title, desc, "marketing", tag, kind, prov[kind], prompt, price, 0, required=["product"] if kind == "photo" else ["idea"], order=(i + 1) * 10)
    for i, (slug, title, tag, prompt) in enumerate(cd.AVATAR_SCENES):
        put(slug, title, prompt, "avatar", tag, "photo", "image-default", prompt + ", keep the face recognizable", 16, 0, "avatar", ["avatar"], order=(i + 1) * 10)

    if conn.execute("SELECT 1 FROM templates WHERE slug = '__free_audio'").fetchone() is None:
        conn.execute(
            "INSERT INTO templates (slug, title, description, category, kind, model, prompt, emoji, price_credits, is_published, is_system, sort_order, created_at, updated_at) "
            "VALUES ('__free_audio', 'Свободное аудио', 'Озвучка текста', 'trends', 'audio', 'audio-default', '', '✦', 10, 1, 1, 9999, ?, ?)", (ts, ts))

    # Пакеты токенов: прежние (детская версия) скрываются, новые — с демо-ценами.
    if conn.execute("SELECT 1 FROM packages WHERE id = 'start'").fetchone() is None:
        conn.execute("UPDATE packages SET is_active = 0 WHERE id IN ('p10', 'p30', 'p100')")
        for pid, title, credits, bonus, stars, rub, badge, sort in cd.PACKAGES:
            conn.execute("INSERT INTO packages (id, title, credits, bonus, price_stars, price_rub, badge, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (pid, title, credits, bonus, stars, rub, badge, sort))
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('frame_regen_price', '4')")


# Какие модели показываем пользователю. Остальные скрыты (не удалены): включить можно в админке.
ACTIVE_MODELS = ("Nano Banana 2", "Nano Banana 2.1", "Nano Banana 2 Lite", "Seedance 2.0", "Seedance 2.5")


def _seed_v7(conn, ts: str) -> None:
    """Оставляем только нужные модели изображений и видео. Остальные скрыты (не удалены).
    Аудио-модель тоже скрыта: раздел аудио в интерфейсе и в боте не показывается."""
    marks = ", ".join("?" * len(ACTIVE_MODELS))
    conn.execute(f"UPDATE ai_models SET is_active = 0 WHERE name NOT IN ({marks})", ACTIVE_MODELS)
    conn.execute(f"UPDATE ai_models SET is_active = 1 WHERE name IN ({marks})", ACTIVE_MODELS)


def apply_welcome_default(db: Database, amount: int) -> None:
    """Один раз при обновлении до платформы: если стартовый бонус не задавали (0), включаем его (WELCOME_BONUS в .env).
    Дальше значение меняется только в админ-панели."""
    with db.tx() as conn:
        if conn.execute("SELECT 1 FROM settings WHERE key = 'welcome_default_v6'").fetchone():
            return
        conn.execute("UPDATE settings SET value = ? WHERE key = 'welcome_bonus' AND value = '0'", (str(max(0, int(amount))),))
        conn.execute("INSERT INTO settings (key, value) VALUES ('welcome_default_v6', '1')")


def seed_defaults(db: Database) -> None:
    ts = now()
    with db.tx() as conn:
        if conn.execute("SELECT COUNT(*) AS n FROM packages").fetchone()["n"] == 0:
            for pid, title, credits, stars, sort in PACKAGES:
                conn.execute("INSERT INTO packages (id, title, credits, price_stars, sort_order) VALUES (?, ?, ?, ?, ?)",
                             (pid, title, credits, stars, sort))
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

        row = conn.execute("SELECT value FROM settings WHERE key = 'seed_version'").fetchone()
        version = row["value"] if row else None
        if version == SEED_VERSION:
            return  # стартовый набор уже внесён — удалённые вами шаблоны не вернутся
        if version is None:
            _seed_v2(conn, ts)
        if version in (None, "2"):
            _seed_v3(conn, ts)
        if version in (None, "2", "3"):
            _seed_v4(conn, ts)
        _seed_v5(conn, ts)
        _seed_v6(conn, ts)
        _seed_v7(conn, ts)
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('seed_version', ?)", (SEED_VERSION,))
