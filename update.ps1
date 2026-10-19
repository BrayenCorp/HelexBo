# Update Nolla AI: removes old files that no longer exist and builds the Mini App.
# Run from the project folder:  .\update.ps1
$old = @(
    "webapp\src\admin\Staff.tsx",
    "webapp\src\pages\Catalog.tsx",
    "webapp\src\pages\Create.tsx",
    "webapp\src\pages\Favorites.tsx",
    "webapp\src\pages\Works.tsx"
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
Write-Host "Done. Now run: python -m app.main"
