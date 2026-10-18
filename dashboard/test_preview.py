"""Optional UI fixtures from an isolated test database, never real customer records."""
import os
from pathlib import Path
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from .models import Plant, HAConnection


@override_settings(STORAGES={'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PreviewTests(TestCase):
    def test_responsive_pages_render(self):
        user=get_user_model().objects.create_superuser('preview-admin','owner@example.test','test-only-password')
        home=Plant.objects.create(owner=user,name='Будинок біля озера',demo=False,model='Home Assistant · ANMA')
        HAConnection.objects.create(plant=home,installation_id='a'*32,tailscale_ip='100.64.10.20',credential='preview-not-a-key')
        target=os.getenv('ANMA_PREVIEW_DIR')
        pages={'login':'/login/','homes':'/app/homes/','connect':'/app/add/','operations':'/admin/'}
        for name,url in pages.items():
            if name!='login':self.client.force_login(user)
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            if target:
                folder=Path(target);folder.mkdir(parents=True,exist_ok=True)
                html=response.content.decode().replace('"/static/','"http://127.0.0.1:8095/static/')
                (folder/(name+'.html')).write_text(html,encoding='utf-8')
