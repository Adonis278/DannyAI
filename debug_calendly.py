"""Debug Calendly API."""
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('CALENDLY_API_KEY')
headers = {'Authorization': f'Bearer {api_key}'}

# Get user and event type
user_resp = requests.get('https://api.calendly.com/users/me', headers=headers)
user_uri = user_resp.json()['resource']['uri']

events_resp = requests.get(
    'https://api.calendly.com/event_types',
    headers=headers,
    params={'user': user_uri, 'active': 'true'}
)
event_type = events_resp.json()['collection'][0]

# Try availability
start_time = datetime.now(timezone.utc) + timedelta(hours=1)
end_time = start_time + timedelta(days=7)

print('Checking availability...')
print(f"Event: {event_type['name']}")
print(f"Start: {start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')}")
print(f"End: {end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')}")

avail_resp = requests.get(
    'https://api.calendly.com/event_type_available_times',
    headers=headers,
    params={
        'event_type': event_type['uri'],
        'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'end_time': end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    }
)

print(f'Status: {avail_resp.status_code}')
print(f'Response: {avail_resp.json()}')
