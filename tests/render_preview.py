"""Render a standalone demo preview without changing the database."""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','anma_cloud.settings')
import django
django.setup()
from django.test import RequestFactory, override_settings
from django.template.loader import render_to_string
from dashboard.demo import history
request=RequestFactory().get('/app/')
request.user=SimpleNamespace(is_authenticated=False,email='')
plant=SimpleNamespace(pk=1,name='Дім · демо',model='Deye Hybrid')
series=history(plant)
telemetry=dict(online=True,demo=True,pv_power=3200,load_power=1200,battery_power=1000,battery_soc=64,grid_power=-1000,grid_available=True,grid_voltage=230,daily_pv=12,fault_code='0',updated_at='2026-10-17T12:00:00+03:00')
output=Path(__file__).resolve().parent
with override_settings(STORAGES={'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}}):
 html=render_to_string('dashboard.html',{'plant':plant,'plants':[plant],'history_json':json.dumps(series),'mode':'demo','live_available':True},request=request)
 html=html.replace('/api/plants/1/live/','/tests/telemetry.json').replace('/api/plants/1/history/','/tests/history.json')
 (output/'preview.html').write_text(html,encoding='utf-8')
 (output/'telemetry.json').write_text(json.dumps(telemetry),encoding='utf-8')
 (output/'history.json').write_text(json.dumps({'series':series}),encoding='utf-8')
 for template in ['landing.html','auth.html','settings.html','add_plant.html']:
  render_to_string(template,{},request=request)
 print('Dashboard, landing, auth, settings and add-site templates rendered; database unchanged.')
