from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dashboard.models import Plant
class Command(BaseCommand):
 help='Create local demo login and demo plants (do not run on production)'
 def handle(self,*args,**kwargs):
  import os
  User=get_user_model()
  email=os.environ.get('ANMA_DEMO_EMAIL','demo@anma.local')
  password=os.environ.get('ANMA_DEMO_PASSWORD','DemoChangeMe2026!')
  user,created=User.objects.get_or_create(username=email,defaults={'email':email})
  if created:user.set_password(password);user.save()
  for name,model in [('Мій будинок','Deye Hybrid 12 kW'),('Дача','Deye Hybrid 6 kW'),('Майстерня','MUST 10 kW')]:Plant.objects.get_or_create(owner=user,name=name,defaults={'model':model,'demo':True})
  self.stdout.write(self.style.SUCCESS(f'Demo user: {email} (password configured at first creation)'))
