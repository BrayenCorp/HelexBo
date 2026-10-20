"""Стартовый каталог платформы: модели, эффекты, тренды, фотосессии, промпты, маркетинг, аватары.

Все тексты — на русском; названия AI-моделей остаются оригинальными. Это СТАРТОВЫЙ набор: после первого запуска
он живёт в базе и редактируется в админ-панели. Описания моделей ориентировочные: реальные возможности зависят от
провайдера, который вы подключите (пока работает демо-режим — см. README).

Превью у карточек не рисуются: пока вы не загрузите свои примеры работ, интерфейс показывает нейтральные
чёрно-белые плашки. Выдуманных «примеров работ» здесь нет.
"""
from __future__ import annotations

# ---------------------------------------------------------------- подписи категорий (код → название)

IMAGE_TAGS = [("photoreal", "ФОТОРЕАЛИЗМ"), ("art", "АРТ"), ("edit", "РЕДАКТИРОВАНИЕ"), ("fast", "БЫСТРЫЕ"), ("hq", "ВЫСОКОЕ КАЧЕСТВО"), ("new", "НОВИНКИ")]
VIDEO_TAGS = [("t2v", "ТЕКСТ → ВИДЕО"), ("i2v", "ИЗОБРАЖЕНИЕ → ВИДЕО"), ("anim", "АНИМАЦИЯ"), ("cine", "КИНЕМАТОГРАФИЧЕСКОЕ ВИДЕО"),
              ("motion", "УПРАВЛЕНИЕ ДВИЖЕНИЕМ"), ("upscale", "УЛУЧШЕНИЕ ВИДЕО")]
AUDIO_TAGS = [("voiceover", "ОЗВУЧКА"), ("voice", "ГОЛОС"), ("ad", "РЕКЛАМА"), ("story", "РАССКАЗ"), ("emotion", "ЭМОЦИОНАЛЬНАЯ РЕЧЬ")]
MODEL_TAGS = {"photo": IMAGE_TAGS, "video": VIDEO_TAGS, "audio": AUDIO_TAGS}

EFFECT_TAGS = [("edit", "Редактирование"), ("photo", "Фото"), ("video", "Видео"), ("improve", "Улучшение")]
TREND_TAGS = [("women", "ЖЕНЩИНЫ"), ("men", "МУЖЧИНЫ"), ("kids", "ДЕТИ"), ("couples", "ПАРЫ"), ("birthday", "ДЕНЬ РОЖДЕНИЯ"), ("dance", "ТАНЦЫ")]  # «ВСЕ» и «ПОПУЛЯРНОЕ» — служебные
PHOTOSHOOT_TAGS = [("women", "ЖЕНЩИНЫ"), ("men", "МУЖЧИНЫ"), ("couples", "ПАРЫ"), ("family", "СЕМЬЯ"), ("birthday", "ДЕНЬ РОЖДЕНИЯ"), ("fashion", "МОДА"),
                   ("luxury", "РОСКОШЬ"), ("lifestyle", "ОБРАЗ ЖИЗНИ"), ("business", "БИЗНЕС"), ("travel", "ПУТЕШЕСТВИЯ"),
                   ("editorial", "РЕДАКЦИОННАЯ СЪЁМКА"), ("street", "УЛИЧНАЯ СЪЁМКА"), ("cinema", "КИНОСТИЛЬ")]
PROMPT_TAGS = [("women", "ЖЕНЩИНЫ"), ("men", "МУЖЧИНЫ"), ("kids", "ДЕТИ"), ("family", "СЕМЬЯ"), ("couples", "ПАРЫ"), ("animals", "ЖИВОТНЫЕ"),
               ("birthday", "ДЕНЬ РОЖДЕНИЯ"), ("fashion", "МОДА"), ("products", "ТОВАРЫ"), ("cinema", "КИНО"), ("lifestyle", "ОБРАЗ ЖИЗНИ"),
               ("architecture", "АРХИТЕКТУРА"), ("marketing", "МАРКЕТИНГ")]
MARKETING_TAGS = [("products", "ТОВАРЫ"), ("ads", "РЕКЛАМА"), ("social", "СОЦИАЛЬНЫЕ СЕТИ"), ("marketplaces", "МАРКЕТПЛЕЙСЫ"), ("ugc", "UGC"), ("brands", "БРЕНДЫ")]
AVATAR_TAGS = [("portrait", "Портрет"), ("fashion", "Мода"), ("travel", "Путешествия"), ("business", "Бизнес"), ("lifestyle", "Образ жизни"),
               ("social", "Социальные сети"), ("ads", "Реклама"), ("cinema", "Кинематографические сцены")]

IDEA_TAGS = [("photo", "ФОТО"), ("video", "ВИДЕО"), ("audio", "АУДИО"), ("portrait", "ПОРТРЕТ"), ("fashion", "МОДА"), ("couples", "ПАРЫ"),
             ("family", "СЕМЬЯ"), ("kids", "ДЕТИ"), ("lifestyle", "ОБРАЗ ЖИЗНИ"), ("cinema", "КИНО"), ("marketing", "МАРКЕТИНГ"), ("other", "ДРУГОЕ")]

