from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from .models import Plant,PlantAccess,HAConnection,TelemetrySample

@override_settings(STORAGES={'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class HomeManagementTests(TestCase):
 def setUp(self):
  self.owner=get_user_model().objects.create_user('owner')
  self.other=get_user_model().objects.create_user('shared')
  self.home=Plant.objects.create(owner=self.owner,name='Original')
  PlantAccess.objects.create(plant=self.home,user=self.other)
  self.edit=f'/app/homes/{self.home.pk}/edit/'
  self.delete=f'/app/homes/{self.home.pk}/delete/'
 def test_owner_rename_only_name(self):
  self.client.force_login(self.owner)
  self.assertEqual(self.client.post(self.edit,{'name':'Новий дім','owner':self.other.pk}).status_code,302)
  self.home.refresh_from_db();self.assertEqual(self.home.name,'Новий дім');self.assertEqual(self.home.owner,self.owner)
 def test_shared_user_cannot_manage(self):
  self.client.force_login(self.other)
  for url in [self.edit,self.delete]:self.assertEqual(self.client.post(url,{'name':'Changed','confirm':'delete'}).status_code,404)
  self.assertTrue(Plant.objects.filter(pk=self.home.pk).exists())
 def test_delete_requires_confirmation_and_cascades_local_records(self):
  connection=HAConnection.objects.create(plant=self.home,installation_id='a'*32,tailscale_ip='100.64.1.2',credential='test')
  TelemetrySample.objects.create(connection=connection)
  self.client.force_login(self.owner)
  self.assertEqual(self.client.get(self.delete).status_code,200)
  self.client.post(self.delete,{})
  self.assertTrue(Plant.objects.filter(pk=self.home.pk).exists())
  self.client.post(self.delete,{'confirm':'delete'})
  for model in [Plant,PlantAccess,HAConnection,TelemetrySample]:self.assertFalse(model.objects.exists())
 def test_menu_admin_only_and_demo_preserved(self):
  self.client.force_login(self.owner)
  response=self.client.get(f'/app/?plant={self.home.pk}&mode=demo')
  self.assertContains(response,'mobile-menu');self.assertContains(response,'value="demo"')
  self.assertNotContains(response,'Операційний центр')
