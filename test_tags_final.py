# -*- coding: utf-8 -*-
import requests

# Test leaderboard API returns tags
r = requests.get('http://127.0.0.1:8000/api/v2/jm/leaderboard?sort=like')
data = r.json()
items = data.get('data', [])

print(f'Total items: {len(items)}')
print('\nFirst 5 items with tags:')
for i in range(min(5, len(items))):
    item = items[i]
    title = item.get('title', '')[:30]
    tags = item.get('tags', [])[:5]
    print(f'{i+1}: {title} - Tags: {tags}')

# Check for Korean comics
print('\nChecking for Korean comics...')
korean_count = 0
for item in items:
    tags = item.get('tags', [])
    if '' in tags:
        korean_count += 1

print(f'Found {korean_count} Korean comics in the leaderboard')
