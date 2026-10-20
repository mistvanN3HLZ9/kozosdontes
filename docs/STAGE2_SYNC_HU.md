# KözösDöntés – 2. szakasz: változásfigyelés és kézi, ellenőrizhető import

Ez **nem** a valódi Országgyűlési API éles bekötése. A minták teljesen kitaláltak.
NEM kér API-hozzáférést, NEM tárol titkokat, NEM ír automatikusan a távoli D1-be.

## A csomag tartalma

- `0002_sync_audit.sql` – D1 migráció, amely `created` és `changed` eseményt naplóz változó checksum esetén.
- `parliament_import.py` – stabilabb XML-checksum: a puszta behúzás/sorköz nem generál módosításriasztást.
- `sync_preview.py` – két XML-pillanatkép összehasonlítása és review-ra alkalmas JSON-riport + idempotens SQL.
- `parliament_sample_v2.xml` – fiktív XML-módosítás és új rekord.
- `test_sync_preview.py` – szinkronizációs/SQL/tranzakciós tesztek.
- `sync-preview.yml` – GitHub Actions dry run, teszt-artifacttal, távoli írás nélkül.

## Telepítés

A ZIP **fedőcsomag**, nem teljes alkalmazás: tartalmát másold a meglévő `ogy-kozosseg-mvp` mappa gyökerébe.
Ez **frissíti** a korábbi `tools/parliament_import.py` fájlt, de nem írja felül a Cloudflare azonosítódat, a React appot, a meglévő D1-et és az `.env` fájlokat. A régi checksumok és az új, formázásfüggetlen checksumok eltérhetnek; korábban importált rekordoknál az első új import technikai checksum-változást naplózhat.

PowerShell a projekt gyökerében:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\kozosdontes-stage2-sync-patch.zip" -DestinationPath . -Force
npm.cmd run db:local
py -m unittest discover -s tests -p "test_*.py" -v
```

`npm.cmd run db:local` új migrációként alkalmazza a `0002_sync_audit.sql` fájlt a **helyi** adatbázisodra.

## Első, teljesen offline összehasonlítás

```powershell
py tools/sync_preview.py `
  --before fixtures/parliament_sample.xml `
  --after fixtures/parliament_sample_v2.xml `
  --mapping config/mapping.sample.json `
  --kind demo `
  --report imports/sync-report.json `
  --sql imports/sync-pending.sql
```

Várható: `created=1`, `changed=1`, `unchanged=1`, `missing_not_deleted=0`.

A jelentés és az SQL megtekintése:

```powershell
Get-Content imports/sync-report.json -Encoding UTF8
Get-Content imports/sync-pending.sql -Encoding UTF8 | Select-Object -First 15
```

**Az SQL nem fut le magától.** Ha leellenőrizted:

```powershell
npx.cmd wrangler d1 execute ogy-kozosseg-db --local --file=./imports/sync-pending.sql
```

Ha az első v1 mintát még nem importáltad korábban, a változásnapló a v2 adatok első beszúrását `created`-ként fogja rögzíteni. A `changed` esemény megfigyeléséhez előbb importáld a v1 XML-t:

```powershell
py tools/parliament_import.py import fixtures/parliament_sample.xml --mapping config/mapping.sample.json --kind demo --output imports/initial.sql
npx.cmd wrangler d1 execute ogy-kozosseg-db --local --file=./imports/initial.sql
# Ezután jöhet a sync-pending.sql, ha a v2 import még nem futott le.
```

Utolsó események helyi lekérdezése:

```powershell
npx.cmd wrangler d1 execute ogy-kozosseg-db --local --command "SELECT external_id,event_type,recorded_at FROM proposal_sync_events ORDER BY id DESC LIMIT 10;"
```

A `sync_runs` tábla a feldolgozott rekordok számát naplózza, **nem** az új/módosult tételek számát.

## Éles felhőadatbázis migrációja (csak amikor a tesztek jók)

Előzetesen nézd meg a migrációt, ellenőrizd, hogy a `wrangler.jsonc` a saját, valódi D1 UUID-det tartalmazza.

```powershell
npx.cmd wrangler d1 migrations list ogy-kozosseg-db --remote
npx.cmd wrangler d1 migrations apply ogy-kozosseg-db --remote
```

Ez kizárólag a naplózó táblát/triggereket hozza létre. **Ne** futtasd a `sync-pending.sql` fájlt `--remote` opcióval: a tesztadatok nem valók az éles adatbázisba.

## GitHub

```powershell
git add migrations/0002_sync_audit.sql tools/parliament_import.py tools/sync_preview.py tests/test_sync_preview.py fixtures/parliament_sample_v2.xml docs/STAGE2_SYNC_HU.md .github/workflows/sync-preview.yml
git commit -m "feat: preview parliamentary sync changes and audit D1 updates"
git push
```

GitHub → Actions → **Parliament sync preview (synthetic, NO DEPLOY)** → Run workflow.
A `synthetic-sync-preview` artifact JSON-riportot és a kitalált SQL-t tartalmazza.

## API-hozzáférés megérkezésekor

1. Ellenőrizni a felhasználási, kvóta- és hitelesítési feltételeket.
2. A valós XML-sémát **titkok nélkül** megvizsgálni, `mapping.real...` mezőket ellenőrizni.
3. Hivatalos adatoknál a mappinghez `"verified_for_official_api": true` megjelölés szükséges, és explicit `--allow-official` kapcsoló; ez *nem* jogi vagy valóságellenőrzési garancia.
4. A közösségi szavazások és a parlamenti szavazások megfelelő összekapcsolását külön validálni.
5. Csak ellenőrzött tesztek, jóváhagyott API-feltételek és sikeres dry run után engedélyezni az időzített, hitelesített szinkront.

### Védelmi korlátok

- A pillanatkép összehasonlítás NEM egyenlő az élő adatbázis tényleges aktuális állapotával.
- Az API listák gyakran lapozottak: a listából hiányzó tétel nem jelenti annak törlését.
- A csak behúzás/sorköz által eltérő XML-elemeket az új checksum általában változatlannak tekinti. Más XML-szintű változás továbbra sem feltétlenül jogi/tartalmi változás.
- Semmilyen új rekord nem válik automatikusan `ballot`-tá, nem nyitja meg a szavazást, és nem publikál AI-magyarázatot.
- A szavazatok és személyes adatok táblái változatlanok.
