import os, requests
from dotenv import load_dotenv

load_dotenv()
sid = os.getenv('TWILIO_ACCOUNT_SID')
token = os.getenv('TWILIO_AUTH_TOKEN')
print('--- ALERTS ---')
res2 = requests.get('https://monitor.twilio.com/v1/Alerts?PageSize=15', auth=(sid, token))
if res2.status_code == 200:
    for a in res2.json().get('alerts', []):
        print(a.get('date_created'), 'Error', a.get('error_code'), ':', a.get('alert_text'))
else:
    print('Failed', res2.status_code, res2.text)
