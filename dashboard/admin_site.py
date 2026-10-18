from datetime import timedelta
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.template.response import TemplateResponse
from django.utils import timezone
from .models import Plant, HAConnection
from django.urls import path
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from .services.home_assistant import FIELDS, HAError
from .services.pairing import service_for

METRIC_LABELS = ['Сонячна генерація','Споживання будинку','Заряд батареї','Потужність батареї (+ заряд / − розряд)',
    'Потужність мережі (+ імпорт / − експорт)','Напруга мережі','Генерація за день','Споживання за день',
    'Імпорт за день','Експорт за день','Заряд батареї за день','Розряд батареї за день',
    'Прогноз на сьогодні','Прогноз на завтра','Мережа доступна','Помилка інвертора','Код помилки']


class OperationsAdminSite(AdminSite):
    site_header = 'ANMA Cloud · Операційний центр'
    site_title = 'ANMA Operations'

    def get_urls(self):
        return [path('users/<int:pk>/homes/', self.admin_view(self.user_homes), name='user_homes'),
                path('machines/<int:pk>/', self.admin_view(self.machine), name='machine'),
                path('machines/<int:pk>/data/', self.admin_view(self.machine_data), name='machine_data')] + super().get_urls()

    def _check_metrics_permission(self, request):
        if not request.user.has_perm('dashboard.view_plant'):
            raise PermissionDenied

    def user_homes(self, request, pk):
        self._check_metrics_permission(request)
        if not request.user.has_perm('auth.view_user'):
            raise PermissionDenied
        person = get_object_or_404(get_user_model(), pk=pk)
        return TemplateResponse(request, 'admin/user_homes.html', {**self.each_context(request),
            'title':'Машини користувача', 'person':person,
            'homes':Plant.objects.filter(owner=person).select_related('connection').order_by('name')})

    def machine(self, request, pk):
        self._check_metrics_permission(request)
        plant = get_object_or_404(Plant.objects.select_related('owner','connection'), pk=pk)
        return TemplateResponse(request, 'admin/machine.html', {**self.each_context(request),
            'title':plant.name, 'plant':plant, 'metrics':list(zip(FIELDS, METRIC_LABELS)),
            'homes':Plant.objects.filter(owner=plant.owner).order_by('name')})

    def machine_data(self, request, pk):
        self._check_metrics_permission(request)
        plant = get_object_or_404(Plant.objects.select_related('connection'), pk=pk)
        try:
            data = service_for(plant).snapshot()
        except HAError as exc:
            return JsonResponse({'online':False,'error':exc.code,'metrics':[]},status=503)
        return JsonResponse({'online':data.get('online',False), 'updated_at':data.get('updated_at'),
            'metrics':[{'key':key,'value':data.get(key),'unit':spec[1],
                        'source_updated_at':data.get('source_updated_at',{}).get(key)} for key,spec in FIELDS.items()]})

    def index(self, request, extra_context=None):
        context = {**self.each_context(request), 'title':'Операційний центр', 'app_list':self.get_app_list(request)}
        if request.user.has_perm('dashboard.view_plant'):
            homes = Plant.objects.select_related('owner','connection').order_by('-created_at')
            query = request.GET.get('q','').strip()[:100]
            if query:
                homes = homes.filter(Q(name__icontains=query)|Q(owner__email__icontains=query)|Q(tailscale_ip__icontains=query))
            connections = HAConnection.objects.all()
            context.update(homes=Paginator(homes,20).get_page(request.GET.get('page')),query=query,
                home_count=Plant.objects.count(),connection_count=connections.count(),
                recent_count=connections.filter(enabled=True,last_error='',last_seen__gte=timezone.now()-timedelta(minutes=5)).count(),
                attention_count=connections.filter(Q(enabled=False)|~Q(last_error='')).count())
        if request.user.has_perm('auth.view_user'):
            users = get_user_model().objects.annotate(home_count=Count('plants')).order_by('-date_joined')
            context.update(user_count=users.count(),recent_users=users[:8])
        context.update(extra_context or {})
        return TemplateResponse(request,'admin/operations.html',context)
