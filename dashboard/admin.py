from django.contrib import admin
from .models import Plant,EntityMapping,PlantAccess,HAConnection,PairingAttempt
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
class EntityInline(admin.TabularInline):
 model=EntityMapping;extra=0
class AccessInline(admin.TabularInline):
 model=PlantAccess;extra=0
@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
 list_display=['name','model','owner','tailscale_ip','demo','created_at']
 list_filter=['demo','model'];search_fields=['name','owner__email','tailscale_ip'];inlines=[EntityInline,AccessInline]

@admin.register(HAConnection)
class ConnectionAdmin(admin.ModelAdmin):
 list_display=['plant','tailscale_ip','enabled','paired_at','last_seen','last_error']
 list_filter=['enabled'];search_fields=['plant__name','plant__owner__email','tailscale_ip']
 fields=['plant','installation_id','tailscale_ip','enabled','paired_at','last_seen','last_error']
 readonly_fields=['plant','installation_id','tailscale_ip','paired_at','last_seen','last_error']
 def has_add_permission(self,request):return False
 def has_delete_permission(self,request,obj=None):return False

class OwnedPlantInline(admin.TabularInline):
 model=Plant;extra=0;fields=['name','tailscale_ip','created_at','live_parameters'];readonly_fields=fields;show_change_link=True
 can_delete=False
 def has_add_permission(self,request,obj=None):return False
 @admin.display(description='Поточні дані')
 def live_parameters(self,obj):
  return format_html('<a href="{}">Поточні параметри →</a>',reverse('admin:machine',args=[obj.pk]))

admin.site.unregister(get_user_model())
@admin.register(get_user_model())
class ANMAUserAdmin(UserAdmin):
 list_display=['email','username','is_active','is_staff','date_joined','last_login','machines']
 inlines=[OwnedPlantInline]
 @admin.display(description='Машини')
 def machines(self,obj):
  return format_html('<a href="{}">Машини та параметри →</a>',reverse('admin:user_homes',args=[obj.pk]))
@admin.register(EntityMapping)
class EntityAdmin(admin.ModelAdmin):
 list_display=['plant','field','entity_id'];search_fields=['field','entity_id']
@admin.register(PlantAccess)
class AccessAdmin(admin.ModelAdmin):
 list_display=['user','plant','can_control']