SECTION_TAGS = {
    "idea": IDEA_TAGS,
    "effect": EFFECT_TAGS, "trend": TREND_TAGS, "photoshoot": PHOTOSHOOT_TAGS, "prompt": PROMPT_TAGS, "marketing": MARKETING_TAGS, "avatar": AVATAR_TAGS,
}
SECTIONS = ("idea", "effect", "trend", "photoshoot", "prompt", "marketing", "mtool", "avatar")

# Материалы, которые нужны инструменту (код → подпись).
MATERIALS = {
    "photo": "Фото", "person": "Фото человека", "garment": "Фото одежды", "idea": "Описание идеи", "product": "Фото товара",
    "reference": "Референс (по желанию)", "photos": "Несколько фото",
}

# ---------------------------------------------------------------- модели
# (slug, название, тип, теги, описание, назначение, кому подходит, provider_key, цена в токенах)

MODELS = [
    # --- изображения ---
    ("nano-banana", "Nano Banana", "photo", ["fast", "edit"], "Быстрая генерация изображений с хорошей детализацией. Удобна для идей и простых правок по описанию.",
     "Быстрые идеи и правки", "блогерам, дизайнерам, новичкам", "image-default", 8),
    ("nano-banana-pro", "Nano Banana Pro", "photo", ["hq", "photoreal"], "Максимум детализации и аккуратная работа со сложными сценами. Для финальных кадров.",
     "Финальные кадры высокого качества", "фотографам, брендам, студиям", "image-default", 16),
    ("nano-banana-2", "Nano Banana 2", "photo", ["photoreal", "edit"], "Сбалансированная модель: реалистичные изображения и точные правки. Хороший выбор по умолчанию.",
     "Универсальная модель на каждый день", "всем", "image-default", 12),
    ("nano-banana-2-lite", "Nano Banana 2 Lite", "photo", ["fast"], "Облегчённая версия для быстрых набросков и недорогих проб.",
     "Быстрые наброски", "тем, кто подбирает идею", "image-default", 6),
    ("nano-banana-2-1", "Nano Banana 2.1", "photo", ["new", "photoreal"], "Обновлённая версия с более естественными тонами и деталями.",
     "Реалистичные портреты и сцены", "фотографам, блогерам", "image-default", 14),
    ("seedream-5-pro", "Seedream 5 Pro", "photo", ["hq", "photoreal"], "Чистая композиция и высокая детализация. Подходит для рекламных и журнальных кадров.",
     "Рекламные и журнальные кадры", "бизнесу, маркетологам", "image-default", 16),
    ("grok-image-2", "Grok Image 2", "photo", ["art", "new"], "Свободная интерпретация запроса и смелые образы.",
     "Необычные образы и концепты", "авторам контента", "image-default", 10),
    ("wan-2-7-pro", "Wan 2.7 Pro", "photo", ["art", "hq"], "Выразительные иллюстрации и стилизованные сцены с богатой текстурой.",
     "Иллюстрации и стилизация", "художникам, дизайнерам", "image-default", 14),
    ("midjourney", "Midjourney", "photo", ["art", "hq"], "Художественные изображения с эстетичной подачей. Для концептов, обложек и арта.",
     "Арт и концепты", "художникам, авторам обложек", "image-default", 20),
    ("flux-2-flex", "FLUX.2 Flex", "photo", ["photoreal", "edit"], "Гибкая модель: фотореализм и аккуратное редактирование с сохранением композиции.",
     "Фотореализм и редактирование", "фотографам, ретушёрам", "image-default", 12),
    ("lexy-aura", "Lexy Aura", "photo", ["art", "new"], "Мягкая атмосферная стилизация портретов и сцен.",
     "Атмосферные портреты", "блогерам, авторам контента", "image-default", 10),
    ("gpt-image-2-5", "GPT Image 2.5", "photo", ["edit", "hq", "new"], "Точное следование описанию, работа с текстом на изображении и со сложными сценами.",
     "Точные запросы и редактирование", "дизайнерам, маркетологам", "image-default", 18),
    # --- видео ---
    ("seedance-2-5", "Seedance 2.5", "video", ["t2v", "i2v", "cine"], "Видео повышенного качества с плавным движением. Работает по описанию и по фото.",
     "Премиальные короткие видео", "создателям контента, бизнесу", "seedance-2.5", 90),
    ("seedance-2-0", "Seedance 2.0", "video", ["t2v", "i2v"], "Надёжная модель для коротких роликов по описанию или фотографии.",
     "Короткие ролики на каждый день", "блогерам", "video-default", 60),
    ("kling-3-photo", "Kling 3.0 Photo", "video", ["i2v", "anim"], "Оживляет фотографию: естественное движение, мимика и камера. Нужно исходное фото.",
     "Оживление фото", "блогерам, фотографам", "video-default", 70),
    ("kling-3-motion", "Kling 3.0 Motion Control", "video", ["motion", "i2v"], "Управление движением героя и камеры. Нужно исходное фото.",
     "Контроль движения", "видеомейкерам", "video-default", 100),
    ("kling-3-frames", "Kling 3.0 Frames", "video", ["i2v", "cine"], "Видео по кадру: плавный переход от исходного изображения к сцене. Нужно исходное фото.",
     "Видео по кадрам", "режиссёрам, рекламистам", "video-default", 80),
    ("kling-3-text", "Kling 3.0 Text", "video", ["t2v"], "Видео только по текстовому описанию, без исходного изображения.",
     "Видео по тексту", "всем", "video-default", 70),
    ("grok-imagine-1-5", "Grok Imagine 1.5", "video", ["t2v", "anim"], "Быстрые яркие ролики и анимация по описанию.",
     "Быстрые ролики", "авторам коротких видео", "video-default", 50),
    ("veo-omni-flash", "Veo Omni Flash", "video", ["t2v", "i2v"], "Быстрая версия: короткие видео с хорошей связностью сцены.",
     "Быстрые видео", "авторам контента", "video-default", 60),
    ("veo-3-1", "Veo 3.1", "video", ["cine", "t2v", "i2v"], "Кинематографичные сцены с продуманной камерой и светом.",
     "Кинематографичное видео", "режиссёрам, брендам", "video-default", 120),
    ("happy-horse-1-1", "Happy Horse 1.1", "video", ["anim", "t2v"], "Лёгкая весёлая анимация и динамичные персонажи.",
     "Анимация и персонажи", "авторам соцсетей", "video-default", 45),
    ("higgsfield-genjutsu", "Higgsfield Genjutsu", "video", ["cine", "i2v"], "Эффектные движения камеры и стилизованные переходы. Нужно исходное фото.",
     "Эффектные переходы", "авторам клипов", "video-default", 85),
    ("topaz-upscale", "Topaz Upscale", "video", ["upscale"], "Улучшение качества: больше чёткости и деталей. Нужно исходное изображение или кадр.",
     "Улучшение качества", "тем, кто готовит материал к публикации", "video-default", 40),
    ("wan-3-0", "Wan 3.0", "video", ["t2v", "i2v", "cine"], "Универсальная видеомодель: по описанию и по фото, с выразительной камерой.",
     "Универсальное видео", "всем", "video-default", 55),
    # --- аудио ---
    ("eleven", "Eleven", "audio", ["voiceover", "voice", "ad", "story", "emotion"], "Озвучка текста выбранным голосом: можно задать эмоцию, скорость и интонацию.",
     "Озвучка, реклама, рассказ", "блогерам, бизнесу, авторам", "audio-default", 10),
]
# Модели, которым нужен или не подходит исходный файл (проверяется при создании).
MODEL_NEEDS_IMAGE = {"kling-3-photo", "kling-3-motion", "kling-3-frames", "higgsfield-genjutsu", "topaz-upscale"}
MODEL_TEXT_ONLY = {"kling-3-text"}
DEFAULT_MODELS = {"photo": "nano-banana-2", "video": "seedance-2-0", "audio": "eleven"}

