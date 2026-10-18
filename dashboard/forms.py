from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Plant
class RegisterForm(UserCreationForm):
 email=forms.EmailField(required=True)
 class Meta:
  model=User;fields=['email','password1','password2']
 def clean_email(self):
  email=self.cleaned_data['email'].strip().lower()
  if User.objects.filter(email__iexact=email).exists():raise forms.ValidationError('Email already registered')
  return email
 def save(self,commit=True):
  user=super().save(commit=False)
  user.email=self.cleaned_data['email'];user.username=user.email
  if commit:user.save()
  return user
class PlantRenameForm(forms.ModelForm):
 class Meta:
  model=Plant;fields=['name'];labels={'name':'Назва будинку'}

class PlantForm(forms.ModelForm):
 tailscale_ip=forms.GenericIPAddressField(label='Tailscale IP',protocol='IPv4',help_text='Адреса Home Assistant, наприклад 100.101.102.103. Порт 8123.')
 pairing_code=forms.CharField(label='Код ANMA',max_length=64,widget=forms.PasswordInput(attrs={'autocomplete':'off'}),help_text='HA → ANMA Cloud → Налаштувати → Підключення сайту. Діє 15 хвилин.')
 class Meta:
  model=Plant;fields=['name','tailscale_ip'];labels={'name':'Назва будинку'}
  widgets={'name':forms.TextInput(attrs={'placeholder':'Будинок, офіс або дача'})}
 def clean_tailscale_ip(self):
  from .services.pairing import validate_address
  from .services.home_assistant import HAError
  try:return validate_address(self.cleaned_data['tailscale_ip'])
  except HAError:raise forms.ValidationError('Вкажіть дозволену Tailscale IPv4-адресу в діапазоні 100.64.0.0–100.127.255.255.') from None
