from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.views.generic import RedirectView
urlpatterns_android = [path('downloads/android/', views.android_download, name='android_download')]
urlpatterns=[path('',views.landing,name='landing'),path('register/',views.register,name='register'),path('login/',auth_views.LoginView.as_view(template_name='auth.html'),name='login'),path('logout/',auth_views.LogoutView.as_view(),name='logout'),path('app/',views.dashboard,name='dashboard'),path('app/add/',views.add_plant,name='add_plant'),path('app/settings/',views.settings_page,name='settings'),path('api/plants/<int:pk>/live/',views.live,name='live'),path('api/plants/<int:pk>/history/',views.chart,name='history')]
urlpatterns[2]=path('login/',views.login_page,name='login')
urlpatterns += [path('app/homes/',views.plants_page,name='plants')]
urlpatterns += [path('app/integration/download/',views.integration_download,name='integration_download')]
urlpatterns += [path('app/homes/<int:pk>/edit/',views.edit_plant,name='edit_plant'),path('app/homes/<int:pk>/delete/',views.delete_plant,name='delete_plant')]

urlpatterns += [path('app/demo/',views.demo_dashboard,name='demo_dashboard')]
urlpatterns += urlpatterns_android
