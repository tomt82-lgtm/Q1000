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
            if date.year >= 2026 and isinstance(entry.get('id'), int):
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


def read_existing(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    return data.get('tracklist', [])


def merge_unique(*lists):
    result = {}
    for items in lists:
        for song in items:
            title, artist = song.get('title'), song.get('artists')
            if title and artist:
                key = (key_text(title), key_text(artist))
                if key not in result:
                    result[key] = {'title': str(title).strip(), 'artists': str(artist).strip()}
    return list(result.values())


def write_json(path, data):
    content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if not path.exists() or path.read_text(encoding='utf-8') != content:
        path.write_text(content, encoding='utf-8')


def main():
    editions = get_editions()
    if not editions:
        raise RuntimeError('Geen edities vanaf 2026 gevonden; bestanden niet wijzigen')
    yearly = {}
    for date, edition_id in editions:
        yearly.setdefault(date.year, []).append((date, edition_id))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    combined_years = []
    for year in sorted(yearly):
        output = OUTPUT.parent / f'qtop40-{year}.json'
        status = OUTPUT.parent / f'qtop40-{year}-status.json'
        existing = read_existing(output)
        fresh = []
        successes = []
        incomplete = []
        for date, edition_id in yearly[year]:
            try:
                tracks, count = read_week(edition_id)
            except Exception as exc:
                incomplete.append({'date': date.isoformat(), 'edition_id': edition_id, 'error': str(exc)})
                continue
            if tracks is None:
                incomplete.append({'date': date.isoformat(), 'edition_id': edition_id, 'positions_found': count})
                continue
            successes.append({'date': date.isoformat(), 'edition_id': edition_id})
            fresh.extend(tracks)
            time.sleep(.1)
        if not successes and not existing:
            raise RuntimeError(f'Geen volledige weekedities in {year}; bestaande bestanden niet wijzigen')
        songs = merge_unique(existing, fresh)
        write_json(output, {
            'title': f'Qmusic – Q-Top 40 Jaarcollectie {year}',
            'description': f'Unieke nummers uit de Qmusic Q-Top 40 van {year}, vanaf 2026 automatisch per jaar aangevuld.',
            'tracklist': songs,
        })
        write_json(status, {
            'last_checked_utc': datetime.now(timezone.utc).isoformat(),
            'complete_weeks': successes,
            'incomplete_weeks': incomplete,
            'unique_tracks': len(songs),
            'total_editions_found': len(yearly[year]),
        })
        combined_years.extend(songs)
        print(f'{year}: {len(successes)}/{len(yearly[year])} volledige edities, {len(songs)} unieke nummers')
        if incomplete:
            print(f'Waarschuwing: {len(incomplete)} onvolledige edities in {year}', file=sys.stderr)

    all_file = OUTPUT.parent / 'qtop40-alle-jaren.json'
    all_songs = merge_unique(read_existing(all_file), combined_years)
    write_json(all_file, {
        'title': 'Qmusic – Q-Top 40 Alle jaren vanaf 2026',
        'description': 'Alle unieke Q-Top 40-nummers vanaf 2026, automatisch aangevuld.',
        'tracklist': all_songs,
    })
    print(f'Alle jaren: {len(all_songs)} unieke nummers')


if __name__ == '__main__':
    main()
