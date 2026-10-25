"""Версия сборки. Видна в приложении («Настройки → О приложении»), в боте (/version) и в админке.

Поднимайте её вместе с заметными изменениями — по ней сразу видно, что у человека открылось:
новая сборка или закешированная старая.
"""
from pathlib import Path

APP_VERSION = "1.1"
BUILD = "2026-10-25.1"


def webapp_build(dist: str | Path) -> str | None:
    """Какая сборка Mini App реально лежит на сервере.

    Файл webapp/public/build.txt попадает в webapp/dist при сборке, поэтому его значение —
    это версия того приложения, которое откроется у человека. None — файла нет (старая сборка).
    """
    try:
        return (Path(dist) / "build.txt").read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def webapp_state(dist: str | Path) -> tuple[str, str]:
    """(статус, человеческое объяснение) для логов и админки. Статус: ok | stale | missing."""
    if not (Path(dist) / "index.html").exists():
        return "missing", "Сборка Mini App не найдена: выполните npm run build в папке webapp и закоммитьте webapp/dist."
    build = webapp_build(dist)
    if build == BUILD:
        return "ok", f"Сборка {build}."
    old = f"сборка {build}" if build else "сборка до версии 1.1"
    return "stale", (f"На сервере лежит старое приложение ({old}), а код сервера — {BUILD}. "
                     "Соберите Mini App и закоммитьте папку webapp/dist: "
                     "cd webapp; npm run build; cd ..; git add -A; git commit -m update; git push")
