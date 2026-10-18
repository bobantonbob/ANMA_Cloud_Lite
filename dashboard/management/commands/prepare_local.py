"""Generate missing local secrets without printing them; backup DB before migration."""
import sqlite3
from datetime import datetime
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Prepare local encryption and back up SQLite without exposing secrets.'

    def handle(self, *args, **options):
        env = settings.BASE_DIR / '.env'
        content = env.read_text(encoding='utf-8-sig') if env.exists() else ''
        if not settings.ANMA_CONNECTION_KEY:
            lines = [line for line in content.splitlines() if not line.startswith('ANMA_CONNECTION_KEY=')]
            lines.append('ANMA_CONNECTION_KEY=' + Fernet.generate_key().decode())
            content = '\n'.join(lines) + '\n'
        for key in ('GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET'):
            if not any(line.startswith(key+'=') for line in content.splitlines()):
                content += key+'=\n'
        env.write_text(content, encoding='utf-8')
        db = settings.DATABASES['default']['NAME']
        backup = settings.BASE_DIR / '.backups' / ('before-pairing-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
        backup.parent.mkdir(exist_ok=True)
        with sqlite3.connect(db) as source, sqlite3.connect(backup) as target:
            source.backup(target)
        self.stdout.write('Local secret settings prepared; SQLite backup created. No secrets printed.')
