from django.contrib import admin
from django.urls import path,include
from django.views.generic import RedirectView
urlpatterns=[path('admin/',admin.site.urls),path('accounts/',include('allauth.urls')),path('',include('dashboard.urls'))]
admin.site.site_header='ANMA Cloud | Administration'
admin.site.site_title='ANMA Cloud Admin'
admin.site.index_title='Operations · Devices · Access'
