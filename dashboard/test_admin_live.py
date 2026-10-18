from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Plant
from .services.home_assistant import HAError


@override_settings(STORAGES={'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AdminLiveTests(TestCase):
    def setUp(self):
        self.owner=get_user_model().objects.create_user('owner',email='owner@example.test')
        self.admin=get_user_model().objects.create_superuser('administrator','admin@example.test','test-password')
        self.home=Plant.objects.create(owner=self.owner,name='Будинок замовника')
        self.page=reverse('admin:machine',args=[self.home.pk])
        self.api=reverse('admin:machine_data',args=[self.home.pk])

    def test_normal_user_and_anonymous_cannot_read_admin_data(self):
        self.assertEqual(self.client.get(self.api).status_code,302)
        self.client.force_login(self.owner)
        with patch('dashboard.admin_site.service_for') as service:
            self.assertEqual(self.client.get(self.api).status_code,302)
            service.assert_not_called()

    def test_staff_without_permission_is_denied(self):
        self.owner.is_staff=True;self.owner.save();self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.api).status_code,403)

    def test_admin_navigation_and_selected_service(self):
        self.client.force_login(self.admin)
        response=self.client.get(reverse('admin:user_homes',args=[self.owner.pk]))
        self.assertContains(response,self.page)
        self.assertContains(self.client.get(self.page),'Поточні параметри')
        with patch('dashboard.admin_site.service_for') as service:
            service.return_value.snapshot.return_value={'online':True,'pv_power':1250,'battery_soc':60,'updated_at':'now','secret':'must-not-leak'}
            response=self.client.get(self.api)
        self.assertEqual(service.call_args.args[0].pk,self.home.pk)
        values={row['key']:row['value'] for row in response.json()['metrics']}
        self.assertEqual(values['pv_power'],1250);self.assertIsNone(values['load_power'])
        self.assertNotContains(response,'must-not-leak')
        self.assertIn('no-store',response['Cache-Control'])

    def test_no_demo_fallback_on_connection_error(self):
        self.client.force_login(self.admin)
        with patch('dashboard.admin_site.service_for',side_effect=HAError('live_not_bound')):
            response=self.client.get(self.api)
        self.assertEqual(response.status_code,503);self.assertFalse(response.json()['online'])
        self.assertEqual(response.json()['metrics'],[])

    def test_admin_does_not_change_customer_visibility(self):
        self.client.force_login(self.owner)
        other=get_user_model().objects.create_user('other')
        hidden=Plant.objects.create(owner=other,name='Private')
        self.assertEqual(self.client.get(f'/api/plants/{hidden.pk}/live/').status_code,404)
