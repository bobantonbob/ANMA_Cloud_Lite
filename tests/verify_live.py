"""Verify the configured local object without changing users or object records."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','anma_cloud.settings')
import django
django.setup()
from django.conf import settings
from django.test import Client, override_settings
from django.contrib.sessions.models import Session
from dashboard.models import Plant
from dashboard.services.home_assistant import HomeAssistant
root=Path(__file__).resolve().parents[1]
auth_file=root/'.backups/live-integration/browser-auth.json'
if '--cleanup' in sys.argv:
 if auth_file.exists():
  data=json.loads(auth_file.read_text());Session.objects.filter(session_key=data['value']).delete();auth_file.unlink()
 print('Temporary browser test session removed.')
 sys.exit()
plant=Plant.objects.get(pk=settings.HA_PLANT_ID)
client=Client()
client.force_login(plant.owner)
with override_settings(ALLOWED_HOSTS=['testserver','127.0.0.1','localhost']):
 for path in [f'/app/?plant={plant.pk}&mode=live',f'/api/plants/{plant.pk}/live/?mode=live',f'/api/plants/{plant.pk}/history/?mode=live']:
  response=client.get(path)
  assert response.status_code==200,(path,response.status_code)
  assert settings.HA_TOKEN.encode() not in response.content
  print('PASS HTTP 200, no token in response:',path)
ha=HomeAssistant();states=ha.states();current=ha.snapshot();history=ha.history()
report={'entity_count':len(ha.discover(states)),'entities':ha.discover(states),'mapping':ha.mapping(states),'current':current,
        'history_points':len(history['series']),'history_missing':history['missing'],
        'first_recorded_point':next((row['timestamp'] for row in history['series'] if row['load'] is not None),None)}
(root/'tests/live-diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
auth_file.write_text(json.dumps({'name':settings.SESSION_COOKIE_NAME,'value':client.cookies[settings.SESSION_COOKIE_NAME].value,'plant':plant.pk}),encoding='utf-8')
print('Live diagnostics saved. Temporary browser session prepared locally; credentials not printed.')