# ---------------------------------------------------------------- эффекты
# (slug, название, описание, тег, тип, инструмент, нужные материалы, цена, популярное)

EFFECTS = [
    ("fx-keep-look", "Сохранить внешность", "Новые сцены и образы, в которых лицо остаётся узнаваемым.", "edit", "photo", "keep_look", ["person"], 14, 1),
    ("fx-storyboard", "Раскадровка", "9 кадров по вашей идее или фото: от общего плана до финала.", "photo", "photo", "storyboard", ["photo", "idea"], 40, 1),
    ("fx-angles", "9 ракурсов", "Один и тот же человек и одежда с девяти разных точек съёмки.", "photo", "photo", "angles", ["person"], 40, 1),
    ("fx-garment-photo", "Фото одежды", "Аккуратное предметное фото одежды для каталога или маркетплейса.", "photo", "photo", "garment_photo", ["garment"], 14, 0),
    ("fx-skin", "Улучшение кожи", "Ровный тон и естественная текстура без эффекта пластика.", "improve", "photo", "skin", ["person"], 10, 0),
    ("fx-tryon", "Виртуальная примерка", "Примерьте одежду с фото: лицо, фигура и фон сохраняются.", "photo", "photo", "tryon", ["person", "garment"], 20, 1),
    ("fx-bg", "Замена фона", "Новый фон при сохранении объекта и освещения.", "edit", "photo", "background", ["photo", "idea"], 12, 0),
    ("fx-object", "Замена объекта", "Замените или уберите предмет на фото по описанию.", "edit", "photo", "object", ["photo", "idea"], 12, 0),
    ("fx-enhance", "Улучшение изображения", "Больше чёткости и деталей, меньше шума.", "improve", "photo", "enhance", ["photo"], 8, 0),
    ("fx-restore", "Восстановление фото", "Старые и повреждённые снимки: убираем царапины и выцветание.", "improve", "photo", "restore", ["photo"], 10, 0),
    ("fx-cinema", "Кинематографический стиль", "Цвет, свет и контраст как в кино.", "photo", "photo", "cinematic", ["photo"], 12, 0),
    ("fx-portrait", "Портретная обработка", "Деликатная ретушь портрета: свет, тон, фон.", "improve", "photo", "portrait", ["person"], 10, 0),
    ("fx-product", "Предметная съёмка", "Товар на чистом или студийном фоне, как с профессиональной съёмки.", "photo", "photo", "product", ["product"], 14, 0),
    ("fx-relight", "Изменение освещения", "Другой свет на готовом снимке: мягкий, контрастный, закат.", "improve", "photo", "relight", ["photo"], 10, 0),
    ("fx-stylize", "Стилизация", "Превращает фото в рисунок, плёнку, графику и другие стили.", "edit", "photo", "stylize", ["photo"], 12, 0),
    ("fx-animate", "Оживить фото", "Фото оживает: лёгкое движение, свет и камера.", "video", "video", "animate", ["photo"], 60, 1),
]
EFFECT_PROMPTS = {
    "keep_look": "Place the person from the photo into a new scene, keep the face and appearance exactly recognizable",
    "storyboard": "Cinematic storyboard of nine consecutive shots based on the idea and the photo, consistent character",
    "angles": "The same person and outfit from nine camera angles, consistent appearance and clothing",
    "garment_photo": "Clean catalog photo of the garment, neutral background, soft studio light, true color",
    "skin": "Natural skin retouch, even tone, keep pores and texture, no plastic look",
    "tryon": "Virtual try-on: the person wears the garment from the second image, keep face, body, background and lighting",
    "background": "Replace the background as described, keep the subject, edges and lighting consistent",
    "object": "Replace or remove the object as described, keep everything else unchanged",
    "enhance": "Enhance the image: sharper details, less noise, keep the original look",
    "restore": "Restore the old photo: remove scratches, fix fading, keep faces unchanged",
    "cinematic": "Cinematic color grade and contrast, film look, keep the content unchanged",
    "portrait": "Gentle portrait retouch: balanced light and tone, clean background, natural look",
    "product": "Professional product photo, clean studio background, soft shadows, sharp details",
    "relight": "Change the lighting as described, keep the subject and composition",
    "stylize": "Restyle the photo as described, keep the composition recognizable",
    "animate": "Gently animate the photo: natural movement, soft light, smooth camera, keep the face unchanged",
}

