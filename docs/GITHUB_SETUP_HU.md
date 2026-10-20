# GitHub előkészítés – Windows PowerShell

**Fájlcsomag verzió:** 1.1. Csak fejlesztői és CI-előkészítés. Nem engedélyez automatikus éles telepítést vagy külső szinkronizálást.

## 1. Az 1.1 javítócsomag alkalmazása

Másold a ZIP fájlt a projekt gyökérmappájába, majd ott PowerShellben:

```powershell
Expand-Archive .\kozosdontes-github-elokeszites-1.1.zip -DestinationPath . -Force
```

Ha a ZIP a Letöltésekben található, add meg az abszolút elérési útját. Ez a patch a `package.json`, `wrangler.jsonc`, `tests/test_importer.py` fájlokat felülírja. A lokális `.wrangler` adatbázist **nem** módosítja. Ha a fenti fájlokban saját módosításokat végeztél, előbb készíts róluk másolatot.

## 2. Ellenőrzés

```powershell
npm.cmd run check
npm.cmd run build
npm.cmd run test:import
```

Várt: TypeScript és build hiba nélkül, 6 Python teszt sikeres. Ha az npm parancs Windows PowerShellben tiltott, továbbra is `npm.cmd`-t használj.

## 3. Git telepítése

```powershell
git --version
```

Ha hiányzik:

```powershell
winget install --id Git.Git -e
```

Indíts új PowerShellt.

## 4. GitHub repo

A https://github.com/new oldalon hozd létre a `kozosdontes` repositoryt. Public repositoryt választhatsz, mivel a cél a nyitott forráskód, de **ne** kapcsolj be sem README, sem .gitignore generálást. A közzétett kódra érvényes nyílt forráskódú licencet külön válassz (a puszta Public beállítás önmagában nem ad felhasználási engedélyt).

A projekt gyökerében:

```powershell
git init -b main
git config user.name "SAJAT_GITHUB_NEV"
git config user.email "SAJAT_GITHUB_EMAIL"
git add .
git status --short
git check-ignore .wrangler node_modules .dev.vars .env
```

**Mielőtt commitolsz:** a `git status --short` listában ne legyen `node_modules/`, `.wrangler/`, `.dev.vars`, `.env`, token, személyes adat, saját letöltött API XML, illetve nem szándékosan létrehozott `.sql` import. A `package-lock.json` kerüljön bele a commitba.

```powershell
git commit -m "chore: bootstrap civic parliament MVP"
git remote add origin https://github.com/SAJAT_FELHASZNALONEV/kozosdontes.git
git push -u origin main
```

A `SAJAT_FELHASZNALONEV` helyére írd a tényleges GitHub felhasználónevet. Az első `git push` böngészős bejelentkezést kérhet.

## 5. Github Actions ellenőrzése

A repository GitHub oldalán nyisd meg az **Actions** lapot.

- A `Verify source` workflow automatikusan teszteli a kódot.
- A `Parliament sync fixture dry run` workflow kézzel futtatható: Actions → workflow → Run workflow. Ez **csak kitalált fixture** adatokon tesztel, és nem ír Cloudflare adatbázisba.

## 6. Mit NEM kapcsolunk még be?

Nincs API titok GitHubban; nincs időzített éles import, automatikus telepítés vagy publikus szavazás. A valódi parlamenti API válasza és felhasználási feltételei alapján később konfiguráljuk a lekérdezéseket.

Ha majd titkot kell használni, GitHub **Settings → Secrets and variables → Actions** helyen tároljuk, a legkisebb szükséges jogosultsággal. Titkot sem commitba, sem képernyőképre, sem hibajegybe nem teszünk.
