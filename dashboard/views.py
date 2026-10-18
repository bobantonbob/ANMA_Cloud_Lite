import json
from django.contrib import messages
from django.conf import settings
from django.views.decorators.cache import never_cache
from .services.home_assistant import HomeAssistant, HAError, FIELDS
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse,Http404
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_GET,require_POST
from django.views.decorators.debug import sensitive_post_parameters
from .forms import RegisterForm,PlantForm,PlantRenameForm
from .models import Plant,PlantAccess
from .demo import snapshot,history
from .services.pairing import pair_plant, service_for
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from django.http import FileResponse
from django.contrib.auth import get_user_model

@never_cache
def landing(request):
 if request.user.is_authenticated:return redirect('dashboard')
 user_count=get_user_model().objects.filter(is_active=True).count()
 return render(request,'landing.html',{'registered_user_count':user_count})
def register(request):
 if request.user.is_authenticated:return redirect('dashboard')
 from allauth.account.views import SignupView
 return SignupView.as_view()(request)

@never_cache
def login_page(request):
 if request.user.is_authenticated:return redirect('dashboard')
 from allauth.account.views import LoginView
 return LoginView.as_view()(request)
def accessible(user):return Plant.objects.filter(Q(owner=user)|Q(accesses__user=user)).select_related('connection').distinct()
def mode_for(request, plant):
 # A server-configured installation is bound to one object, never every account.
 requested = request.GET.get('mode')
 if requested not in (None, 'live', 'demo'):
  return None
 if requested:
  return requested
 return 'live' if plant.pk == settings.HA_PLANT_ID else 'demo' if plant.demo else 'live'


def live_allowed(plant):
 return (plant.connection.enabled if hasattr(plant,'connection') else plant.pk == settings.HA_PLANT_ID and settings.HA_PLANT_ID > 0)


@login_required
@never_cache
def dashboard(request):
 plants=accessible(request.user)
 active_id=request.GET.get('plant')
 selected=plants.filter(pk=active_id).first() if str(active_id or '').isdigit() else plants.filter(pk=settings.HA_PLANT_ID).first() or plants.first()
 mode=mode_for(request,selected) if selected else 'demo'
 if mode is None:
  return JsonResponse({'error':'invalid_mode'},status=400)
 return render(request,'dashboard.html',{'plants':plants,'plant':selected,
  'mode':mode,'live_available':bool(selected and live_allowed(selected)),
  'history_json':json.dumps(history(selected)) if selected and mode=='demo' else '[]'})


@login_required
@never_cache
@require_GET
def live(request,pk):
 plant=get_object_or_404(accessible(request.user),pk=pk)
 mode=mode_for(request,plant)
 if mode is None:
  return JsonResponse({'error':'invalid_mode'},status=400)
 if mode=='demo':
  return JsonResponse(snapshot(plant))
 if not live_allowed(plant):
  return JsonResponse({'online':False,'demo':False,'error':'live_not_bound'},status=403)
 service=None
 try:
  service=service_for(plant)
  return JsonResponse(service.snapshot())
 except HAError as exc:
  payload=service.offline(exc.code) if service else {**{f:None for f in FIELDS},'online':False,'demo':False,'updated_at':None,'error':exc.code}
  return JsonResponse(payload,status=503)


@login_required
@never_cache
@require_GET
def chart(request,pk):
 plant=get_object_or_404(accessible(request.user),pk=pk)
 mode=mode_for(request,plant)
 if mode is None:
  return JsonResponse({'error':'invalid_mode'},status=400)
 if mode=='demo':
  return JsonResponse({'series':history(plant),'demo':True,'available':True})
 if not live_allowed(plant):
  return JsonResponse({'series':[],'demo':False,'error':'live_not_bound'},status=403)
 try:
  return JsonResponse(service_for(plant).history())
 except HAError as exc:
  return JsonResponse({'series':[],'demo':False,'available':False,'error':exc.code},status=503)

@login_required
@never_cache
@sensitive_post_parameters('pairing_code')
def add_plant(request):
 form=PlantForm(request.POST or None)
 if request.method=='POST' and form.is_valid():
  errors={'invalid_or_expired_code':'Код неправильний, використаний або прострочений. Створіть новий у налаштуваннях ANMA Cloud у Home Assistant.',
   'connection_failed':'Машина недоступна. Перевірте Tailscale на цьому сервері, доступ до машини та порт 8123.',
   'integration_missing':'На машині немає API ANMA. Встановіть інтеграцію v0.3.0 і перезапустіть Home Assistant.',
   'already_bound':'Ця станція вже прив’язана. Повторна прив’язка до іншого акаунта заборонена.',
   'too_many_attempts':'Забагато спроб. Спробуйте через 10 хвилин.',
   'connection_disabled':'Доступ до цієї станції призупинено адміністратором.',
   'encryption_not_configured':'Сервер ще не налаштований: адміністратор має додати ключ шифрування підключень.'}
  try:
   obj=pair_plant(request.user,form.cleaned_data['name'],form.cleaned_data['tailscale_ip'],form.cleaned_data['pairing_code'])
  except HAError as exc:
   form.add_error(None,errors.get(exc.code,'Не вдалося підтвердити підключення. Перевірте версію інтеграції та спробуйте новий код.'))
  else:
   messages.success(request,'Будинок підтверджено й додано до вашого кабінету.')
   return redirect('/app/?plant='+str(obj.pk)+'&mode=live')
 return render(request,'add_plant.html',{'form':form})

@login_required
@never_cache
def plants_page(request):
 return render(request,'plants.html',{'plants':accessible(request.user)})

@login_required
@never_cache
def edit_plant(request,pk):
 plant=get_object_or_404(Plant,pk=pk,owner=request.user)
 form=PlantRenameForm(request.POST or None,instance=plant)
 if request.method=='POST' and form.is_valid():
  form.save();messages.success(request,'Назву будинку оновлено.')
  return redirect('plants')
 return render(request,'edit_plant.html',{'home':plant,'form':form})

@login_required
@never_cache
def delete_plant(request,pk):
 plant=get_object_or_404(Plant,pk=pk,owner=request.user)
 if request.method=='POST' and request.POST.get('confirm')=='delete':
  plant.delete()
  messages.success(request,'Будинок видалено із сайту. Home Assistant залишився без змін.')
  return redirect('plants')
 return render(request,'delete_plant.html',{'home':plant})

@login_required
def integration_download(request):
 root=settings.BASE_DIR/'ha_integration'
 stream=BytesIO()
 with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
  for path in sorted((root/'custom_components/anma_cloud').rglob('*')):
   if path.is_file() and '__pycache__' not in path.parts and path.suffix in ('.py','.json','.png'):
    archive.write(path,path.relative_to(root))
  archive.write(root/'README_UA.md','README_UA.md')
 stream.seek(0)
 return FileResponse(stream,as_attachment=True,filename='ANMA_HA_Integration_v0.3.0.zip')
@login_required
def settings_page(request):return render(request,'settings.html')

@login_required
@never_cache
def demo_dashboard(request):
 from types import SimpleNamespace
 plant=SimpleNamespace(pk=0,name='ANMA · Демо будинок',model='Демонстраційні дані')
 if request.GET.get('data')=='live':return JsonResponse(snapshot(plant))
 if request.GET.get('data')=='history':return JsonResponse({'series':history(plant),'demo':True,'available':True})
 return render(request,'dashboard.html',{'plant':plant,'plants':[plant],'mode':'demo','demo_preview':True,'history_json':json.dumps(history(plant)),'live_available':False})
