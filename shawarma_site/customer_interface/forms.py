from django import forms


class ConfirmOrderForm(forms.Form):
    name = forms.CharField(widget=forms.TextInput(attrs={
        'required': True,
        'placeholder': 'Введите имя',
        'pattern': "^[А-Яа-яЁёA-Za-z\s]+$",  # '+7[0-9]{10}',
        'title': 'Имя не может содержать цифр и спец. знаков.',
        'class': 'form-control'
    }), help_text='Имя не может содержать цифр и спец. знаков.', label='Ваше имя', max_length=12)
    phone_number = forms.CharField(widget=forms.TextInput(attrs={
        'required': True,
        'placeholder': '+7XXXXXXXXXX',
        'pattern': "\+7[0-9]{10}",  # '+7[0-9]{10}',
        'title': 'Введите номер в формате +7XXXXXXXXXX',
        'type': 'tel',
        'class': 'form-control'
    }), help_text='Введите номер в формате +7XXXXXXXXXX', label='Ваш номер телефона')
    comment = forms.CharField(max_length=100, label="Комментарий", widget=forms.TextInput(attrs={
        'class': 'form-control',
        'title': ''
    }), required=False)
    order_content = forms.CharField(widget=forms.HiddenInput(attrs={'required': True}))


class CheckOrderStatus(forms.Form):
    phone_number = forms.CharField(widget=forms.TextInput(attrs={
        'required': True,
        'placeholder': '+7XXXXXXXXXX',
        'pattern': "\+7[0-9]{10}",  # '+7[0-9]{10}',
        'title': 'Введите номер в формате +7XXXXXXXXXX',
        'type': 'tel',
        'class': 'form-control'
    }), help_text='Введите номер в формате +7XXXXXXXXXX', label='Ваш номер телефона')
