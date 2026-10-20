import hashlib
from django.test import TestCase
from django.urls import reverse


class AndroidDownloadTests(TestCase):
    def test_public_signed_preview_download(self):
        response = self.client.get(reverse('android_download'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.android.package-archive')
        self.assertIn('attachment;', response['Content-Disposition'])
        body = b''.join(response.streaming_content)
        self.assertEqual(hashlib.sha256(body).hexdigest(),
                         '7d39c55905c3284925f03fac58dc33b8ab7c1164193f2d6aec7d3a72bc90cbff')

    def test_download_is_read_only(self):
        self.assertEqual(self.client.post(reverse('android_download')).status_code, 405)
