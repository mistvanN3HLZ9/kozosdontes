# Architektúra és fejlesztési döntések

```text
Böngésző
   │ GET /        ──→ Cloudflare static assets (Vite build)
   └ GET /api/*   ──→ Workers REST API ──→ D1 (SQLite)

API-hozzáférés után:
Országgyűlés Web API (XML) ──→ Python XML inspektor/import ──→ ellenőrzött SQL ──→ D1
                                   ↑
                           Token csak környezetben
```

## Miért egy Cloudflare Worker?

A Vite Cloudflare plugin segítségével a SPA és a Worker API egy telepítési egység. Ugyanaz a domain, nem kell CORS és nincs két szolgáltatás között külön üzemeltetési függőség. Az ingyenes kvótákat rendszeresen ellenőrizni kell.

## Adatimport

Az adatimport két részre oszlik: (a) hiteles API-válasz lekérése; (b) explicit mapping alapján D1 SQL készítése. **Sémaellenőrzés nélkül nincs automatikus hivatalos import.** A script idempotens, mert `external_id` egyedi és a verziók `(proposal_id, source_checksum)` páros szerint egyediek.

A dokumentumoknak később egyedi forrásazonosítója, a szöveghelynek és a tartalom SHA256 lenyomatának kell lennie. Az összegzéseket nem írhatjuk felül verziózás nélkül.

## API szerződés – első fázis

`GET /api/health` ⇒ `{ "status":"ok", "database":"d1", "version":"0.1.0" }`.

`GET /api/proposals?limit=12&page=1&kind=official` ⇒ `{ "data": Proposal[], "pagination": {"page":1,"limit":12,"total":0} }`.

`GET /api/proposals/:slug` ⇒ `{ "proposal": Proposal, "versions": [], "documents": [], "explanation": null }`.

A nem létező rekord `404`; az egyéb metódus `405`; adatbázishiba `500` és nem szolgáltat ki érzékeny részleteket.

## Következő fázisokhoz előkészített, de NEM működő táblák

`user_profiles`, `ballots`, `votes`, `topic_rounds`, `topic_preferences`, `explanations`, `error_reports`, `audit_events`.

A szavazás bekapcsolásakor elengedhetetlen: hitelesített Firebase ID token szerveroldali validációja, igazolt email-állapot, tranzakcionális írás, `UNIQUE(ballot_id,user_uid)`, CSRF/abuse védelem, rate limiting, adatvédelmi felülvizsgálat.

## Különbség a nyilvános demo és az éles politikai adat között

`record_kind=demo` jelölés kötelező a kitalált példákon. Valódi iromány csak manuálisan ellenőrzött `record_kind=official` státusszal kerülhet be. Az oldal szavazás funkciója nincs bekapcsolva, ezért semmilyen demonstráció nem értelmezhető közvéleménykutatásként.
