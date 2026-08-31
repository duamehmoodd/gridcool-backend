import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('temperature-api-quickstart/.env')
import src.api.fortyguard_extra as fg
from src.data_prep.city_metadata import get_city_metadata
import requests
from datetime import datetime, timezone, timedelta

meta = get_city_metadata('phoenix_az')

test_dates = [
    ('today', datetime.now(timezone.utc)),
    ('1 day ago', datetime.now(timezone.utc) - timedelta(days=1)),
    ('3 days ago', datetime.now(timezone.utc) - timedelta(days=3)),
    ('7 days ago', datetime.now(timezone.utc) - timedelta(days=7)),
]

for label, dt in test_dates:
    date_str = dt.strftime('%Y-%m-%d')
    time_str = dt.strftime('%H:00')
    payload = {
        'polygon_aoi': fg._bbox_for(meta),
        'date_time': {'start_date': date_str, 'start_time': time_str, 'filter_type': 1},
        'granularity': 100
    }
    resp = requests.post('https://api.fortyguard.com/v1/heatmap', headers=fg._headers(), json=payload, timeout=30)
    if resp.status_code != 200:
        print(label, date_str, time_str, 'SUBMIT FAILED', resp.text)
        continue
    activity_id = resp.json()['data']['activity_id']
    result = fg._poll(activity_id)
    n = len(result.get('map_data', {}).get('features', []))
    print(label, date_str, time_str, 'features:', n)