# ---------------------------------------------------------------- тренды
# (slug, название, описание, тег, тип, промпт, цена, популярное)

TRENDS = [
    ("tr-fashion-angel", "Модный ангел", "Образ в духе высокой моды: белые крылья, мягкий свет, студия.", "women", "photo",
     "High-fashion portrait of the person from the photo with large soft white wings, studio light, editorial look, keep the face recognizable", 14, 1),
    ("tr-car-flight", "Полёт на автомобиле", "Динамичное видео: герой летит над городом на автомобиле.", "men", "video",
     "The person from the photo driving a car that lifts into the air above a city, smooth camera movement, cinematic", 60, 1),
    ("tr-rain-change", "Перевоплощение под дождём", "Под дождём образ меняется на новый, камера плавно приближается.", "women", "video",
     "The person from the photo transforms into a new elegant look standing in the rain, cinematic lighting, slow camera push-in", 60, 1),
    ("tr-witch", "Ведьма на метле", "Сказочный полёт на метле над ночным лесом.", "women", "video",
     "The person from the photo as a storybook witch flying on a broom over a night forest, moonlight, smooth motion", 60, 0),
    ("tr-wednesday-dance", "Танец в стиле Wednesday", "Строгий образ и узнаваемый ритмичный танец.", "dance", "video",
     "The person from the photo performs a stylish rhythmic dance in a gothic hall, dark outfit, keep the face unchanged", 60, 1),
    ("tr-quick-change", "Переодевание одним движением", "Один жест — и новый наряд.", "women", "video",
     "The person from the photo changes outfit in one fluid motion, smooth transition, keep the face unchanged", 60, 1),
    ("tr-paris-metro", "Ночное метро Парижа", "Атмосферный ночной кадр на станции парижского метро.", "couples", "photo",
     "Night photo in a Paris metro station, moody cinematic light, the people from the photo, keep faces recognizable", 14, 0),
    ("tr-cine-transform", "Кинематографическое перевоплощение", "Герой превращается в персонажа большого кино.", "men", "video",
     "The person from the photo transforms into a cinematic hero, dramatic light, smooth transition, keep the face unchanged", 60, 0),
    ("tr-viral-dance", "Вирусный танец", "Ваш портрет танцует под популярное движение.", "dance", "video",
     "The person from the photo performs a popular viral dance move, energetic, keep the face unchanged", 60, 1),
    ("tr-halloween", "Хэллоуинское перевоплощение", "Праздничный жутко-милый образ: тыквы, свечи, туман.", "kids", "photo",
     "Friendly Halloween portrait of the child from the photo in a cute costume with pumpkins and candles, fully clothed, age-appropriate, keep the face recognizable", 14, 0),
    ("tr-birthday-cinema", "Именинный кадр как в кино", "День рождения с кинематографичным светом, свечами и конфетти.", "birthday", "photo",
     "Cinematic birthday portrait of the person from the photo with candles and confetti, warm light, keep the face recognizable", 14, 0),
    ("tr-couple-dance", "Парный танец", "Двое танцуют медленный танец в мягком свете.", "couples", "video",
     "The two people from the photo slowly dancing together in soft warm light, smooth camera, keep faces unchanged", 60, 0),
    ("tr-young-hero", "Юный супергерой", "Ребёнок в оригинальном костюме героя на крыше города.", "kids", "photo",
     "The child from the photo as an original friendly superhero on a city rooftop at sunset, fully clothed, age-appropriate, keep the face recognizable", 14, 0),
]

