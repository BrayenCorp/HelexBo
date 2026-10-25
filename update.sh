#!/usr/bin/env bash
# Обновление Nolla AI для Git Bash (MINGW64). Запуск из папки проекта:  ./update.sh
# Для PowerShell есть такой же скрипт update.ps1.
set -e

old=(
  "webapp/src/admin/Staff.tsx"
  "webapp/src/pages/Create.tsx"
  "webapp/src/pages/Favorites.tsx"
  "webapp/src/pages/Works.tsx"
  "webapp/src/pages/About.tsx"
  "webapp/src/pages/Category.tsx"
  "webapp/src/pages/Explore.tsx"
  "webapp/src/pages/Generate.tsx"
  "webapp/src/pages/Payments.tsx"
  "webapp/src/pages/Settings.tsx"
  "webapp/src/pages/Shop.tsx"
  "webapp/src/pages/TemplatePage.tsx"
  "webapp/src/pages/Tokens.tsx"
  "webapp/src/pages/Welcome.tsx"
  "webapp/src/styles.css"
  "webapp/src/admin/Showcase.tsx"
)
for p in "${old[@]}"; do
  if [ -f "$p" ]; then rm "$p"; echo "Удалён старый файл: $p"; fi
done

cd webapp
npm install
npm run build
cd ..

if [ ! -f webapp/dist/index.html ]; then
  echo "Сборка не получилась: webapp/dist/index.html не создан. Исправьте ошибки выше и запустите снова."
  exit 1
fi

echo
echo "Mini App собран. Railway НЕ собирает приложение сам — отправьте папку webapp/dist в репозиторий:"
echo "  git add -A"
echo "  git commit -m update"
echo "  git push"
echo
echo "После деплоя откройте https://ваш-домен/api/version — build и webapp_build должны совпадать."
