from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig

class ANMAAdminConfig(AdminConfig):
 default_site='dashboard.admin_site.OperationsAdminSite'
class DashboardConfig(AppConfig):
 default_auto_field='django.db.models.BigAutoField'
 name='dashboard'
 verbose_name='ANMA Cloud'
