from django.db import models
from django.conf import settings
from django.utils import timezone
class Plant(models.Model):
 owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='plants')
 name=models.CharField(max_length=100)
 model=models.CharField(max_length=120,default='Deye Hybrid 12 kW')
 tailscale_ip=models.GenericIPAddressField(protocol='IPv4',null=True,blank=True,help_text='IP must be reachable by server; do not trust an address as authentication')
 demo=models.BooleanField(default=True)
 created_at=models.DateTimeField(auto_now_add=True)
 def __str__(self):return self.name
class EntityMapping(models.Model):
 plant=models.ForeignKey(Plant,on_delete=models.CASCADE,related_name='mappings')
 field=models.CharField(max_length=60)
 entity_id=models.CharField(max_length=180)
 class Meta:
  unique_together=[('plant','field')]
 def __str__(self):return f'{self.plant}: {self.field}'
class PlantAccess(models.Model):
 user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 plant=models.ForeignKey(Plant,on_delete=models.CASCADE,related_name='accesses')
 can_control=models.BooleanField(default=False)
 class Meta:
  unique_together=[('user','plant')]

class HAConnection(models.Model):
 plant=models.OneToOneField(Plant,on_delete=models.CASCADE,related_name='connection')
 installation_id=models.CharField(max_length=64,unique=True)
 tailscale_ip=models.GenericIPAddressField(protocol='IPv4',unique=True)
 credential=models.TextField(editable=False)
 enabled=models.BooleanField(default=True)
 paired_at=models.DateTimeField(auto_now_add=True)
 last_seen=models.DateTimeField(null=True,blank=True)
 last_error=models.CharField(max_length=60,blank=True)
 def __str__(self):return f'{self.plant.name} · {self.tailscale_ip}'

class PairingAttempt(models.Model):
 user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
 created_at=models.DateTimeField(auto_now_add=True,db_index=True)
 result=models.CharField(max_length=32,default='started')

class TelemetrySample(models.Model):
 connection=models.ForeignKey(HAConnection,on_delete=models.CASCADE,related_name='samples')
 created_at=models.DateTimeField(default=timezone.now)
 payload=models.JSONField(default=dict)
 class Meta:
  indexes=[models.Index(fields=['connection','created_at'])]
