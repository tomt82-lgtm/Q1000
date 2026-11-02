# Qmusic THX TO YOU Top 1000 (2026) → Soundiiz → Apple Music

Deze GitHub Actions-workflow haalt ieder halfuur nummers op uit de API van Qmusic, bewaart eerdere nummers en publiceert `docs/playlist.json` voor Soundiiz. Je Mac hoeft niet aan te blijven.

## Installeren (één keer)

1. Maak op https://github.com/new een **openbare** repository, bijvoorbeeld `qmusic-top1000-2026`. (Publiceer hierin geen persoonlijke gegevens.)
2. Upload `update.py`, de map `.github/workflows/` en deze `README.md` naar de hoofdmap. Maak ook een lege map `docs` met daarin een `.gitkeep` bestand.
3. Open in GitHub **Actions → Update Qmusic Top 1000 → Run workflow**. Controleer of de run slaagt. Als hij faalt, kijk naar de foutmelding. De API kan andere veldnamen teruggeven; dan moet de omzetter worden aangepast.
4. Open **Settings → Pages → Build and deployment → Deploy from a branch → main /docs → Save**. Kies de `docs`-map zodra de eerste run `playlist.json` heeft aangemaakt.
5. Na de eerste geslaagde run wordt de openbare JSON-link doorgaans:
   `https://GEBRUIKERSNAAM.github.io/qmusic-top1000-2026/playlist.json`
   Test die link in een privévenster. Je moet JSON zien met `title` en `tracklist`.
6. Open Soundiiz → **Tools / Synchronize** (of **Automation / My Syncs**) → **Playlist URL**, plak je JSON-link, kies je gekoppelde Apple Music-account als bestemming, **Add** en **Daily**.
7. Controleer via Soundiiz de import en het aantal herkende nummers. Voor een lijst met meer dan 200 nummers is een betaald Soundiiz-abonnement nodig.

## Belangrijke kanttekeningen

- Op het screenshot van 2 november 2026 retourneerde `played?limit=1000` 19 nummers. Controleer tijdens de uitzending of dit aantal blijft meegroeien; het betekent niet dat de volledige Top 1000 nu al beschikbaar is.
- De screenshot toont velden `position`, `title` en `artist.name` in `tracks`. Een echte test van het script tegen de live-API is nog niet uitgevoerd.
- GitHub Actions is niet gegarandeerd exact op het ingestelde tijdstip; geplande jobs kunnen vertraagd of overgeslagen worden. Inactieve workflows kunnen worden uitgeschakeld.
- Soundiiz synchroniseert op zijn eigen dagelijkse schema, niet halfuurlijks. `Add` bewaart bestaande nummers maar garandeert geen correcte rangorde. Voor exacte Top 1000-rangschikking moet de API de positie leveren en de software die sorteren; met `Replace` kan Soundiiz dan de volgorde herstellen.
- Het script sorteert op officiële rangpositie (1000 naar 1), onafhankelijk van de volgorde in de API.
- Sommige nummers kunnen door Soundiiz verkeerd gematcht worden; controleer de uiteindelijke Apple Music-lijst.
- Stop de workflow na de uitzending of schakel het schema uit als de playlist compleet is.


### Aanpassing 2 november 2026
De API levert `tracks[].position`, `tracks[].title` en `tracks[].artist.name`. De verzamelaar archiveert nu per officiële hitlijstpositie in `docs/chart-positions.json` en publiceert in aflopende positievolgorde. Het Qmusic-veld `count` geeft het momenteel aantal beschikbare nummers aan; `total` is 1000. De uitkomst en beperkingen (API-limieten, catalogusmatching, GitHub-schematiming) moeten na installatie gecontroleerd worden.
