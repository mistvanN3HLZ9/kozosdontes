# 2. fázis – parlamenti adatszinkron előkészítési terv

Állapot: **a hozzáférési kérelem elküldve; API-válaszra várunk**.

## Már megvalósítható

1. Kód GitHub-repositoryban, CI aktív.
2. Importáló helyi, kitalált XML-fixture-rel tesztelve.
3. Github Actions kézi `Parliament sync fixture dry run` workflow.
4. Helyi D1 migráció és idempotens tesztimport.

## Mi kell az éles szinkronhoz?

- Írásos hozzáférési és újraközlési feltételek az Országgyűlés Hivatalától.
- Valódi, **titkoktól megtisztított** XML-minta vagy kizárólag strukturális elemnévlista.
- A lista/azonosító/státusz/szavazás mezők hivatalos megfeleltetése.
- Javaslatverziók, módosítások, végszavazás pontos kapcsolása.
- Olyan éles import, amely kizárólag előzetesen érvényesített, forráscímkézett adatot ír.
- Hibás adatforrásnál semmit sem publikáló fail-closed működés.
- Időzítés és kvótakezelés: kezdetben napi néhány szinkron, csak engedély esetén.

## Titkok és adatvédelem

Ne ossz meg `PARLIAMENT_ACCESS_TOKEN` értéket. Helyi `.env` / `.dev.vars` verziókezelésből kizárva. XML nyersválaszok és generált SQL importok az `imports/` könyvtárban, `.gitignore` által kizárva.

## Megjegyzés

A jelenlegi mintakonfigurációk (`mapping.real.example.json`) hipotetikus mezőneveket tartalmaznak. Nem kapcsoljuk automatán élő rendszerre addig, amíg valós válaszon nincsenek ellenőrizve.
