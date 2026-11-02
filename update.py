#!/usr/bin/env python3
"""Qmusic THX TO YOU 1000 (2026) -> Soundiiz public JSON.

Stores chart entries by *position* so a repeated recording in the chart is not
silently dropped. Publish descending chart positions (1000, 999, ..., 1).
"""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = os.getenv('QMUSIC_API', 'https://api.qmusic.be/2.9/lists/473/editions/7397/tracks/played?limit=1000')
OUTPUT = Path('docs/playlist.json')
STATE = Path('docs/chart-positions.json')


def fetch():
    request = Request(SOURCE, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; QmusicChartArchive/1.0)',
        'Accept': 'application/json',
    })
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def get_artist(row):
    a = row.get('artist') or row.get('artists') or row.get('artist_name')
    if isinstance(a, dict):
        return a.get('name', '')
    if isinstance(a, list):
        return ', '.join((x.get('name', '') if isinstance(x, dict) else str(x)) for x in a)
    return a if isinstance(a, str) else ''


def parse(row):
    if not isinstance(row, dict):
        return None
    # The Qmusic API has title, artist.name and position on each tracks[] entry.
    track = row.get('track') if isinstance(row.get('track'), dict) else row
    title = track.get('title') or row.get('title')
    artist = get_artist(track) or get_artist(row)
    position = row.get('position') or track.get('position')
    try:
        position = int(position)
    except (TypeError, ValueError):
        return None
    if not (1 <= position <= 1000 and isinstance(title, str) and title.strip() and artist.strip()):
        return None
    entry = {'title': title.strip(), 'artists': artist.strip()}
    isrc = track.get('isrc') or row.get('isrc')
    if isinstance(isrc, str) and isrc.strip():
        entry['isrc'] = isrc.strip()
    return position, entry


def main():
    data = fetch()
    if not isinstance(data, dict) or not isinstance(data.get('tracks'), list):
        raise ValueError('The API returned no valid tracks list; retaining previous output.')
    if data.get('list_name') != 'THX TO YOU 1000' or str(data.get('edition_name')) != '2026':
        raise ValueError('Unexpected chart identity; retaining previous output.')
    incoming = data['tracks']
    saved = json.loads(STATE.read_text('utf-8')) if STATE.exists() else {}
    parsed = [v for row in incoming if (v := parse(row))]
    if incoming and not parsed:
        raise ValueError('Tracks were returned, but none had position/title/artist.')
    for position, entry in parsed:
        saved[str(position)] = entry
    if not saved:
        raise ValueError('No chart entries available yet; refusing empty playlist.')
    ordered = sorted(saved, key=lambda key: int(key), reverse=True)
    playlist = {
        'title': 'Qmusic – THX TO YOU Top 1000 (2026)',
        'description': 'Qmusic THX TO YOU 1000 (2026), in bekendmakingsvolgorde, vanaf positie 1000.',
        'tracklist': [saved[key] for key in ordered],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    OUTPUT.write_text(json.dumps(playlist, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(f'API count={data.get("count")}; received={len(incoming)}; parsed={len(parsed)}; saved positions={len(ordered)}')


if __name__ == '__main__':
    main()
