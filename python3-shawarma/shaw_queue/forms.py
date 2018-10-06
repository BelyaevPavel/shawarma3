from django import forms
from django.contrib.admin import widgets
from django.utils import timezone
import datetime

from .models import Order, OrderContent, Staff, Delivery, StaffCategory, DeliveryOrder, Customer


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('id', 'daily_number', 'open_time', 'close_time',
                  'prepared_by')

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        self.fields['prepared_by'] = forms.CharField()
        self.fields['date'].widget = widgets.AdminDateWidget()
        self.fields['start_time'].widget = widgets.AdminTimeWidget()
        self.fields['end_time'].widget = widgets.AdminTimeWidget()


class DeliveryForm(forms.ModelForm):
    car_driver = forms.ModelChoiceField(queryset=Staff.objects.filter(staff_category__title__iexact='Cook'))

    class Meta:
        model = Delivery
        fields = ['car_driver']


class IncomingCallForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['phone_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'required': True,
                'placeholder': '+7XXXXXXXXXX',
                'pattern': '\+7[0-9]{10}',
                'title': 'Введите номер в формате +7XXXXXXXXXX',
                'type': 'tel'
            })
        }


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={
                'required': True,
                'placeholder': 'Введите имя',
                'pattern': "^[А-Яа-яЁё\s]+$",  # '+7[0-9]{10}',
                'title': 'Имя не может содержать цифр и спец. знаков.'
            }),
            'phone_number': forms.TextInput(attrs={
                'required': True,
                'placeholder': '+7XXXXXXXXXX',
                'pattern': "\+7[0-9]{10}",  # '+7[0-9]{10}',
                'title': 'Введите номер в формате +7XXXXXXXXXX',
                'type': 'tel'
            })
        }


class DeliveryOrderForm(forms.ModelForm):
    order = forms.ModelChoiceField(queryset=Order.objects.filter(open_time__contains=datetime.date.today),
                                   widget=forms.HiddenInput())
    #  delivery = forms.ModelChoiceField(queryset=Delivery.objects.filter(creation_timepoint__contains=datetime.date.today))
    class Meta:
        model = DeliveryOrder
        exclude = ['prep_start_timepoint']
        widgets = {
            'address': forms.TextInput(attrs={
                'class': 'test-class',
                'required': True,
                'placeholder': 'Введите адрес...'
            }),
            'obtain_timepoint': forms.DateTimeInput(attrs={
                'required': True,
                'placeholder': 'Формат: ДД.ММ.ГГГГ ЧЧ:ММ:СС',
                'pattern': "[0-3][0-9].[0-1][0-9].[0-9]{4} [0-2][0-9]:[0-6][0-9]:[0-6][0-9]",
                'title': 'Введите дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ:СС',
            }),
            'delivered_timepoint': forms.DateTimeInput(attrs={
                'required': True,
                'placeholder': 'Формат: ДД.ММ.ГГГГ ЧЧ:ММ:СС',
                'pattern': "[0-3][0-9].[0-1][0-9].[0-9]{4} [0-2][0-9]:[0-6][0-9]:[0-6][0-9]",
                'title': 'Введите дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ:СС',
            }),
            'preparation_duration': forms.TimeInput(attrs={
                'required': True,
                'placeholder': 'Формат: ЧЧ:ММ:СС',
                'pattern': "[[0-2][0-9]:[0-6][0-9]:[0-6][0-9]",
                'title': 'Введите время ЧЧ:ММ:СС',
            }),
            'delivery_duration': forms.TimeInput(attrs={
                'required': True,
                'placeholder': 'Формат: ЧЧ:ММ:СС',
                'pattern': "[0-2][0-9]:[0-6][0-9]:[0-6][0-9]",
                'title': 'Введите время в формате ЧЧ:ММ:СС',
            })
        }