# ---------------------------------------------------------------- фотосессии
# (slug, название, описание, тег, промпт, цена, популярное)

KEEP = "keep the face recognizable, natural skin, tasteful, no text on the image"
PHOTOSHOOTS = [
    ("ps-luxury-studio", "Роскошная студийная съёмка", "Дорогой студийный свет, глубокие тени, ощущение глянца.", "luxury",
     f"Luxury studio photoshoot of the person from the photo, rich lighting, glossy premium look, {KEEP}", 16, 1),
    ("ps-bw-editorial", "Чёрно-белая редакционная съёмка", "Графичный монохромный кадр в духе журнала.", "editorial",
     f"Black and white editorial photoshoot of the person from the photo, strong contrast, magazine look, {KEEP}", 16, 1),
    ("ps-street-fashion", "Уличная мода", "Городской образ, естественный свет, лёгкое движение.", "street",
     f"Street fashion photoshoot of the person from the photo in a modern city, natural light, {KEEP}", 16, 0),
    ("ps-classic-suit", "Классический костюм", "Строгий костюм, чистый фон, уверенная поза.", "men",
     f"Classic tailored suit portrait of the man from the photo, clean background, soft light, {KEEP}", 16, 0),
    ("ps-birthday", "День рождения", "Шарики, конфетти и праздничный свет.", "birthday",
     f"Birthday photoshoot of the person from the photo with balloons and confetti, bright warm light, {KEEP}", 16, 0),
    ("ps-night-cinema", "Ночная кинематографическая съёмка", "Неоновые отражения, мокрый асфальт, кино-настроение.", "cinema",
     f"Night cinematic photoshoot of the person from the photo, city lights, shallow depth of field, {KEEP}", 16, 1),
    ("ps-autumn", "Осенняя фотосессия", "Золотой листопад и мягкое солнце.", "lifestyle",
     f"Autumn photoshoot of the person from the photo among golden leaves, soft sunlight, {KEEP}", 16, 0),
    ("ps-retro-car", "Ретро-автомобиль", "Классический автомобиль и ретро-стиль.", "fashion",
     f"Retro photoshoot of the person from the photo next to a classic car, vintage style, {KEEP}", 16, 0),
    ("ps-minimal-studio", "Минималистичная студия", "Чистый фон, простая композиция, мягкий свет.", "women",
     f"Minimalist studio portrait of the woman from the photo, clean seamless background, soft light, {KEEP}", 16, 0),
    ("ps-luxury-hotel", "Роскошный отель", "Холл, мрамор и тёплый интерьерный свет.", "luxury",
     f"Photoshoot of the person from the photo in a luxury hotel lobby, marble, warm interior light, {KEEP}", 16, 0),
    ("ps-beach", "Пляжная фотосессия", "Море, рассветный свет, лёгкий образ.", "travel",
     f"Beach photoshoot of the person from the photo at dawn, airy light, {KEEP}", 16, 0),
    ("ps-business", "Деловой портрет", "Портрет для резюме, сайта и профиля.", "business",
     f"Professional business portrait of the person from the photo, neutral background, confident, {KEEP}", 16, 1),
    ("ps-couple", "Фотосессия пары", "Нежные кадры для двоих в мягком свете.", "couples",
     f"Romantic couple photoshoot of the two people from the photo, soft golden light, {KEEP}", 18, 0),
    ("ps-family-walk", "Семейная прогулка", "Тёплые семейные кадры на природе.", "family",
     f"Family photoshoot of the people from the photo walking in a park, warm natural light, {KEEP}", 18, 0),
    ("ps-women-window", "Мягкий портрет у окна", "Боковой свет из окна и спокойное настроение.", "women",
     f"Soft portrait of the woman from the photo by a window, gentle side light, {KEEP}", 16, 0),
    ("ps-men-street", "Городской характер", "Мужской образ на улице в золотой час.", "men",
     f"Urban portrait of the man from the photo at golden hour, {KEEP}", 16, 0),
    ("ps-fashion-runway", "Показ мод", "Образ как на подиуме: яркий свет и динамика.", "fashion",
     f"Runway fashion photo of the person from the photo, bright stage light, {KEEP}", 16, 0),
    ("ps-travel-city", "Путешествие по старому городу", "Европейские улицы, тёплый вечерний свет.", "travel",
     f"Travel photo of the person from the photo on an old European street, evening light, {KEEP}", 16, 0),
    ("ps-lifestyle-cafe", "Кофейня и утро", "Спокойный образ жизни: кофе, свет, уют.", "lifestyle",
     f"Lifestyle photo of the person from the photo in a cozy cafe in the morning, natural light, {KEEP}", 16, 0),
    ("ps-editorial-color", "Редакционная съёмка с акцентом", "Выразительная композиция и графичный свет.", "editorial",
     f"Editorial photo of the person from the photo, bold composition, matte tones, {KEEP}", 16, 0),
    ("ps-street-night", "Уличная съёмка ночью", "Свет фонарей и городские отражения.", "street",
     f"Night street photo of the person from the photo, lamp light, reflections, {KEEP}", 16, 0),
    ("ps-cinema-hero", "Кинопортрет героя", "Атмосферный кадр как из фильма.", "cinema",
     f"Cinematic portrait of the person from the photo, moody light, film look, {KEEP}", 16, 0),
    ("ps-business-team", "Деловая команда", "Строгий кадр для сайта компании.", "business",
     f"Business team portrait of the people from the photo in a modern office, {KEEP}", 18, 0),
    ("ps-birthday-cake", "Праздничный торт", "Свечи, торт и тёплая атмосфера.", "birthday",
     f"The person from the photo at a birthday party with a cake and candles, warm light, {KEEP}", 16, 0),
]

