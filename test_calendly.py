"""Test Calendly API connection and show available appointments."""
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

def main():
    api_key = os.getenv('CALENDLY_API_KEY')
    if not api_key:
        print("❌ CALENDLY_API_KEY not set in .env")
        return
    
    headers = {'Authorization': f'Bearer {api_key}'}
    
    # Get user
    print("🔗 Connecting to Calendly...")
    user_resp = requests.get('https://api.calendly.com/users/me', headers=headers)
    if user_resp.status_code != 200:
        print(f'❌ Calendly API Error: {user_resp.status_code}')
        print(user_resp.text)
        return
    
    user_data = user_resp.json()['resource']
    user_uri = user_data['uri']
    print(f'✅ Connected as: {user_data.get("name", "Unknown")}')
    print(f'   Email: {user_data.get("email", "N/A")}')
    print()
    
    # Get event types
    print("📅 Available Appointment Types:")
    events_resp = requests.get(
        'https://api.calendly.com/event_types',
        headers=headers,
        params={'user': user_uri, 'active': 'true'}
    )
    
    event_types = events_resp.json().get('collection', [])
    if not event_types:
        print("   No active event types found.")
        print("   Please create an event type in Calendly dashboard.")
        return
    
    for et in event_types:
        print(f'   • {et["name"]} ({et["duration"]} min)')
        print(f'     URL: {et["scheduling_url"]}')
    
    # Get available times for first event type
    print()
    print("🕐 Available Times (Next 7 Days):")
    
    event_type = event_types[0]
    # Start from tomorrow to ensure future time
    start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    end_time = start_time + timedelta(days=7)
    
    avail_resp = requests.get(
        'https://api.calendly.com/event_type_available_times',
        headers=headers,
        params={
            'event_type': event_type['uri'],
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'end_time': end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        }
    )
    
    if avail_resp.status_code != 200:
        print(f'   ❌ Error fetching availability: {avail_resp.status_code}')
        print(f'   {avail_resp.text}')
        return
    
    available = avail_resp.json().get('collection', [])
    
    if not available:
        print("   No available times in the next 7 days.")
        print("   Check your Calendly availability settings.")
        return
    
    # Group by day
    by_day = {}
    for slot in available[:20]:  # Limit to 20 slots
        dt = datetime.fromisoformat(slot['start_time'].replace('Z', '+00:00'))
        day = dt.strftime('%A, %B %d')
        time_str = dt.strftime('%I:%M %p')
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(time_str)
    
    for day, times in by_day.items():
        print(f'   {day}:')
        print(f'      {", ".join(times[:5])}')
    
    print()
    print("✅ Calendly is ready for Danny to book appointments!")


if __name__ == "__main__":
    main()
