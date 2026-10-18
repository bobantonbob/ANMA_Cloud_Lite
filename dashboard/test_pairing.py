import hashlib
import hmac
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import timedelta
from cryptography.fernet import Fernet
from django.test import TestCase, SimpleTestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.core.exceptions import ImmediateHttpResponse
from .auth import GoogleOnlyAdapter
from .models import Plant, HAConnection, PairingAttempt
from .services.home_assistant import HAError
from .services.pairing import pair_plant, cipher, validate_address, PairedHomeAssistant, connector_request

TEST_KEY = Fernet.generate_key().decode()
TEST_SETTINGS = dict(ANMA_CONNECTION_KEY=TEST_KEY, ANMA_ALLOWED_TAILSCALE_IPS=[],
    STORAGES={'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})


class AddressTests(SimpleTestCase):
    def test_rejects_ssrf_and_accepts_only_tailnet(self):
        for address in ['127.0.0.1','169.254.169.254','192.168.1.1','8.8.8.8','::1','100.64.1.2:8123','http://100.64.1.2','100.128.0.1']:
            with self.subTest(address=address), self.assertRaises(HAError):validate_address(address)
        self.assertEqual(validate_address('100.64.1.2'),'100.64.1.2')

    @override_settings(ANMA_ALLOWED_TAILSCALE_IPS=['100.64.1.2'])
    def test_allowlist(self):
        with self.assertRaises(HAError):validate_address('100.64.1.3')


@override_settings(**TEST_SETTINGS)
class PairingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user=get_user_model().objects.create_user('new-google',email='owner@example.test')
        self.other=get_user_model().objects.create_user('other-google',email='other@example.test')
        self.code='A'*32
        self.installation='a'*32
        self.calls=[]

    def remote(self, address, action, body=None, token=None):
        self.calls.append((address,action,body,token))
        if action in ('verify','pair'):
            material=f"{body['nonce']}\n{body['timestamp']}\n{body['credential_hash']}"
            expected=hmac.new(self.code.encode(),material.encode(),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected,body['proof']):raise HAError('invalid_or_expired_code')
            return {'protocol':1,'installation_id':self.installation,'paired':action=='pair'}
        if action == 'history':
            return {'installation_id':self.installation,'history':[[{'entity_id':'sensor.anma_battery_power','state':'100','attributes':{'unit_of_measurement':'W'},'last_updated':(timezone.now()-timedelta(hours=25)).isoformat()}]]}
        return {'installation_id':self.installation,'states':[
            {'entity_id':'sensor.anma_battery_power','state':'100','attributes':{'unit_of_measurement':'W'}}]}

    def pair(self,address='100.64.1.2'):
        with patch('dashboard.services.pairing.connector_request',side_effect=self.remote):
            return pair_plant(self.user,'Дім',address,self.code)

    def test_encrypted_and_scoped(self):
        home=self.pair(); connection=home.connection
        self.assertFalse(home.demo);self.assertEqual(home.owner,self.user)
        token=cipher().decrypt(connection.credential.encode()).decode()
        self.assertNotIn(token,connection.credential)
        self.assertNotIn(self.code,connection.credential)
        self.assertEqual(hashlib.sha256(token.encode()).hexdigest(),self.calls[-1][2]['credential_hash'])

    def test_multiple_homes_and_ownership(self):
        first=self.pair();self.installation='b'*32;second=self.pair('100.64.1.3')
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/app/homes/'),'100.64.1.2')
        self.assertContains(self.client.get('/app/homes/'),'100.64.1.3')
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/app/homes/'),'100.64.1.2')
        self.assertEqual(self.client.get(f'/api/plants/{first.pk}/live/').status_code,404)
        self.assertEqual(self.client.get(f'/api/plants/{second.pk}/history/').status_code,404)

    def test_wrong_code_no_creation(self):
        with patch('dashboard.services.pairing.connector_request',side_effect=self.remote),self.assertRaises(HAError):
            pair_plant(self.user,'Дім','100.64.1.2','B'*32)
        self.assertFalse(Plant.objects.exists());self.assertFalse(HAConnection.objects.exists())

    def test_repair_preserves_home_and_other_owner_cannot_claim(self):
        first=self.pair();old=first.connection.credential
        repaired=self.pair();self.assertEqual(first.pk,repaired.pk)
        self.assertNotEqual(old,repaired.connection.credential)
        with patch('dashboard.services.pairing.connector_request',side_effect=self.remote),self.assertRaises(HAError):
            pair_plant(self.other,'Claim','100.64.1.2',self.code)
        self.assertEqual(Plant.objects.count(),1)
        self.assertEqual(self.calls[-1][1],'verify')

    def test_failure_after_verify_rolls_back(self):
        def fail(address,action,body):
            if action=='pair':raise HAError('connection_failed')
            return self.remote(address,action,body)
        with patch('dashboard.services.pairing.connector_request',side_effect=fail),self.assertRaises(HAError):
            pair_plant(self.user,'Дім','100.64.1.2',self.code)
        self.assertFalse(Plant.objects.exists());self.assertFalse(HAConnection.objects.exists())

    @override_settings(HA_BATTERY_SIGN=-1)
    def test_live_does_not_double_invert_and_history_comes_from_ha(self):
        home=self.pair()
        with patch('dashboard.services.pairing.connector_request',side_effect=self.remote):
            service=PairedHomeAssistant(home.connection)
            self.assertEqual(service.snapshot()['battery_power'],100)
            self.assertEqual(service.history()['series'][0]['battery'],100)
        home.connection.refresh_from_db();self.assertIsNotNone(home.connection.last_seen)

    def test_rate_limit(self):
        PairingAttempt.objects.bulk_create([PairingAttempt(user=self.user) for _ in range(10)])
        with patch('dashboard.services.pairing.connector_request') as network,self.assertRaises(HAError):
            pair_plant(self.user,'Дім','100.64.1.2',self.code)
        network.assert_not_called()

    def test_form_error_and_disabled(self):
        self.client.force_login(self.user)
        with patch('dashboard.views.pair_plant',side_effect=HAError('connection_failed')):
            response=self.client.post('/app/add/',{'name':'Дім','tailscale_ip':'100.64.1.2','pairing_code':self.code})
        self.assertContains(response,'Машина недоступна');self.assertNotContains(response,self.code)
        home=self.pair();home.connection.enabled=False;home.connection.save()
        self.assertEqual(self.client.get(f'/api/plants/{home.pk}/live/').status_code,403)

    def test_admin_permissions_and_no_credentials(self):
        self.pair();self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/').status_code,302)
        self.user.is_staff=True;self.user.is_superuser=True;self.user.save()
        response=self.client.get('/admin/')
        self.assertContains(response,'Будинки та машини');self.assertContains(response,self.user.email)
        self.assertNotContains(response,HAConnection.objects.first().credential)
        self.assertEqual(self.client.get('/admin/?q=missing').status_code,200)

    def test_download_contains_component_not_secrets(self):
        from io import BytesIO
        from zipfile import ZipFile
        self.client.force_login(self.user)
        response=self.client.get('/app/integration/download/')
        self.assertEqual(response.status_code,200)
        with ZipFile(BytesIO(b''.join(response.streaming_content))) as archive:
            self.assertIn('custom_components/anma_cloud/pairing.py',archive.namelist())
            self.assertNotIn('.env',archive.namelist())
            self.assertIsNone(archive.testzip())


@override_settings(**TEST_SETTINGS)
class GoogleTests(TestCase):
    def test_public_password_signup_available(self):
        self.assertContains(self.client.get('/login/'), 'name="password"')
        self.assertContains(self.client.get('/register/'), 'name="password1"')
        self.assertEqual(self.client.get('/accounts/signup/').status_code, 200)

    @override_settings(GOOGLE_CLIENT_ID='client',GOOGLE_CLIENT_SECRET='secret')
    def test_google_button(self):
        self.assertContains(self.client.get('/login/'),'Продовжити з Google')

    def test_google_verification_policy(self):
        adapter=GoogleOnlyAdapter()
        verified=SocialLogin(account=SocialAccount(provider='google'),email_addresses=[EmailAddress(email='a@example.test',verified=True)])
        self.assertTrue(adapter.is_open_for_signup(None,verified))
        verified.email_addresses[0].verified=False
        self.assertFalse(adapter.is_open_for_signup(None,verified))
