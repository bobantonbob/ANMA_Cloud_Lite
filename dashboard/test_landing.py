from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


@override_settings(STORAGES={'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class LandingTests(TestCase):
    def test_guest_has_no_fake_avatar_or_account_badge(self):
        response=self.client.get('/')
        self.assertContains(response,'data-i18n="guest"')
        self.assertNotContains(response,'class="avatar"')
        self.assertIn('no-store',response.headers['Cache-Control'])

    def test_authenticated_visitors_redirect_and_can_logout(self):
        user=get_user_model().objects.create_user('signed-in',email='signed@example.test')
        self.client.force_login(user)
        for path in ('/','/login/','/register/'):
            response=self.client.get(path,follow=True)
            self.assertEqual(response.request['PATH_INFO'],'/app/')
            self.assertContains(response,'action="/logout/"')
            self.assertNotContains(response,'data-i18n="getStarted"')
        self.client.post('/logout/')
        self.assertContains(self.client.get('/'),'data-i18n="guest"')

    def test_public_counter_contains_active_registered_users_only(self):
        users = get_user_model()
        users.objects.create_user('active-one', email='one@example.test')
        users.objects.create_user('active-two', email='two@example.test')
        users.objects.create_user('inactive', email='off@example.test', is_active=False)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['registered_user_count'], 2)
        self.assertContains(response, 'активних користувачів ANMA Cloud', html=False)
        self.assertContains(response, 'data-i18n="heroSolar"')
