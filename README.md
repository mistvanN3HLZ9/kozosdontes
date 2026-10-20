# KözösDöntés – 1. fejlesztési szakasz

> **Független parlamenti döntésfigyelő – technikai MVP-alap**  
> Állapot: **fejlesztői demó**. A demórekordok kitaláltak. Regisztráció, éles szavazás, AI-magyarázat és automatikus valós API-szinkron **még nincs bekapcsolva**.

## Mit tartalmaz ez a repository?

- React + TypeScript + Vite reszponzív frontend, magyar szövegekkel.
- Cloudflare Workers backend: `/api/health`, `/api/proposals`, `/api/proposals/:slug`.
- Cloudflare D1 adatbázis 1 SQL migrációval és összes későbbi fő entitás alapmodelljével.
- Öt **egyértelműen kitalált** demo-téma, kizárólag a helyi adatbázisba betölthető fixture-ként.
- Python XML-inspektor és konfigurálható, idempotens SQL-importáló.
- Hat futtatható Python teszt, amelyek egyebek mellett a sémát, az import duplikációmentességét és az egy fiók/egy szavazat megszorítást ellenőrzik.
- GitHub Actions alapellenőrző workflow.

### Könyvtárstruktúra

```text
ogy-kozosseg-mvp/
├── src/                 React frontend, stílusok, API típusok
├── worker/              Cloudflare Worker API
├── migrations/          D1 adatbázismigrációk
├── fixtures/            KITALÁLT lokális mintaadatok
├── config/              XML mezőmegfeleltetési példák
├── tools/               XML inspektor / SQL importáló
├── tests/               Python import- és sématesztek
├── docs/                Architektúra és további fejlesztési döntések
├── .github/workflows/   CI ellenőrzés (NEM telepít automatikusan)
├── vite.config.ts
└── wrangler.jsonc
```

## 0. Előkészítés – Windows PowerShell

Szükséges: **Node.js 22 LTS vagy újabb támogatott verzió**, npm, Python 3.11+, Git.

```powershell
node --version
npm --version
python --version
```

Csomagold ki a ZIP-et, majd lépj a `ogy-kozosseg-mvp` mappába:

```powershell
cd .\ogy-kozosseg-mvp
npm install
```

Az `npm install` hálózati hozzáférést igényel; létrehozza a `package-lock.json` fájlt. **Tedd be a lockfájlt a Git-re**, a CI-t ezután átállíthatod `npm ci` parancsra. A forrásokhoz nem kell fizetős felhőszolgáltatás.

## 1. Helyi D1 adatbázis

```powershell
npm run db:local
npm run db:seed
```

A seed öt **kitalált** témát tölt be, és külön DEMÓ címkét alkalmaz. Ne használd éles közvélemény-kutatásra.

A `wrangler.jsonc` fájlban a `database_id` nullás helyőrzője **helyi fejlesztéshez** használható. Valódi Cloudflare telepítés előtt ki kell cserélni a létrehozott D1 adatbázis UUID-jére.

## 2. Fejlesztői szerver

```powershell
npm run dev
```

Nyisd meg a Vite konzol által kijelzett címet (alapesetben `http://127.0.0.1:5173`).

Ellenőrző végpontok:

```powershell
Invoke-RestMethod http://127.0.0.1:5173/api/health
Invoke-RestMethod 'http://127.0.0.1:5173/api/proposals?limit=5'
Invoke-RestMethod http://127.0.0.1:5173/api/proposals/demo-lakhatasi-tamogatas
```

Várt eredmény: a health `status = ok`, a lista öt demórekordot ad, a részletes adatlap forrás és AI-magyarázat híján erre egyértelműen figyelmeztet.

## 3. Projekt ellenőrzése

```powershell
npm run check
npm run build
npm run test:import
```

A Python tesztekhez **nem kell npm** és nincs külső Python-függőség. A GitHub Actions is elvégzi az ellenőrzést minden push/PR során.

## 4. Parlament Web API – hozzáférés és adatimport

Hivatalos tájékoztató: https://www.parlament.hu/w-api-tajekoztato

Hivatalos API kézikönyv: https://www.parlament.hu/documents/10181/122580/webapi_felhasznaloi_kezikonyv.pdf/ecd95564-d32d-4b84-9748-89c4833ea10d

A dokumentáció szerint a parlamenti Web API **előzetes hozzáférési kódot** használ. A regisztrációs elérhetőséget és feltételeket ellenőrizd a hivatalos tájékoztatón. A dokumentációban látható URL-ek között szerepel az `iromany.cgi` részletes adatlap és a `szavazasok.cgi` szavazások listája. **Az éles irománylista pontos válaszsémája és elérhetősége csak valódi, engedélyezett API-válasszal véglegesíthető.**

### 4/a. Teljes importlánc kitalált XML-ből

```powershell
python tools/parliament_import.py inspect fixtures/parliament_sample.xml
python tools/parliament_import.py import fixtures/parliament_sample.xml --mapping config/mapping.sample.json --kind demo --output imports/sample.sql
npx wrangler d1 execute ogy-kozosseg-db --local --file=./imports/sample.sql
```

Ez két további **demó** rekordot hoz létre. Az importot újrafuttatva nem keletkezik duplikáció.

### 4/b. Felkészülés éles XML-válaszra

A token **nem** kerül a git repositoryba. PowerShell munkamenetben:

```powershell
$env:PARLIAMENT_ACCESS_TOKEN = 'AZ_API_ALTAL_KIADOTT_TOKEN'
$env:PARLIAMENT_LIST_URL = 'AZ_ENGEDÉLYEZETT_HTTPS_PARLAMENT_HU_LISTA_ENDPOINT'
python tools/parliament_import.py fetch --output imports/parliament-real.xml
python tools/parliament_import.py inspect imports/parliament-real.xml
```

