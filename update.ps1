# Update Nolla AI: removes old files that no longer exist and builds the Mini App.
# Run from the project folder:  .\update.ps1
$old = @(
    "webapp\src\admin\Staff.tsx",
    "webapp\src\pages\Catalog.tsx",
    "webapp\src\pages\Create.tsx",
    "webapp\src\pages\Favorites.tsx",
    "webapp\src\pages\Works.tsx",
    "webapp\src\pages\About.tsx",
    "webapp\src\pages\Category.tsx",
    "webapp\src\pages\Explore.tsx",
    "webapp\src\pages\Generate.tsx",
    "webapp\src\pages\Payments.tsx",
    "webapp\src\pages\Settings.tsx",
    "webapp\src\pages\Shop.tsx",
    "webapp\src\pages\TemplatePage.tsx",
    "webapp\src\pages\Tokens.tsx",
    "webapp\src\pages\Welcome.tsx",
    "webapp\src\styles.css",
    "webapp\src\pages\Settings.tsx",
    "webapp\src\pages\Payments.tsx",
    "webapp\src\admin\Showcase.tsx"
)
foreach ($p in $old) {
    if (Test-Path $p) {
        Remove-Item $p
        Write-Host "Removed old file: $p"
    }
}
Push-Location webapp
npm install
npm run build
Pop-Location
if (-not (Test-Path "webapp\dist\index.html")) {
    Write-Host "Сборка не получилась: webapp/dist/index.html не создан. Исправьте ошибки выше и запустите скрипт снова." -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "Mini App собран. Railway НЕ собирает приложение сам — отправьте папку webapp/dist в репозиторий:" -ForegroundColor Yellow
Write-Host "  git add -A" -ForegroundColor Yellow
Write-Host "  git commit -m update" -ForegroundColor Yellow
Write-Host "  git push" -ForegroundColor Yellow
Write-Host ""
Write-Host "После деплоя откройте https://ваш-домен/api/version — build и webapp_build должны совпадать." -ForegroundColor Yellow
Write-Host "Done. Now run: python -m app.main"
