import sys
sys.path.insert(0, 'e:/Code/JM-Aura')

from backend.core.api_adapter import adapt_search_result, adapt_album_detail
from backend.core.req import GetSearchCategoryReq2, GetBookInfoReq2

print("Testing leaderboard API...")
raw = GetSearchCategoryReq2(category='0', page=1, sort='like').execute()
print('Raw data type:', type(raw))
if isinstance(raw, dict):
    print('Keys:', list(raw.keys())[:20])
    content = raw.get('content', [])
    if content:
        print('First item keys:', list(content[0].keys())[:20])

items = adapt_search_result(raw)
if items:
    print('Adapted first item keys:', list(items[0].keys()))
    print('Adapted tags:', items[0].get('tags'))
    
    # Test getting detail for first item
    album_id = items[0].get('album_id')
    if album_id:
        print(f'\nTesting detail API for album_id={album_id}...')
        detail_raw = GetBookInfoReq2(album_id).execute()
        print('Detail raw type:', type(detail_raw))
        if isinstance(detail_raw, dict):
            print('Detail keys:', list(detail_raw.keys())[:20])
            print('Has tags:', 'tags' in detail_raw)
            print('tags value:', detail_raw.get('tags'))
        
        detail = adapt_album_detail(detail_raw)
        print('Adapted detail tags:', detail.get('tags'))