# ---------------------------------------------------------------- промпты
# (slug, название, тег, текст промпта, поддерживаемые модели (названия), тип)

_IMG_ALL = ["Nano Banana 2", "Nano Banana Pro", "Seedream 5 Pro", "FLUX.2 Flex", "GPT Image 2.5"]
_IMG_ART = ["Midjourney", "Wan 2.7 Pro", "Lexy Aura", "Grok Image 2"]
PROMPTS = [
    ("pr-w-window", "Портрет у окна", "women", "Женский портрет у большого окна, мягкий боковой свет, лёгкая плёночная зернистость, естественная кожа, спокойный взгляд", _IMG_ALL),
    ("pr-w-fashion", "Fashion-кадр", "women", "Модная съёмка: женщина в оверсайз-пальто на фоне серой студийной стены, строгая композиция, мягкий контраст", _IMG_ALL),
    ("pr-m-office", "Деловой портрет", "men", "Мужчина в тёмном костюме, нейтральный фон, мягкий свет, уверенный спокойный взгляд, реалистичная кожа", _IMG_ALL),
    ("pr-m-street", "Город на закате", "men", "Мужчина идёт по городской улице на закате, тёплый контровой свет, кинематографичная глубина резкости", _IMG_ALL),
    ("pr-k-tale", "Сказочный лес", "kids", "Улыбающийся ребёнок в уютной одежде в сказочном лесу со светлячками, мягкий тёплый свет, добрая иллюстративная атмосфера", _IMG_ART + ["Nano Banana 2"]),
    ("pr-k-space", "Юный космонавт", "kids", "Ребёнок в ярком скафандре на борту космического корабля, иллюстрация, дружелюбное настроение, полностью одет", _IMG_ART + ["Nano Banana 2"]),
    ("pr-f-park", "Семья в парке", "family", "Семья идёт по осеннему парку, тёплый вечерний свет, естественные улыбки, лёгкая зернистость плёнки", _IMG_ALL),
    ("pr-f-table", "Семейный ужин", "family", "Большой семейный стол, тёплый свет лампы, уютный интерьер, живые эмоции, реалистичная фотография", _IMG_ALL),
    ("pr-c-sunset", "Пара на закате", "couples", "Пара обнимается на берегу моря на закате, золотой свет, лёгкий ветер, нежное настроение", _IMG_ALL),
    ("pr-c-city", "Прогулка вдвоём", "couples", "Пара гуляет по старой европейской улице вечером, мягкий свет фонарей, киношная атмосфера", _IMG_ALL),
    ("pr-a-cat", "Кот-аристократ", "animals", "Серый кот в бархатном кресле, студийный свет, глубокие тени, портрет в стиле старых мастеров", _IMG_ART + ["Nano Banana 2"]),
    ("pr-a-dog", "Собака на природе", "animals", "Золотистый ретривер бежит по полю в лучах рассвета, динамичный кадр, высокая детализация шерсти", _IMG_ALL),
    ("pr-b-party", "Праздничный стол", "birthday", "Именинный торт со свечами, шарики и конфетти, тёплый свет, праздничное настроение, реалистичная фотография", _IMG_ALL),
    ("pr-b-confetti", "Взрыв конфетти", "birthday", "Человек смеётся в облаке конфетти, студийный свет, яркий динамичный кадр", _IMG_ALL),
    ("pr-fa-lookbook", "Lookbook образа", "fashion", "Образ из трёх слоёв одежды в нейтральных тонах, чистый фон, чёткие детали ткани, журнальная съёмка", _IMG_ALL),
    ("pr-fa-street", "Уличная мода", "fashion", "Образ в стиле streetwear на городской улице, естественный свет, широкий угол, динамичная поза", _IMG_ALL),
    ("pr-p-bottle", "Бутылка на камне", "products", "Стеклянная бутылка на тёмном камне, мягкий контровой свет, капли воды, премиальная предметная съёмка", _IMG_ALL),
    ("pr-p-sneaker", "Кроссовок в движении", "products", "Кроссовок в прыжке над асфальтом, брызги, динамичный студийный свет, реклама спортивной обуви", _IMG_ALL),
    ("pr-ci-noir", "Нуар", "cinema", "Детектив под дождём ночью, неоновые отражения, высокий контраст, кадр из фильма нуар", _IMG_ALL + ["Midjourney"]),
    ("pr-ci-epic", "Эпический пейзаж", "cinema", "Одинокая фигура на краю скалы над облаками, масштабный кадр, драматичное освещение, широкий формат", _IMG_ART),
    ("pr-l-coffee", "Утро с кофе", "lifestyle", "Чашка кофе на подоконнике, утреннее солнце, уютная комната, мягкие тени, естественные цвета", _IMG_ALL),
    ("pr-l-travel", "Дорога в горах", "lifestyle", "Путешественник с рюкзаком на горной дороге на рассвете, свежий воздух, масштаб, мягкий свет", _IMG_ALL),
    ("pr-ar-house", "Дом в лесу", "architecture", "Минималистичный дом из стекла и дерева в сосновом лесу, туман, утренний свет, архитектурная фотография", _IMG_ALL),
    ("pr-ar-interior", "Светлый интерьер", "architecture", "Просторная гостиная в скандинавском стиле, много света, натуральные материалы, реалистичная визуализация", _IMG_ALL),
    ("pr-m-ad", "Рекламный постер", "marketing", "Постер для кофейни: чашка в центре, чистый светлый фон, место для заголовка сверху, мягкие тени", _IMG_ALL),
    ("pr-m-social", "Обложка для соцсетей", "marketing", "Яркая вертикальная обложка сториз: продукт крупным планом, простая композиция, много свободного места под текст", _IMG_ALL),
]

