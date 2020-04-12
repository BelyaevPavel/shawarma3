from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import loader
from .forms import ConfirmOrderForm, CheckOrderStatus
from shawarma_site.settings import SHAW_QUEUE_URL, SEND_ORDER_URL, CHECK_ORDER_STATUS_URL, GET_MENU_URL
import json
import time
import random
import requests


# Create your views here.
def index(request):
    template = loader.get_template('customer_interface/index.html')
    context = {
        'categories': [
            {
                'title': 'Шаурма',
                'items': [
                    {
                        'id': 1,
                        'name': 'Шаурма М',
                        'price': 110
                    },
                    {
                        'id': 2,
                        'name': 'Шаурма С',
                        'price': 150
                    },
                    {
                        'id': 3,
                        'name': 'Шаурма Б',
                        'price': 210
                    },
                ]
            },
            {
                'title': 'Напитки',
                'items': [
                    {
                        'id': 4,
                        'name': 'Пепси',
                        'price': 50
                    },
                    {
                        'id': 5,
                        'name': 'Кола',
                        'price': 110
                    },
                    {
                        'id': 6,
                        'name': 'Фанта',
                        'price': 70
                    },
                ]
            }
        ]
    }
    return HttpResponse(template.render(context, request))


def contacts(request):
    template = loader.get_template('customer_interface/contacts.html')
    return HttpResponse(template.render({}, request))


def about(request):
    template = loader.get_template('customer_interface/contacts.html')
    return HttpResponse(template.render({}, request))


def menu(request):
    template = loader.get_template('customer_interface/menu.html')
    context = get_menu()
    return HttpResponse(template.render(context, request))


def create_order(request):
    template = loader.get_template('customer_interface/create_order.html')
    if request.method == 'POST':
        form = ConfirmOrderForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            send_order_data(cleaned_data)
            return redirect('check_order')
        else:
            context = {
                'form': ConfirmOrderForm(request.POST)
            }
            return HttpResponse(template.render(context, request))
    else:
        context = {
            'form': ConfirmOrderForm()
        }
        return HttpResponse(template.render(context, request))


def check_order(request):
    template = loader.get_template('customer_interface/check_order.html')
    if request.method == 'POST':
        form = CheckOrderStatus(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            response = check_order_status(cleaned_data['phone_number'])
            context = {
                'form': form,
                'order_status': response
            }
            return HttpResponse(template.render(context, request))
        else:
            context = {
                'form': form
            }
            return HttpResponse(template.render(context, request))
    else:
        context = {
            'form': CheckOrderStatus()
        }
        return HttpResponse(template.render(context, request))


def check_order_ajax(request):
    phone_number = request.GET.get('phone_number', None)
    try:
        response = check_order_status(phone_number)
    except:
        data = {
            'success': False
        }
        return JsonResponse(data=data)

    data = {
        'success': True,
        'order_status': response
    }
    return JsonResponse(data=data)


def check_order_status(phone_number):
    """
    Requests order status from shawarma server.
    :param phone_number:
    :return:
    """
    response = ""
    if CHECK_ORDER_STATUS_URL != "" and CHECK_ORDER_STATUS_URL is not None:
        result = requests.get(CHECK_ORDER_STATUS_URL, params={'phone_number': phone_number})
        if result.status_code == 200:
            json_results = result.json()
            response = json_results['response']
            return response
        else:
            return 'Ошибка!'
    else:
        responses = ['На модерации', 'Заказу присвоен номер 12', 'Заказ готов!']
        time.sleep(random.random() * 3)
        response = responses[random.randint(0, 2)]
    return response


def send_order_data(order_data):
    # TODO: Implement request
    """
    Sends order data to shawarma server.
    :param order_data:
    :return:
    """
    if SEND_ORDER_URL != "" and SEND_ORDER_URL is not None:
        result = requests.get(SEND_ORDER_URL, params=order_data)
        if result.status_code == 200:
            json_results = result.json()
            return json_results['success']
        else:
            return False
    else:
        return False


def get_menu():
    """
    Requests menu data from shawarma server.
    :return: Dictionary with menu categories and items.
    """

    if GET_MENU_URL != "" and GET_MENU_URL is not None:
        result = requests.get(GET_MENU_URL)
        if result.status_code == 200:
            json_results = result.json()
            response = {
                'categories': json_results['categories']
            }
            return response
        else:
            return {}
    else:
        context = {
            'categories': [
                {
                    'title': 'Шаурма',
                    'items': [
                        {
                            'id': 1,
                            'name': 'Шаурма М',
                            'price': 110
                        },
                        {
                            'id': 2,
                            'name': 'Шаурма С',
                            'price': 150
                        },
                        {
                            'id': 3,
                            'name': 'Шаурма Б',
                            'price': 210
                        },
                    ]
                },
                {
                    'title': 'Напитки',
                    'items': [
                        {
                            'id': 4,
                            'name': 'Пепси',
                            'price': 50
                        },
                        {
                            'id': 5,
                            'name': 'Кола',
                            'price': 110
                        },
                        {
                            'id': 6,
                            'name': 'Фанта',
                            'price': 70
                        },
                    ]
                }
            ]
        }
    return context
