import os, requests
from dotenv import load_dotenv

load_dotenv()
sid = os.getenv('TWILIO_ACCOUNT_SID')
token = os.getenv('TWILIO_AUTH_TOKEN')
print('--- CALLS ---')
res2 = requests.get(f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json?PageSize=10', auth=(sid, token))
if res2.status_code == 200:
    for c in res2.json().get('calls', []):
        d = c.get('start_time')
        t = c.get('to')
        s = c.get('status')
        dur = c.get('duration')
        print(d, t, s, dur, 'sec')
else:
    print('Failed', res2.status_code, res2.text)