# ---------------------------------------------------------------- маркетинг
# Инструменты: (slug, название, описание, тег, тип, нужные материалы, цена, формат)
MARKETING_TOOLS = [
    ("mt-ad-image", "Рекламное изображение", "Готовый рекламный кадр по описанию продукта.", "ads", "photo", ["idea"], 16, "1:1"),
    ("mt-ad-video", "Рекламное видео", "Короткий рекламный ролик по описанию или фото.", "ads", "video", ["idea"], 70, "9:16"),
    ("mt-product-photo", "Фото товара", "Товар на чистом или студийном фоне.", "products", "photo", ["product"], 14, "1:1"),
    ("mt-product-card", "Карточка товара", "Изображение для карточки: товар, фон, место под текст.", "marketplaces", "photo", ["product"], 14, "3:4"),
    ("mt-ugc", "UGC", "Контент в стиле «снял обычный человек».", "ugc", "video", ["idea"], 70, "9:16"),
    ("mt-social", "Креатив для социальных сетей", "Квадратные и вертикальные креативы для постов и сториз.", "social", "photo", ["idea"], 14, "9:16"),
    ("mt-marketplace", "Изображение для маркетплейса", "Главное фото товара по требованиям площадок.", "marketplaces", "photo", ["product"], 14, "3:4"),
    ("mt-campaign", "Креатив кампании", "Набор визуалов для рекламной кампании.", "ads", "photo", ["idea"], 18, "16:9"),
    ("mt-lookbook", "Lookbook", "Серия образов одежды в едином стиле.", "brands", "photo", ["garment"], 18, "3:4"),
    ("mt-brand", "Брендовый визуал", "Фирменная картинка в вашей эстетике.", "brands", "photo", ["idea"], 16, "1:1"),
]
# Шаблоны: (slug, название, описание, тег, тип, промпт, цена)
MARKETING_TEMPLATES = [
    ("mk-city", "Товар в центре города", "Продукт на фоне городской улицы, живой свет.", "products", "photo",
     "Product photo in the center of a modern city street, natural light, shallow depth of field, clean composition", 16),
    ("mk-luxury-still", "Роскошная предметная съёмка", "Тёмный фон, акцентный свет, дорогая подача.", "products", "photo",
     "Luxury still life product shot on a dark surface, dramatic accent light, glossy reflections", 16),
    ("mk-motion", "Товар в движении", "Динамичный ролик: товар летит, вращается, разбрызгивает капли.", "ads", "video",
     "Dynamic product video: the product rotates and moves with water splashes, smooth studio lighting", 70),
    ("mk-quiet-lux", "Тихая роскошь", "Сдержанная палитра, мягкий свет, чистая композиция.", "brands", "photo",
     "Quiet luxury brand visual, neutral palette, soft light, minimal composition", 16),
    ("mk-ugc-creator", "UGC-креатор", "Человек показывает продукт на камеру, как в обычном видео.", "ugc", "video",
     "UGC-style video of a person showing the product to the camera in a cozy room, handheld feel", 70),
    ("mk-lookbook", "Модный Lookbook", "Серия образов на нейтральном фоне.", "brands", "photo",
     "Fashion lookbook photo on a neutral background, full-length pose, clear fabric details", 18),
    ("mk-campaign", "Рекламная кампания", "Сильный ключевой визуал с местом под слоган.", "ads", "photo",
     "Advertising campaign key visual, bold composition, empty space for a slogan", 18),
    ("mk-perfume", "Парфюмерная реклама", "Флакон, свет, стекло и вуаль тумана.", "ads", "photo",
     "Perfume advertisement, glass bottle with soft haze and light refraction, elegant", 18),
    ("mk-beauty", "Бьюти-реклама", "Крупный план, чистая кожа, текстуры средства.", "ads", "photo",
     "Beauty product advertisement, close-up, clean skin, product texture swatch, soft glow", 18),
    ("mk-food", "Реклама еды", "Аппетитный свет, пар, свежие ингредиенты.", "ads", "photo",
     "Food advertisement photo, appetizing light, steam, fresh ingredients, shallow depth of field", 16),
]

