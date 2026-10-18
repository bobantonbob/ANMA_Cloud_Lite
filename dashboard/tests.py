"""Focused regression coverage; uses an isolated test database and mocked HA."""
import json
from datetime import timedelta
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from .models import Plant
from .services.home_assistant import HomeAssistant, HAError, normalize

CONFIG = dict(HA_URL='http://100.114.0.63:8123', HA_TOKEN='test-only-secret', HA_PLANT_ID=1,
              HA_GRID_SIGN=1, HA_BATTERY_SIGN=-1, HA_ENTITY_MAPPING='{}')


def state(eid, value, unit=None, stamp=None):
    return {'entity_id':eid,'state':value,'attributes':{'unit_of_measurement':unit},
            'last_updated':(stamp or timezone.now()).isoformat()}


class NormalizeTests(SimpleTestCase):
    def test_units_and_signs(self):
        self.assertEqual(normalize(state('x','2.5','kW'),'pv_power'),2500)
        self.assertEqual(normalize(state('x','800','W'),'battery_power',-1),-800)
        self.assertEqual(normalize(state('x','3200','Wh'),'daily_pv'),3.2)
        self.assertEqual(normalize(state('x','0','%'),'battery_soc'),0)
        self.assertIs(normalize(state('x','off'),'grid_available'),False)

    def test_missing_never_becomes_zero(self):
        for value in [None,'','unavailable','unknown','nan','Infinity',True]:
            self.assertIsNone(normalize(state('x',value,'W'),'pv_power'))
        self.assertIsNone(normalize(state('x','12',None),'pv_power'))
        self.assertIsNone(normalize(state('x','120','%'),'battery_soc'))


@override_settings(**CONFIG)
class AdapterTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.ha=HomeAssistant()

    def test_discovered_mapping_and_missing(self):
        states={'sensor.anma_cloud_pv_power':state('sensor.anma_cloud_pv_power','1.5','kW')}
        with patch.object(self.ha,'states',return_value=states):
            result=self.ha.snapshot()
        self.assertEqual(result['pv_power'],1500)
        self.assertIsNone(result['load_power'])
        self.assertIn('load_power',result['missing'])
        self.assertNotIn(CONFIG['HA_TOKEN'],json.dumps(result))
        offline=self.ha.offline('connection_failed')
        self.assertEqual(offline['updated_at'],result['updated_at'])
        self.assertIsNone(offline['pv_power'])
        self.assertFalse(offline['online'])

    @override_settings(HA_ENTITY_MAPPING='{"pv_power":"sensor.custom_pv"}')
    def test_explicit_mapping(self):
        self.assertEqual(HomeAssistant().mapping({})['pv_power'],'sensor.custom_pv')

    def test_authentication_no_retry_or_secret(self):
        opener=MagicMock();opener.open.side_effect=HTTPError('secret-url',401,'secret-message',{},None)
        with patch('dashboard.services.home_assistant.build_opener',return_value=opener):
            with self.assertRaises(HAError) as error:self.ha.authenticate()
        self.assertEqual(str(error.exception),'authentication_failed')
        self.assertEqual(opener.open.call_count,1)

    def test_timeout_retries_once(self):
        opener=MagicMock();opener.open.side_effect=URLError('private detail')
        with patch('dashboard.services.home_assistant.build_opener',return_value=opener),patch('dashboard.services.home_assistant.time.sleep'):
            with self.assertRaises(HAError):self.ha.states()
        self.assertEqual(opener.open.call_count,2)

    def test_history_timestamp_alignment_gaps_and_units(self):
        now=timezone.now();a=now-timedelta(hours=2);b=now-timedelta(hours=1)
        eid='sensor.anma_cloud_battery_power'
        states={eid:state(eid,'1000','W')}
        history=[[state(eid,'1','kW',a),{'state':'unavailable','last_changed':b.isoformat()}]]
        with patch.object(self.ha,'states',return_value=states),patch.object(self.ha,'request',return_value=history) as request:
            result=self.ha.history()
        self.assertEqual(request.call_args.args[1]['filter_entity_id'],eid)
        series=result['series']
        self.assertIsNone(series[0]['battery'])
        self.assertEqual(next(x for x in series if x['timestamp']==a.isoformat())['battery'],-1000)
        self.assertIsNone(series[-1]['battery'])
        self.assertTrue(all(x['pv'] is None for x in series))
        self.assertTrue(result['available'])

    def test_history_empty_is_not_demo(self):
        with patch.object(self.ha,'states',return_value={}):result=self.ha.history()
        self.assertFalse(result['available']);self.assertFalse(result['demo'])
        self.assertTrue(all(row['pv'] is None for row in result['series']))


@override_settings(**CONFIG, STORAGES={'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class EndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner=get_user_model().objects.create_user('owner',password='test-password-only')
        self.other=get_user_model().objects.create_user('other',password='test-password-only')
        self.plant=Plant.objects.create(pk=1,owner=self.owner,name='Home')
        self.unbound=Plant.objects.create(pk=2,owner=self.owner,name='Other site')

    def test_auth_and_ownership(self):
        self.assertEqual(self.client.get('/api/plants/1/live/?mode=live').status_code,302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/api/plants/1/live/?mode=live').status_code,404)
        self.assertEqual(self.client.get('/api/plants/1/history/?mode=live').status_code,404)

    def test_only_bound_site_can_use_token(self):
        self.client.force_login(self.owner)
        with patch('dashboard.views.HomeAssistant') as service:
            self.assertEqual(self.client.get('/api/plants/2/live/?mode=live').status_code,403)
            service.assert_not_called()

    def test_live_failure_is_not_simulated(self):
        self.client.force_login(self.owner)
        with patch('dashboard.services.home_assistant.HomeAssistant.snapshot',side_effect=HAError('connection_failed')):
            response=self.client.get('/api/plants/1/live/?mode=live')
        self.assertEqual(response.status_code,503)
        self.assertFalse(response.json()['demo']);self.assertIsNone(response.json()['pv_power'])

    def test_demo_is_explicit_and_offline_independent(self):
        self.client.force_login(self.owner)
        with patch('dashboard.views.HomeAssistant') as service:
            data=self.client.get('/api/plants/1/live/?mode=demo').json()
            service.assert_not_called()
        self.assertTrue(data['demo']);self.assertTrue(data['online'])

    def test_live_template_and_history(self):
        self.client.force_login(self.owner)
        response=self.client.get('/app/?plant=1&mode=live')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"mode:'live'")
        self.assertNotContains(response,CONFIG['HA_TOKEN'])
        self.assertContains(response,'history:[]')
        self.assertContains(response,'battery-summary-line')
        self.assertContains(response,'id="batteryDirectionMark"')
        self.assertEqual(response.content.count(b'id="batteryPower"'),1)
        with patch('dashboard.services.home_assistant.HomeAssistant.history',return_value={'series':[],'available':False,'demo':False}):
            response=self.client.get('/api/plants/1/history/?mode=live')
        self.assertEqual(response.status_code,200);self.assertFalse(response.json()['demo'])

    def test_invalid_mode_rejected(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/api/plants/1/live/?mode=oops').status_code,400)
