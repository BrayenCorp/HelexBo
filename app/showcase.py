"""ВИТРИНА NOLLA AI — РЕДАКТИРУЕТСЯ ЗДЕСЬ, В КОДЕ.

Это единственный источник карточек раздела «Идеи» и блока «Популярные идеи» на главной.
Админка витриной не управляет.

КАК ДОБАВИТЬ КАРТОЧКУ
---------------------
1. Положите картинку в папку  webapp/public/showcase/  (например, night-portrait.jpg).
   В карточке укажите путь "/showcase/night-portrait.jpg".
   Можно и без картинки: тогда подставится одно из ваших фото или нейтральная плашка.
   Видео тоже можно: положите night.mp4 туда же и укажите "image": "/showcase/night.mp4".
2. Добавьте объект в список SHOWCASE ниже. Поле section решает, в каком разделе она появится:
   "idea" — «Идеи», "trend" — «Тренды», "photoshoot" — «Фотосессии», "effect" — «Эффекты», "marketing" — «Маркетинг».
3. Пересоберите приложение (npm run build) и перезапустите сервер — карточка появится сама.

В разделе «Идеи» показываются только карточки с kind="photo" — человек просто загружает своё фото.
Видео и остальное кладите в "trend", "photoshoot", "effect" или "marketing".

ПОЛЯ КАРТОЧКИ
-------------
    slug        обязательно  латиницей, уникально: по нему карточка узнаётся при обновлении
    title       обязательно  название на карточке
    description обязательно  одна-две строки под названием
    category    обязательно  код категории из CATEGORIES ниже (вкладки в разделе «Идеи»)
    kind        обязательно  "photo" | "video" | "audio" — что получится у пользователя
    prompt      обязательно  описание для модели; подставляется в генератор по кнопке «Попробовать»
    model                    "image-default" | "video-default" | "audio-default" или название модели,
                             например "Nano Banana 2". Пусто — модель по типу (kind)
    price                    цена в токенах. 0 или пусто — цена модели по умолчанию
    image                    путь к превью: "/showcase/имя-файла.jpg"
    section                  куда попадёт карточка: "idea" (по умолчанию) | "trend" | "photoshoot" | "effect" | "marketing"
    needs                    что должен прислать пользователь: ["person"], ["photo"], ["product"], [] — ничего
    featured    True/False   «Рекомендуем»: карточка поднимается выше остальных
    on_home     True/False   показывать на главной (по умолчанию True)
    hidden      True/False   временно скрыть карточку, не удаляя её

КАК ДОБАВИТЬ КАТЕГОРИЮ
----------------------
Допишите пару ("код", "НАЗВАНИЕ") в CATEGORIES. Код затем указывайте в поле category.
"""
from __future__ import annotations

# (код, подпись вкладки в разделе «Идеи»)
CATEGORIES: list[tuple[str, str]] = [
    ("photo", "ФОТО"),
    ("video", "ВИДЕО"),
    ("audio", "АУДИО"),
    ("portrait", "ПОРТРЕТ"),
    ("fashion", "МОДА"),
    ("couples", "ПАРЫ"),
    ("family", "СЕМЬЯ"),
    ("kids", "ДЕТИ"),
    ("lifestyle", "ОБРАЗ ЖИЗНИ"),
    ("cinema", "КИНО"),
    ("marketing", "МАРКЕТИНГ"),
    ("other", "ДРУГОЕ"),
]

SHOWCASE: list[dict] = [
    {
        "slug": "idea-cinematic-portrait",
        "title": "Кинематографический портрет",
        "description": "Мягкий свет, глубокие тени и настроение большого кино.",
        "category": "portrait",
        "kind": "photo",
        "prompt": "Cinematic portrait of the person from the photo, soft key light, deep shadows, shallow depth of field, "
                  "film grain, keep the face recognizable, natural skin",
        "model": "Nano Banana 2",
        "price": 14,
        "image": "/showcase/9aae985bffd1eb8e6ab080aa67a3dc3f.jpg",
        "needs": ["person"],
        "featured": True,
    },
    {
        "slug": "idea-night-shoot",
        "title": "Ночная фотосессия",
        "description": "Неон, отражения и город после дождя.",
        "category": "lifestyle",
        "kind": "photo",
        "prompt": "Night photoshoot in a neon-lit city street after rain, reflections on asphalt, cinematic colour, "
                  "keep the face recognizable",
        "model": "Nano Banana 2",
        "price": 14,
        "image": "/showcase/630b8cbf0f9dfd0eba264eaab09d535f.jpg",
        "needs": ["person"],
        "featured": True,
    },
    {
        "slug": "idea-bw-fashion",
        "title": "Чёрно-белая мода",
        "description": "Редакционная съёмка в строгой монохромной гамме.",
        "category": "fashion",
        "kind": "photo",
        "prompt": "Black and white editorial fashion portrait, studio light, strong contrast, elegant pose, "
                  "keep the face recognizable",
        "model": "Seedream 5 Pro",
        "price": 16,
        "image": "/showcase/97f20309fc6d3598291220ec7bc4148.jpg",
        "needs": ["person"],
    },
    {
        "slug": "idea-luxury-studio",
        "title": "Роскошная студийная съёмка",
        "description": "Дорогой свет и ощущение глянцевой обложки.",
        "category": "portrait",
        "kind": "photo",
        "prompt": "Luxury studio photoshoot, rich lighting, glossy premium look, tasteful, keep the face recognizable",
        "model": "Nano Banana Pro",
        "price": 16,
        "image": "/showcase/cc894af2e9f5ff329c7e845eae379e9.jpg",
        "needs": ["person"],
    },
    {
        "slug": "idea-animate-photo",
        "section": "trend",
        "title": "Оживи фотографию",
        "description": "Короткое видео из обычного снимка: лёгкое движение и дыхание кадра.",
        "category": "video",
        "kind": "video",
        "prompt": "Animate the photo: subtle natural motion, gentle camera move, realistic lighting",
        "model": "Kling 3.0 Photo",
        "price": 70,
        "image": "/showcase/f6cb9d304e4a0825b42f7cc3c43971f5_720w.mp4.mp4",
        "needs": ["photo"],
        "featured": True,
    },
    {
        "slug": "idea-ad-video",
        "section": "trend",
        "title": "Рекламное видео",
        "description": "Вертикальный ролик для соцсетей с акцентом на товар.",
        "category": "marketing",
        "kind": "video",
        "prompt": "Vertical advertising video, product in focus, clean composition, soft studio light, smooth camera move",
        "model": "Seedance 2.5",
        "price": 70,
        "image": "",
        "needs": [],
    },
]