# ---------------------------------------------------------------- сцены аватаров
# (slug, название, тег, промпт)
AVATAR_SCENES = [
    ("av-portrait-studio", "Студийный портрет", "portrait", "Studio portrait of the person, soft light, neutral backdrop"),
    ("av-portrait-natural", "Портрет на природе", "portrait", "Natural light portrait of the person outdoors, gentle background blur"),
    ("av-fashion-editorial", "Журнальная съёмка", "fashion", "Fashion editorial of the person, stylish outfit, studio light"),
    ("av-fashion-street", "Уличная мода", "fashion", "Street fashion photo of the person in a city"),
    ("av-travel-city", "Путешествие по городу", "travel", "The person traveling in an old European city, evening light"),
    ("av-travel-sea", "У моря", "travel", "The person by the sea at sunrise, airy light"),
    ("av-business-office", "Деловой портрет", "business", "Professional business portrait of the person in a modern office"),
    ("av-business-speaker", "Спикер на сцене", "business", "The person speaking on a conference stage, spotlight"),
    ("av-life-cafe", "Утро в кофейне", "lifestyle", "The person in a cozy cafe in the morning, natural light"),
    ("av-life-home", "Уют дома", "lifestyle", "The person at home in a bright cozy interior"),
    ("av-social-cover", "Обложка профиля", "social", "Clean profile cover photo of the person, simple background, space for text"),
    ("av-social-reels", "Кадр для сториз", "social", "Vertical story frame of the person, bold composition"),
    ("av-ads-product", "С продуктом в руках", "ads", "The person holding a product and smiling, advertising photo, clean background"),
    ("av-ads-brand", "Лицо бренда", "ads", "Brand ambassador portrait of the person, premium look"),
    ("av-cine-noir", "Нуар", "cinema", "Cinematic noir scene with the person, night rain, neon reflections"),
    ("av-cine-epic", "Эпичный кадр", "cinema", "Epic cinematic wide shot with the person on a cliff above clouds"),
]

# ---------------------------------------------------------------- быстрые действия главной (название, описание, действие)
QUICK_ACTIONS = [
    ("Создать изображение", "По описанию", {"to": "create", "kind": "photo"}),
    ("Создать видео", "По описанию или фото", {"to": "create", "kind": "video"}),
    ("Оживить фото", "Фото в короткое видео", {"to": "tool", "slug": "fx-animate"}),
    ("Изменить изображение", "Правки по описанию", {"to": "create", "kind": "photo", "edit": True}),
    ("Создать аватар", "Цифровая версия вас", {"to": "avatars"}),
    ("Создать фотосессию", "Готовые образы", {"to": "photoshoots"}),
    ("Создать рекламу", "Креативы для бизнеса", {"to": "marketing"}),
    ("Создать фото товара", "Для каталога и маркетплейса", {"to": "tool", "slug": "mt-product-photo"}),
]

# ---------------------------------------------------------------- параметры редактора
VOICES = [("alina", "Алина — женский, мягкий"), ("maxim", "Максим — мужской, спокойный"), ("olga", "Ольга — женский, дикторский"),
          ("igor", "Игорь — мужской, глубокий"), ("sofia", "Софья — женский, молодой")]
EMOTIONS = [("neutral", "Нейтрально"), ("joy", "Радостно"), ("calm", "Спокойно"), ("solemn", "Торжественно"), ("sad", "Грустно"), ("inspire", "Вдохновляюще")]
TONES = [("even", "Ровная"), ("question", "Вопросительная"), ("exclaim", "Восклицательная"), ("confidential", "Доверительная"), ("ad", "Рекламная")]

# ---------------------------------------------------------------- пакеты токенов (демо-цены)
# (id, название, токены, бонус, цена в Stars, цена в ₽, плашка, порядок)
PACKAGES = [
    ("start", "СТАРТОВЫЙ", 500, 0, 250, 490, "", 10),
    ("pro", "ПРО", 1500, 100, 650, 1290, "Популярный", 20),
    ("creator", "СОЗДАТЕЛЬ", 5000, 500, 2000, 3990, "Выгодно", 30),
    ("studio", "СТУДИЯ", 15000, 2000, 5500, 9990, "", 40),
]

# ---------------------------------------------------------------- MCP
MCP_TOOLS = [
    ("create_image", "Создать изображение", "Создаёт изображение по описанию. Списывает токены."),
    ("edit_image", "Изменить изображение", "Изменяет изображение из вашей истории по описанию. Списывает токены."),
    ("create_video", "Создать видео", "Создаёт видео по описанию. Списывает токены."),
    ("create_audio", "Создать аудио", "Озвучивает текст. Списывает токены."),
    ("get_generation_status", "Проверить статус генерации", "Статус и результат по номеру генерации."),
    ("get_balance", "Проверить баланс", "Текущий баланс токенов."),
    ("get_history", "Получить историю", "Последние генерации."),
]
MCP_CLIENTS = [
    ("ChatGPT", "Подключите через раздел «Коннекторы» и укажите адрес сервера MCP и токен."),
    ("Claude", "Добавьте удалённый сервер MCP в настройках коннекторов и укажите адрес и токен."),
    ("Cursor", "Добавьте сервер в файл mcp.json: адрес и заголовок Authorization."),
    ("Codex", "Добавьте сервер MCP в конфигурацию клиента: адрес и заголовок Authorization."),
    ("MCP", "Любой клиент с поддержкой удалённых серверов MCP (HTTP) подключается по адресу и токену."),
]