A tényleges XML elemei alapján **ellenőrizd és módosítsd** a `config/mapping.real.example.json` fájlt. A benne lévő mezőnevek **csak hipotézisek**, nem hitelesített valós mezőnevek. Ezután:

```powershell
python tools/parliament_import.py import imports/parliament-real.xml --mapping config/mapping.real.example.json --kind official --output imports/real.sql
# Ellenőrizd az importálásra váró rekordok címét, azonosítóját és SQL tartalmát!
npx wrangler d1 execute ogy-kozosseg-db --local --file=./imports/real.sql
```

Egyelőre kézi indítású import, **nem kész automatikus szinkronizáció**. A Python program kizárólag `https://parlament.hu` vagy aldomainjei URL-jét fogadja el a letöltéshez, és az XML DOCTYPE/ENTITY tiltott. A raw válasz a `.gitignore` miatt nincs verziókövetve.

### Fontos hiányosságok a későbbi szinkronhoz

- Tényleges hozzáférés és XML mezők ellenőrzése.
- Irományok, módosító irományok, önálló szavazások összerendelése.
- Valódi forrás PDF/HTML csatolása és dokumentumverziók differenciálása.
- Időzített futtatás, naplózás, vészjelzés, jóváhagyási felület.
- A hivatalos szavazás típusának és a felhasználói kérdés pontos megfeleltetése.

## 5. Cloudflare éles telepítés (amikor készen állsz)

1. Hozz létre ingyenes Cloudflare-fiókot.
2. Hitelesítsd a Wrangler CLI-t:

```powershell
npx wrangler login
```

3. Hozz létre **valódi** D1 adatbázist:

```powershell
npx wrangler d1 create ogy-kozosseg-db
```

4. Másold a kiadott `database_id` UUID-t a `wrangler.jsonc` megfelelő helyére. **Soha ne hagyd a nulla UUID-t az éles konfigurációban.**
5. Futtasd a távoli migrációt:

```powershell
npm run db:remote
```

6. Építsd és telepítsd a Workers appot:

```powershell
npm run deploy
```

A weboldal az így kapott `*.workers.dev` HTTPS-címen érhető el. **A remote adatbázis szándékosan üres**, tehát addig nem jelennek meg javaslatok, amíg ellenőrzött hivatalos rekordokat nem importálsz. Kitalált demo-adatokat **ne tölts fel éles környezetbe**.

A backend a frontenddel azonos originről érhető el, így nem kell külön CORS-szabályt nyitnunk. Nincsenek nyilvános importáló, adminisztrációs vagy szavazatíró API-k a jelenlegi verzióban.

## 6. Biztonság és adatvédelem

**Jelenlegi állapot:** a publikusan elérhető API csak olvas. Nincs felhasználói fiók, személyes adat gyűjtés vagy szavazatbeküldés. A későbbi adatbázisséma előkészített táblái nem jelentik azt, hogy a regisztráció és szavazás működik.

Éles szavazás és regisztráció csak megfelelő hitelesítés, szerveroldali jogosultságellenőrzés, adatkezelési tájékoztató, ellenőrzött törlési folyamat, rate limiting és security review után kapcsolható be. Egy megerősített email-cím **nem bizonyítja egy személy egyediségét**; az oldal eredményei önkéntes online felhasználók véleményét mutatják.

AI magyarázatot a jelenlegi verzió **nem generál és nem címkéz ellenőrzöttként**. A `published` rekordok API-ja már kész, de éles közzététel előtt forrásellenőrzésre és változatkezelésre van szükség.

## 7. Hibakeresés

- `500` az API-ban: valószínűleg a helyi migráció hiányzik. `npm run db:local`.
- Üres lista: nem töltöttél seedet. `npm run db:seed`.
- `wrangler deploy` invalid D1 database ID: hozd létre a D1-t és másold be az UUID-t.
- Vite Node engine hiba: frissíts Node 22 LTS-re.
- `parliament_import.py fetch` XML parsing hiba: lehet hozzáférési hiba, CAPTCHA vagy az endpoint HTML-t adott. Ne próbálkozz CAPTCHA megkerülésével; egyeztesd az API hozzáférést.
- Az npm verzióütközéseknél futtasd `npm install`, és az elkészült lockfájlt tartsd verziókövetésben. Az induló csomagban nincs `node_modules`.

## 8. Egyértelmű következő lépések

**2. fázis:** valós, engedélyezett parlamenti API XML-séma feltérképezése és automatikus szinkron; **3. fázis:** forráshivatkozásos AI-magyarázat; **4. fázis:** fiókok; **5. fázis:** biztonságos szavazatok és témaválasztás; **6. fázis:** nyilvános béta és adatvédelmi audit.

A projekt nonprofit, nyílt forrású mintaként fejleszthető; a licenc végleges megválasztása a repository tulajdonosának döntése.

## 9. GitHub repository létrehozása

A csomag **helyi Git-repository struktúra**, nem hoz létre automatikusan távoli GitHub repositoryt. VS Code terminálban vagy PowerShellben:

```powershell
git init
git add .
git commit -m "Initial MVP scaffold: Vite, Workers, D1, importer"
git branch -M main
```

GitHubon hozz létre egy üres `ogy-kozosseg-mvp` repositoryt (README nélkül, mert ez már benne van), majd:

```powershell
git remote add origin https://github.com/FELHASZNALONEVED/ogy-kozosseg-mvp.git
git push -u origin main
```

A valós API-token, `.env`, `.dev.vars`, lementett XML-válasz vagy személyes adat **soha ne legyen a commit része**. Az `npm install` után létrejött `package-lock.json` fájlt viszont javasolt commitolni a reprodukálható buildekhez.
