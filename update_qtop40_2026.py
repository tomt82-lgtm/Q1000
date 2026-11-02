#!/usr/bin/env python3
"""Build unique Q-Top 40 2026 year collection from Qmusic's public API."""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = 'https://api.qmusic.be/2.0/lists/125'
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'docs' / 'qtop40-2026.json'
REPORT = ROOT / 'docs' / 'qtop40-2026-status.json'
USER_AGENT = 'QTop40YearCollector/1.0 (public Qmusic chart archive)'


def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}), timeout=25) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            if attempt == 2:
                raise RuntimeError(f'API-opvraag mislukt: {url}: {exc}') from exc
            time.sleep(2 * (attempt + 1))


def key_text(text):
    text = unicodedata.normalize('NFKC', str(text)).casefold()
    return re.sub(r'\s+', ' ', text).strip()


def get_editions():
    url = f'{API}/editions?order=reverse'
    visited = set()
    result = []
    while url not in visited:
        visited.add(url)
        data = fetch(url)
        if not isinstance(data, dict) or not isinstance(data.get('editions'), list):
            raise RuntimeError('Onverwacht formaat van de editie-API')
        for entry in data['editions']:
            # Gebruik de vermelde editie-datum, want happened_on kan afwijken.
            name = str(entry.get('name', ''))
            try:
                date = datetime.strptime(name[:10], '%d/%m/%Y').date()
            except ValueError:
                continue
            if date.year == 2026 and isinstance(entry.get('id'), int):
                result.append((date, entry['id']))
        page = int(data.get('page') or 1)
        pages = int(data.get('pages') or 1)
        if page >= pages:
            break
        url = f'{API}/editions?order=reverse&page={page + 1}'
        time.sleep(.15)
    return sorted(set(result))


def read_week(edition_id):
    found = []
    for page in range(1, 4):
        payload = fetch(f'{API}/editions/{edition_id}/tracks/played?limit=100&page={page}')
        if not isinstance(payload, dict) or not isinstance(payload.get('tracks'), list):
            raise RuntimeError(f'Onverwacht trackformaat voor editie {edition_id}')
        found.extend(payload['tracks'])
        page_count = int(payload.get('pages') or 1)
        if page >= page_count or not payload['tracks']:
            break
    valid = []
    for track in found:
        title = track.get('title') or track.get('name')
        artist = track.get('artist')
        if isinstance(artist, dict):
            artist = artist.get('name')
        if not artist:
            artist = track.get('artists')
        if isinstance(artist, list):
            artist = ', '.join((x.get('name') if isinstance(x, dict) else str(x)) for x in artist)
        pos = track.get('position')
        if title and artist and isinstance(pos, int) and 1 <= pos <= 40:
            valid.append({'title': str(title).strip(), 'artists': str(artist).strip(), 'position': pos})
    # Een volledige Top 40 moet 40 verschillende posities hebben.
    positions = [t['position'] for t in valid]
    if len(set(positions)) != 40:
        return None, len(set(positions))
    return sorted(valid, key=lambda t: t['position']), 40


def main():
    editions = get_editions()
    if not editions:
        raise RuntimeError('Geen edities uit 2026 gevonden; bestaande lijst niet wijzigen')
    unique = {}
    successes = []
    incomplete = []
    for date, edition_id in editions:
        try:
            tracks, count = read_week(edition_id)
        except Exception as exc:
            incomplete.append({'date': date.isoformat(), 'edition_id': edition_id, 'error': str(exc)})
            continue
        if tracks is None:
            incomplete.append({'date': date.isoformat(), 'edition_id': edition_id, 'positions_found': count})
            continue
        successes.append({'date': date.isoformat(), 'edition_id': edition_id})
        for song in tracks:
            key = (key_text(song['title']), key_text(song['artists']))
            if key not in unique:
                unique[key] = {'title': song['title'], 'artists': song['artists']}
        time.sleep(.1)
    if not successes:
        raise RuntimeError('Geen enkele volledige editie gevonden; bestaande lijst niet wijzigen')
    playlist = {
        'title': 'Qmusic – Q-Top 40 Jaarcollectie 2026',
        'description': 'Alle unieke nummers uit de volledig gecontroleerde weekedities van Qmusic Q-Top 40 in 2026. Volgorde: eerste verschijning in het jaar.',
        'tracklist': list(unique.values()),
    }
    report = {
        'last_checked_utc': datetime.now(timezone.utc).isoformat(),
        'complete_weeks': successes,
        'incomplete_weeks': incomplete,
        'unique_tracks': len(unique),
        'total_editions_found': len(editions),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(playlist, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Volledige edities: {len(successes)}/{len(editions)}; unieke nummers: {len(unique)}; onvolledig: {len(incomplete)}')
    if incomplete:
        print('OPGELET: sommige weken ontbreken; zie docs/qtop40-2026-status.json', file=sys.stderr)


if __name__ == '__main__':
    main()
