# -*- coding: utf-8 -*-


from django.http.response import HttpResponseRedirect

from .models import Menu, Order, Staff, StaffCategory, MenuCategory, OrderContent, Servery, OrderOpinion, PauseTracker
from django.template import loader
from django.core.exceptions import EmptyResultSet, MultipleObjectsReturned, PermissionDenied, ObjectDoesNotExist
from requests.exceptions import ConnectionError, ConnectTimeout, Timeout
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import logout, login, views as auth_views
from django.db.models import Max, Min, Count, Avg, F
from hashlib import md5
from shawarma.settings import TIME_ZONE, LISTNER_URL, LISTNER_PORT, PRINTER_URL, SERVER_1C_PORT, SERVER_1C_IP, \
    GETLIST_URL, SERVER_1C_USER, SERVER_1C_PASS, ORDER_URL, FORCE_TO_LISTNER
from raven.contrib.django.raven_compat.models import client
import requests
import datetime
import logging
import json
import sys
import os
import subprocess

logger = logging.getLogger(__name__)


@login_required()
def redirection(request):
    staff_category = StaffCategory.objects.get(staff__user=request.user)
    if staff_category.title == 'Cook':
        return HttpResponseRedirect('cook_interface')
    if staff_category.title == 'Cashier':
        return HttpResponseRedirect('menu')
    if staff_category.title == 'Operator':
        return HttpResponseRedirect('current_queue')


def cook_pause(request):
    user = request.user
    try:
        staff = Staff.objects.get(user=user)
    except MultipleObjectsReturned:
        data = {
            'success': False,
            'message': 'Множество экземпляров персонала возвращено!'
        }
        logger.error('{} Множество экземпляров персонала возвращено!'.format(user))
        client.captureException()
        return JsonResponse(data)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске персонала!'
        }
        logger.error('{} Что-то пошло не так при поиске персонала!'.format(user))
        return JsonResponse(data)
    if staff.available:
        pause = PauseTracker(staff=staff, start_timestamp=datetime.datetime.now())
        pause.save()
        staff.available = False
        staff.save()
    else:
        try:
            last_pause = PauseTracker.objects.filter(staff=staff,
                                                     start_timestamp__contains=datetime.date.today()).order_by(
                'start_timestamp')
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске последней паузы!'
            }
            return JsonResponse(data)
        if len(last_pause) > 0:
            last_pause = last_pause[len(last_pause) - 1]
            last_pause.end_timestamp = datetime.datetime.now()
            last_pause.save()

        staff.available = True
        staff.save()

    data = {
        'success': True
    }
    if staff.staff_category.title == 'Cook':
        return cook_interface(request)

    if staff.staff_category.title == 'Shashlychnik':
        return shashlychnik_interface(request)


def logout_view(request):
    user = request.user
    try:
        staff = Staff.objects.get(user=user)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске пользователя!'
        }
        client.captureException()
        return JsonResponse(data)
    if staff.available:
        staff.available = False
        staff.save()
    logout(request)
    return redirect('welcomer')


# Create your views here.
@login_required()
def welcomer(request):
    template = loader.get_template('shaw_queue/welcomer.html')
    try:
        context = {
            'staff_category': StaffCategory.objects.get(staff__user=request.user),
        }
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске категории персонала!'
        }
        client.captureException()
        return JsonResponse(data)
    return HttpResponse(template.render(context, request))


@login_required()
def menu(request):
    try:
        menu_items = Menu.objects.order_by('title')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске последней паузы!'
        }
        client.captureException()
        return JsonResponse(data)
    template = loader.get_template('shaw_queue/menu_page.html')
    try:
        context = {
            'user': request.user,
            'available_cookers': Staff.objects.filter(available=True, staff_category__title__iexact='Cook'),
            'staff_category': StaffCategory.objects.get(staff__user=request.user),
            'menu_items': menu_items,
            'menu_categories': MenuCategory.objects.order_by('weight')
        }
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске последней паузы!'
        }
        client.captureException()
        return JsonResponse(data)
    return HttpResponse(template.render(context, request))


def search_comment(request):
    content_id = request.POST.get('id', '')
    comment_part = request.POST.get('note', '')
    data = {
        'html': ''
    }
    if len(comment_part) > 0:
        try:
            comments = OrderContent.objects.filter(note__icontains=comment_part).distinct('note')[:5]
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске комментариев!'
            }
            client.captureException()
            return JsonResponse(data)
        context = {
            'id': content_id,
            'comments': comments
        }
        template = loader.get_template('shaw_queue/suggestion_list.html')
        data['html'] = template.render(context, request)
    return JsonResponse(data)


def evaluation(request):
    template = loader.get_template('shaw_queue/evaluation_page.html')
    context = {

    }
    return HttpResponse(template.render(context, request))


def evaluate(request):
    daily_number = request.POST.get('daily_number', None)
    mark = request.POST.get('mark', None)
    note = request.POST.get('note', '')
    try:
        if daily_number:
            daily_number = int(daily_number)
            try:
                current_daily_number = Order.objects.filter(open_time__contains=datetime.date.today()).aggregate(
                    Max('daily_number'))
            except:
                data = {
                    'success': False,
                    'message': 'Что-то пошло не так при поиске номера заказов!'
                }
                client.captureException()
                return JsonResponse(data)
            current_daily_number = current_daily_number['daily_number__max']
            hundreds = current_daily_number // 100
            if daily_number + hundreds * 100 <= current_daily_number:
                if hundreds * 100 <= daily_number + hundreds * 100:
                    try:
                        order = Order.objects.get(open_time__contains=datetime.date.today(),
                                                  daily_number=daily_number + hundreds * 100)
                    except:
                        data = {
                            'success': False,
                            'message': 'Что-то пошло не так при поиске заказа!'
                        }
                        client.captureException()
                        return JsonResponse(data)
                    order_opinion = OrderOpinion(note=note, mark=int(mark), order=order,
                                                 post_time=datetime.datetime.now())
                    order_opinion.save()
                else:
                    try:
                        order = Order.objects.get(open_time__contains=datetime.date.today(),
                                                  daily_number=daily_number + (hundreds - 1) * 100)
                    except:
                        data = {
                            'success': False,
                            'message': 'Что-то пошло не так при поиске заказа!'
                        }
                        client.captureException()
                        return JsonResponse(data)
                    order_opinion = OrderOpinion(note=note, mark=int(mark), order=order,
                                                 post_time=datetime.datetime.now())
                    order_opinion.save()
        else:
            order_opinion = OrderOpinion(note=note, mark=int(mark), post_time=datetime.datetime.now())
            order_opinion.save()

        data = {
            'success': True
        }
        return JsonResponse(data)
    except:
        data = {
            'success': False
        }
        client.captureException()
        return JsonResponse(data)


def buyer_queue(request):
    try:
        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                           is_canceled=False, is_ready=False).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске открытых заказов!'
        }
        client.captureException()
        return JsonResponse(data)
    try:
        ready_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                            content_completed=True, supplement_completed=True, is_ready=True,
                                            is_canceled=False).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске готовых заказов!'
        }
        client.captureException()
        return JsonResponse(data)
    context = {
        'open_orders': [{'servery': order.servery, 'daily_number': order.daily_number} for order in open_orders],
        'ready_orders': [{'servery': order.servery, 'daily_number': order.daily_number} for order in
                         ready_orders],
        'display_open_orders': [{'servery': order.servery, 'daily_number': order.daily_number % 100} for order in
                                open_orders],
        'display_ready_orders': [{'servery': order.servery, 'daily_number': order.daily_number % 100} for order in
                                 ready_orders]
    }
    template = loader.get_template('shaw_queue/buyer_queue.html')
    return HttpResponse(template.render(context, request))


def buyer_queue_ajax(request):
    try:
        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                           is_canceled=False, is_ready=False).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске открытых заказов!'
        }
        client.captureException()
        return JsonResponse(data)
    try:
        ready_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                            content_completed=True, supplement_completed=True, is_ready=True,
                                            is_canceled=False).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске готовых заказов!'
        }
        client.captureException()
        return JsonResponse(data)
    context = {
        'open_orders': [{'servery': order.servery, 'daily_number': order.daily_number} for order in open_orders],
        'ready_orders': [{'servery': order.servery, 'daily_number': order.daily_number} for order in
                         ready_orders],
        'display_open_orders': [{'servery': order.servery, 'daily_number': order.daily_number % 100} for order in
                                open_orders],
        'display_ready_orders': [{'servery': order.servery, 'daily_number': order.daily_number % 100} for order in
                                 ready_orders]
    }
    template = loader.get_template('shaw_queue/buyer_queue_ajax.html')
    data = {
        'html': template.render(context, request),
        'ready': json.dumps([order.daily_number for order in ready_orders.filter(is_voiced=False)]),
        'voiced': json.dumps([order.is_voiced for order in ready_orders.filter(is_voiced=False)])
    }
    # for order in ready_orders:
    #     order.is_voiced = True
    #     order.save()
    return JsonResponse(data)


@login_required()
def current_queue(request):
    try:
        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                           is_canceled=False, is_ready=False).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске открытых заказов!'
        }
        client.captureException()
        return JsonResponse(data)
    try:
        ready_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                            is_canceled=False, content_completed=True, shashlyk_completed=True,
                                            supplement_completed=True, is_ready=True).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске готовых заказов!'
        }
        client.captureException()
        return JsonResponse(data)
    # print open_orders
    # print ready_orders

    template = loader.get_template('shaw_queue/current_queue_grid.html')
    context = {
        'open_orders': [{'order': open_order,
                         'printed': open_order.printed,
                         'cook_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                             menu_item__can_be_prepared_by__title__iexact='cook').filter(
                             finish_timestamp__isnull=False).aggregate(count=Count('id')),
                         'cook_part_count': OrderContent.objects.filter(order=open_order).filter(
                             menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                         'shashlychnik_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                             menu_item__can_be_prepared_by__title__iexact='shashlychnik').filter(
                             finish_timestamp__isnull=False).aggregate(count=Count('id')),
                         'shashlychnik_part_count': OrderContent.objects.filter(order=open_order).filter(
                             menu_item__can_be_prepared_by__title__iexact='shashlychnik').aggregate(count=Count('id')),
                         'operator_part': OrderContent.objects.filter(order=open_order).filter(
                             menu_item__can_be_prepared_by__title__iexact='operator')
                         } for open_order in open_orders],
        'ready_orders': [{'order': open_order,
                          'cook_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                              menu_item__can_be_prepared_by__title__iexact='cook').filter(
                              finish_timestamp__isnull=False).aggregate(count=Count('id')),
                          'cook_part_count': OrderContent.objects.filter(order=open_order).filter(
                              menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                          'shashlychnik_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                              menu_item__can_be_prepared_by__title__iexact='shashlychnik').filter(
                              finish_timestamp__isnull=False).aggregate(count=Count('id')),
                          'shashlychnik_part_count': OrderContent.objects.filter(order=open_order).filter(
                              menu_item__can_be_prepared_by__title__iexact='shashlychnik').aggregate(count=Count('id')),
                          'operator_part': OrderContent.objects.filter(order=open_order).filter(
                              menu_item__can_be_prepared_by__title__iexact='operator')
                          } for open_order in ready_orders],
        'open_length': len(open_orders),
        'ready_length': len(ready_orders),
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
    }
    # print context
    return HttpResponse(template.render(context, request))


@login_required()
def order_history(request):
    try:
        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=False,
                                           is_canceled=False, is_ready=True).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске последней паузы!'
        }
        client.captureException()
        return JsonResponse(data)
    # print open_orders
    # print ready_orders

    template = loader.get_template('shaw_queue/order_history.html')
    try:
        context = {
            'open_orders': [{'order': open_order,
                             'printed': open_order.printed,
                             'cook_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                                 menu_item__can_be_prepared_by__title__iexact='cook').filter(
                                 finish_timestamp__isnull=False).aggregate(count=Count('id')),
                             'cook_part_count': OrderContent.objects.filter(order=open_order).filter(
                                 menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                             'operator_part': OrderContent.objects.filter(order=open_order).filter(
                                 menu_item__can_be_prepared_by__title__iexact='operator')
                             } for open_order in open_orders],
            'open_length': len(open_orders),
            'staff_category': StaffCategory.objects.get(staff__user=request.user),
        }
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при подготовке шаблона!'
        }
        client.captureException()
        return JsonResponse(data)
    # print context
    return HttpResponse(template.render(context, request))


@login_required()
def current_queue_ajax(request):
    try:
        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                           is_canceled=False, is_ready=False).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске последней паузы!'
        }
        client.captureException()
        return JsonResponse(data)

    try:
        ready_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                            is_canceled=False, content_completed=True, shashlyk_completed=True,
                                            supplement_completed=True, is_ready=True).order_by('open_time')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске последней паузы!'
        }
        client.captureException()
        return JsonResponse(data)

    template = loader.get_template('shaw_queue/current_queue_grid_ajax.html')
    try:
        context = {
            'open_orders': [{'order': open_order,
                             'printed': open_order.printed,
                             'cook_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                                 menu_item__can_be_prepared_by__title__iexact='cook').filter(
                                 finish_timestamp__isnull=False).aggregate(count=Count('id')),
                             'cook_part_count': OrderContent.objects.filter(order=open_order).filter(
                                 menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                             'shashlychnik_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                                 menu_item__can_be_prepared_by__title__iexact='shashlychnik').filter(
                                 finish_timestamp__isnull=False).aggregate(count=Count('id')),
                             'shashlychnik_part_count': OrderContent.objects.filter(order=open_order).filter(
                                 menu_item__can_be_prepared_by__title__iexact='shashlychnik').aggregate(
                                 count=Count('id')),
                             'operator_part': OrderContent.objects.filter(order=open_order).filter(
                                 menu_item__can_be_prepared_by__title__iexact='operator')
                             } for open_order in open_orders],
            'ready_orders': [{'order': open_order,
                              'cook_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                                  menu_item__can_be_prepared_by__title__iexact='cook').filter(
                                  finish_timestamp__isnull=False).aggregate(count=Count('id')),
                              'cook_part_count': OrderContent.objects.filter(order=open_order).filter(
                                  menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                              'shashlychnik_part_ready_count': OrderContent.objects.filter(order=open_order).filter(
                                  menu_item__can_be_prepared_by__title__iexact='shashlychnik').filter(
                                  finish_timestamp__isnull=False).aggregate(count=Count('id')),
                              'shashlychnik_part_count': OrderContent.objects.filter(order=open_order).filter(
                                  menu_item__can_be_prepared_by__title__iexact='shashlychnik').aggregate(
                                  count=Count('id')),
                              'operator_part': OrderContent.objects.filter(order=open_order).filter(
                                  menu_item__can_be_prepared_by__title__iexact='operator')
                              } for open_order in ready_orders],
            'open_length': len(open_orders),
            'ready_length': len(ready_orders),
            'staff_category': StaffCategory.objects.get(staff__user=request.user),
        }
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске последней паузы!'
        }
        client.captureException()
        return JsonResponse(data)
    data = {
        'html': template.render(context, request)
    }
    return JsonResponse(data)


@login_required()
def production_queue(request):
    free_content = OrderContent.objects.filter(order__open_time__contains=datetime.date.today(),
                                               order__close_time__isnull=True,
                                               menu_item__can_be_prepared_by__title__iexact='cook').order_by(
        'order__open_time')
    template = loader.get_template('shaw_queue/production_queue.html')
    context = {
        'free_content': free_content,
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
    }
    return HttpResponse(template.render(context, request))


@login_required()
def cook_interface(request):
    def new_processor(request):
        user = request.user
        staff = Staff.objects.get(user=user)
        if not staff.available:
            staff.available = True
            staff.save()
        context = None
        taken_order_content = None
        taken_orders = Order.objects.filter(prepared_by=staff, open_time__isnull=False,
                                            open_time__contains=datetime.date.today(), is_canceled=False,
                                            content_completed=False,
                                            close_time__isnull=True).order_by('open_time'),
        has_order = False
        if taken_orders[0]:
            taken_order_content = OrderContent.objects.filter(order=taken_orders[0][0],
                                                              menu_item__can_be_prepared_by__title__iexact='Cook',
                                                              finish_timestamp__isnull=True).order_by('id')
            if len(taken_order_content) > 0:
                has_order = True
        # print "Orders: {}".format(taken_orders)
        # print "Order: {}".format(taken_orders[0][0])
        # print "Has order: {}. Content compleated: {}".format(has_order, taken_orders[0][0].content_completed)

        if not has_order:
            free_orders = Order.objects.filter(prepared_by__isnull=True, is_canceled=False,
                                               open_time__contains=datetime.date.today()).order_by('open_time')

            for free_order in free_orders:
                taken_order_content = OrderContent.objects.filter(order=free_order,
                                                                  menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
                    'id')
                taken_order_in_grill_content = OrderContent.objects.filter(order=free_order,
                                                                           grill_timestamp__isnull=False,
                                                                           menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
                    'id')
                # ALERT! Only SuperGuy can handle this amount of shawarma!!!
                if len(taken_order_content) > 6:
                    if staff.super_guy:
                        free_order.prepared_by = staff
                    else:
                        continue
                else:
                    free_order.prepared_by = staff

                if free_order.prepared_by == staff:
                    free_order.save()
                    # print "Free orders prepared_by: {}".format(free_order.prepared_by)
                    context = {
                        'free_order': free_order,
                        'order_content': [{'number': number,
                                           'item': item} for number, item in enumerate(taken_order_content, start=1)],
                        'in_grill_content': [{'number': number,
                                              'item': item} for number, item in
                                             enumerate(taken_order_in_grill_content, start=1)],
                        'staff_category': staff
                    }

                break
        else:
            taken_order_content = OrderContent.objects.filter(order=taken_orders[0][0],
                                                              menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
                'id')
            taken_order_in_grill_content = OrderContent.objects.filter(order=taken_orders[0][0],
                                                                       grill_timestamp__isnull=False,
                                                                       menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
                'id')
            context = {
                'free_order': taken_orders[0][0],
                'order_content': [{'number': number,
                                   'item': item} for number, item in enumerate(taken_order_content, start=1)],
                'in_grill_content': [{'number': number,
                                      'item': item} for number, item in
                                     enumerate(taken_order_in_grill_content, start=1)],
                'staff_category': staff
            }

        template = loader.get_template('shaw_queue/cook_interface_alt.html')
        return HttpResponse(template.render(context, request))

    def old_processor(request):
        user = request.user
        user_avg_prep_duration = OrderContent.objects.filter(staff_maker__user=user, start_timestamp__isnull=False,
                                                             finish_timestamp__isnull=False).values(
            'menu_item__id').annotate(
            production_duration=Avg(F('finish_timestamp') - F('start_timestamp'))).order_by('production_duration')

        available_cook_count = Staff.objects.filter(user__last_login__contains=datetime.date.today(),
                                                    staff_category__title__iexact='cook').aggregate(
            Count('id'))  # Change to logged.

        free_content = OrderContent.objects.filter(order__open_time__contains=datetime.date.today(),
                                                   order__close_time__isnull=True,
                                                   order__is_canceled=False,
                                                   menu_item__can_be_prepared_by__title__iexact='cook',
                                                   start_timestamp__isnull=True).order_by(
            'order__open_time')[:available_cook_count['id__count']]

        in_progress_content = OrderContent.objects.filter(order__open_time__contains=datetime.date.today(),
                                                          order__close_time__isnull=True,
                                                          order__is_canceled=False,
                                                          start_timestamp__isnull=False,
                                                          finish_timestamp__isnull=True,
                                                          staff_maker__user=user,
                                                          is_in_grill=False,
                                                          is_canceled=False).order_by(
            'order__open_time')[:1]

        in_grill_content = OrderContent.objects.filter(order__open_time__contains=datetime.date.today(),
                                                       order__close_time__isnull=True,
                                                       order__is_canceled=False,
                                                       start_timestamp__isnull=False,
                                                       finish_timestamp__isnull=True,
                                                       staff_maker__user=user,
                                                       is_in_grill=True,
                                                       is_canceled=False)

        in_grill_dict = [{'product': product,
                          'time_in_grill': datetime.datetime.now().replace(
                              tzinfo=None) - product.grill_timestamp.replace(
                              tzinfo=None)} for product in in_grill_content]

        if len(free_content) > 0:
            if len(in_progress_content) == 0:
                free_content_ids = [content.id for content in free_content]
                id_to_prepare = -1
                for product in user_avg_prep_duration:
                    if product['menu_item__id'] in free_content_ids:
                        id_to_prepare = product['menu_item__id']
                        break

                if id_to_prepare == -1:
                    id_to_prepare = free_content_ids[0]

                context = {
                    'next_product': OrderContent.objects.get(id=id_to_prepare),
                    'in_progress': None,
                    'in_grill': in_grill_dict,
                    'current_time': datetime.datetime.now(),
                    'staff_category': StaffCategory.objects.get(staff__user=request.user),
                }
            else:
                context = {
                    'next_product': None,
                    'in_progress': in_progress_content[0],
                    'in_grill': in_grill_dict,
                    'current_time': datetime.datetime.now(),
                    'staff_category': StaffCategory.objects.get(staff__user=request.user),
                }
        else:
            if len(in_progress_content) != 0:
                context = {
                    'next_product': None,
                    'in_progress': in_progress_content[0],
                    'in_grill': in_grill_dict,
                    'current_time': datetime.datetime.now(),
                    'staff_category': StaffCategory.objects.get(staff__user=request.user),

                }
            else:
                context = {
                    'next_product': None,
                    'in_progress': None,
                    'in_grill': in_grill_dict,
                    'current_time': datetime.datetime.now(),
                    'staff_category': StaffCategory.objects.get(staff__user=request.user),

                }

        template = loader.get_template('shaw_queue/cook_interface.html')
        return HttpResponse(template.render(context, request))

    def new_processor_with_queue(request):
        user = request.user
        staff = Staff.objects.get(user=user)
        # if not staff.available:
        #     staff.available = True
        #     staff.save()
        context = None
        taken_order_content = None
        new_order = Order.objects.filter(prepared_by=staff, open_time__isnull=False,
                                         open_time__contains=datetime.date.today(), is_canceled=False,
                                         content_completed=False, is_grilling=False,
                                         close_time__isnull=True).order_by('open_time')
        other_orders = Order.objects.filter(prepared_by=staff, open_time__isnull=False,
                                            open_time__contains=datetime.date.today(), is_canceled=False,
                                            close_time__isnull=True).order_by('open_time')
        has_order = False
        if len(new_order) > 0:
            new_order = new_order[0]
            taken_order_content = OrderContent.objects.filter(order=new_order,
                                                              menu_item__can_be_prepared_by__title__iexact='Cook',
                                                              finish_timestamp__isnull=True).order_by('id')
            if len(taken_order_content) > 0:
                has_order = True

        taken_order_content = OrderContent.objects.filter(order=new_order,
                                                          menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
            'id')
        taken_order_in_grill_content = OrderContent.objects.filter(order=new_order,
                                                                   grill_timestamp__isnull=False,
                                                                   menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
            'id')
        context = {
            'free_order': new_order,
            'order_content': [{'number': number,
                               'item': item} for number, item in enumerate(taken_order_content, start=1)],
            'in_grill_content': [{'number': number,
                                  'item': item} for number, item in
                                 enumerate(taken_order_in_grill_content, start=1)],
            'cooks_orders': [{'order': cooks_order,
                              'cook_content_count': len(OrderContent.objects.filter(order=cooks_order,
                                                                                    menu_item__can_be_prepared_by__title__iexact='cook'))}
                             for cooks_order in other_orders if len(OrderContent.objects.filter(order=cooks_order,
                                                                                                menu_item__can_be_prepared_by__title__iexact='cook')) > 0],
            'staff_category': staff.staff_category,
            'staff': staff
        }

        template = loader.get_template('shaw_queue/cook_interface_with_queue.html')
        aux_html = template.render(context, request)
        return HttpResponse(template.render(context, request))

    return new_processor_with_queue(request)


@login_required()
def c_i_a(request):
    def new_processor(request):
        user = request.user
        staff = Staff.objects.get(user=user)
        # if not staff.available:
        #     staff.available = True
        #     staff.save()
        # print u"AJAX from {}".format(user)
        context = None
        taken_order_content = None
        taken_orders = Order.objects.filter(prepared_by=staff, open_time__isnull=False,
                                            open_time__contains=datetime.date.today(), is_canceled=False,
                                            content_completed=False,
                                            close_time__isnull=True).order_by('open_time'),
        has_order = False
        if taken_orders[0]:
            taken_order_content = OrderContent.objects.filter(order=taken_orders[0][0],
                                                              menu_item__can_be_prepared_by__title__iexact='Cook',
                                                              finish_timestamp__isnull=True).order_by('id')
            if len(taken_order_content) > 0:
                has_order = True
        # print "Orders: {}".format(taken_orders)
        # print "Order: {}".format(taken_orders[0][0])
        # print "Has order: {}. Content compleated: {}".format(has_order, taken_orders[0][0].content_completed)

        if not has_order:
            free_orders = Order.objects.filter(prepared_by__isnull=True, is_canceled=False,
                                               open_time__contains=datetime.date.today()).order_by('open_time')

            for free_order in free_orders:
                taken_order_content = OrderContent.objects.filter(order=free_order,
                                                                  menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
                    'id')
                # ALERT! Only SuperGuy can handle this amount of shawarma!!!
                if len(taken_order_content) > 6:
                    if staff.super_guy:
                        free_order.prepared_by = staff
                    else:
                        continue
                else:
                    free_order.prepared_by = staff

                if free_order.prepared_by == staff:
                    free_order.save()
                    # print "Free orders prepared_by: {}".format(free_order.prepared_by)
                    context = {
                        'free_order': free_order,
                        'order_content': [{'number': number,
                                           'item': item} for number, item in enumerate(taken_order_content, start=1)],
                        'staff_category': staff
                    }

                break
        else:
            taken_order_content = OrderContent.objects.filter(order=taken_orders[0][0],
                                                              menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
                'id')
            context = {
                'free_order': taken_orders[0][0],
                'order_content': [{'number': number,
                                   'item': item} for number, item in enumerate(taken_order_content, start=1)],
                'staff_category': staff
            }

        template = loader.get_template('shaw_queue/cook_interface_alt_ajax.html')
        data = {
            'html': json.dumps(template.render(context, request))
        }
        return JsonResponse(data)

    def queue_processor(request):
        user = request.user
        try:
            staff = Staff.objects.get(user=user)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске пользователя!'
            }
            client.captureException()
            return JsonResponse(data)
        # if not staff.available:
        #     staff.available = True
        #     staff.save()
        context = None
        taken_order_content = None
        other_orders = Order.objects.filter(prepared_by=staff, open_time__isnull=False,
                                            open_time__contains=datetime.date.today(), is_canceled=False,
                                            close_time__isnull=True).order_by('open_time')
        try:
            new_order = Order.objects.filter(prepared_by=staff, open_time__isnull=False,
                                             open_time__contains=datetime.date.today(), is_canceled=False,
                                             content_completed=False, is_grilling=False,
                                             close_time__isnull=True).order_by('open_time')
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске заказа!'
            }
            client.captureException()
            return JsonResponse(data)

        has_order = False
        if len(new_order) > 0:
            new_order = new_order[0]
            try:
                taken_order_content = OrderContent.objects.filter(order=new_order,
                                                                  menu_item__can_be_prepared_by__title__iexact='Cook',
                                                                  finish_timestamp__isnull=True).order_by('id')
            except:
                data = {
                    'success': False,
                    'message': 'Что-то пошло не так при поиске продуктов!'
                }
                client.captureException()
                return JsonResponse(data)
            if len(taken_order_content) > 0:
                has_order = True

        try:
            taken_order_content = OrderContent.objects.filter(order=new_order,
                                                              menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
                'id')
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске продуктов!'
            }
            client.captureException()
            return JsonResponse(data)
        try:
            taken_order_in_grill_content = OrderContent.objects.filter(order=new_order,
                                                                       grill_timestamp__isnull=False,
                                                                       menu_item__can_be_prepared_by__title__iexact='Cook').order_by(
                'id')
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске продуктов!'
            }
            client.captureException()
            return JsonResponse(data)
        context = {
            'selected_order': new_order,
            'order_content': [{'number': number,
                               'item': item} for number, item in enumerate(taken_order_content, start=1)],
            'staff_category': staff.staff_category,
            'staff': staff
        }
        template = loader.get_template('shaw_queue/selected_order_content.html')
        context_other = {
            'cooks_orders': [{'order': cooks_order,
                              'cook_content_count': len(OrderContent.objects.filter(order=cooks_order,
                                                                                    menu_item__can_be_prepared_by__title__iexact='cook'))}
                             for cooks_order in other_orders if len(OrderContent.objects.filter(order=cooks_order,
                                                                                                menu_item__can_be_prepared_by__title__iexact='cook')) > 0]
        }
        template_other = loader.get_template('shaw_queue/cooks_order_queue.html')
        data = {
            'success': True,
            'html': template.render(context, request),
            'html_other': template_other.render(context_other, request)
        }

        return JsonResponse(data=data)

    return queue_processor(request)


@login_required()
def shashlychnik_interface(request):
    def new_processor_with_queue(request):
        user = request.user
        staff = Staff.objects.get(user=user)
        # if not staff.available:
        #     staff.available = True
        #     staff.save()
        context = None
        taken_order_content = None
        new_orders = Order.objects.filter(open_time__isnull=False,
                                          open_time__contains=datetime.date.today(), is_canceled=False,
                                          shashlyk_completed=False, is_grilling_shash=False,
                                          close_time__isnull=True).order_by('open_time')
        other_orders = Order.objects.filter(open_time__isnull=False,
                                            open_time__contains=datetime.date.today(), is_canceled=False,
                                            close_time__isnull=True).order_by('open_time')
        has_order = False
        selected_order = None
        for order in new_orders:
            taken_order_content = OrderContent.objects.filter(order=order,
                                                              menu_item__can_be_prepared_by__title__iexact='Shashlychnik',
                                                              finish_timestamp__isnull=True).order_by('id')
            if len(taken_order_content) > 0:
                has_order = True
                selected_order = order
                break

        taken_order_content = OrderContent.objects.filter(order=selected_order,
                                                          menu_item__can_be_prepared_by__title__iexact='Shashlychnik').order_by(
            'id')
        taken_order_in_grill_content = OrderContent.objects.filter(order=selected_order,
                                                                   grill_timestamp__isnull=False,
                                                                   menu_item__can_be_prepared_by__title__iexact='Shashlychnik').order_by(
            'id')
        context = {
            'selected_order': selected_order,
            'order_content': [{'number': number,
                               'item': item} for number, item in enumerate(taken_order_content, start=1)],
            'in_grill_content': [{'number': number,
                                  'item': item} for number, item in
                                 enumerate(taken_order_in_grill_content, start=1)],
            'cooks_orders': [{'order': cooks_order,
                              'cook_content_count': len(OrderContent.objects.filter(order=cooks_order,
                                                                                    menu_item__can_be_prepared_by__title__iexact='Shashlychnik'))}
                             for cooks_order in other_orders if len(OrderContent.objects.filter(order=cooks_order,
                                                                                                menu_item__can_be_prepared_by__title__iexact='Shashlychnik')) > 0],
            'staff_category': staff.staff_category,
            'staff': staff
        }

        template = loader.get_template('shaw_queue/shaslychnik_interface_with_queue.html')
        aux_html = template.render(context, request)
        return HttpResponse(template.render(context, request))

    return new_processor_with_queue(request)


@login_required()
def s_i_a(request):
    def queue_processor(request):
        user = request.user
        staff = Staff.objects.get(user=user)
        # if not staff.available:
        #     staff.available = True
        #     staff.save()
        context = None
        taken_order_content = None
        new_order = Order.objects.filter(open_time__isnull=False,
                                         open_time__contains=datetime.date.today(), is_canceled=False,
                                         shashlyk_completed=False, is_grilling_shash=False,
                                         close_time__isnull=True).order_by('open_time')
        has_order = False
        selected_order = None
        for order in new_order:
            taken_order_content = OrderContent.objects.filter(order=order,
                                                              menu_item__can_be_prepared_by__title__iexact='Shashlychnik',
                                                              finish_timestamp__isnull=True).order_by('id')
            if len(taken_order_content) > 0:
                has_order = True
                selected_order = order
                break

        taken_order_content = OrderContent.objects.filter(order=selected_order,
                                                          menu_item__can_be_prepared_by__title__iexact='Shashlychnik').order_by(
            'id')
        taken_order_in_grill_content = OrderContent.objects.filter(order=selected_order,
                                                                   grill_timestamp__isnull=False,
                                                                   menu_item__can_be_prepared_by__title__iexact='Shashlychnik').order_by(
            'id')
        context = {
            'selected_order': selected_order,
            'order_content': [{'number': number,
                               'item': item} for number, item in enumerate(taken_order_content, start=1)],
            'staff_category': staff.staff_category,
            'staff': staff
        }
        template = loader.get_template('shaw_queue/selected_order_content.html')
        data = {
            'success': True,
            'html': template.render(context, request)
        }

        return JsonResponse(data=data)

    return queue_processor(request)


@login_required()
@permission_required('shaw_queue.change_order')
def set_cooker(request, order_id, cooker_id):
    try:
        order = Order.objects.get_object_or_404(id=order_id)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске заказа!'
        }
        client.captureException()
        return JsonResponse(data)
    try:
        cooker = Staff.objects.get_object_or_404(id=cooker_id)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске повара!'
        }
        client.captureException()
        return JsonResponse(data)
    order.prepared_by = cooker

    return JsonResponse(data={'success': True})


@login_required()
@permission_required('shaw_queue.change_order')
def order_content(request, order_id):
    order_info = get_object_or_404(Order, id=order_id)
    order_content = OrderContent.objects.filter(order_id=order_id)
    flag = True
    for item in order_content:
        if item.finish_timestamp is None:
            flag = False
    if flag:
        order_info.content_completed = True
        order_info.supplement_completed = True
    order_info.save()
    current_order_content = OrderContent.objects.filter(order=order_id)
    template = loader.get_template('shaw_queue/order_content.html')
    context = {
        'order_info': order_info,
        'maker': order_info.prepared_by,
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
        'order_content': current_order_content,
        'ready': order_info.content_completed and order_info.supplement_completed,
        'serveries': Servery.objects.all()
    }
    return HttpResponse(template.render(context, request))


def print_order(request, order_id):
    order_info = get_object_or_404(Order, id=order_id)
    order_info.printed = True
    order_info.save()
    order_content = OrderContent.objects.filter(order_id=order_id).values('menu_item__title', 'menu_item__price',
                                                                          'note').annotate(
        count_titles=Count('menu_item__title')).annotate(count_notes=Count('note'))
    template = loader.get_template('shaw_queue/print_order_wh.html')
    context = {
        'order_info': order_info,
        'order_content': order_content
    }

    cmd = 'echo "{}"'.format(template.render(context, request)) + " | lp -h " + PRINTER_URL
    scmd = cmd.encode('utf-8')
    os.system(scmd)

    return HttpResponse(template.render(context, request))


def voice_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except:
        client.captureException()
        return HttpResponse()
    order.is_voiced = False
    order.save()

    return HttpResponse()


def unvoice_order(request):
    daily_number = request.POST.get('daily_number', None)
    data = {
        'success': False
    }
    if daily_number:
        try:
            order = Order.objects.get(daily_number=daily_number, open_time__contains=datetime.date.today())
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске заказа!'
            }
            client.captureException()
            return JsonResponse(data)
        order.is_voiced = True
        order.save()
        data = {
            'success': True
        }

    return JsonResponse(data=data)


def select_order(request):
    user = request.user
    try:
        staff = Staff.objects.get(user=user)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске персонала!'
        }
        client.captureException()
        return JsonResponse(data)
    order_id = request.POST.get('order_id', None)
    data = {
        'success': False
    }
    if order_id:
        try:
            context = {
                'selected_order': get_object_or_404(Order, id=order_id),
                'order_content': [{'number': number,
                                   'item': item} for number, item in
                                  enumerate(OrderContent.objects.filter(order__id=order_id,
                                                                        menu_item__can_be_prepared_by__title__iexact='Cook'),
                                            start=1)],
                'staff_category': staff.staff_category
            }
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске последней паузы!'
            }
            client.captureException()
            return JsonResponse(data)
        template = loader.get_template('shaw_queue/selected_order_content.html')
        data = {
            'success': True,
            'html': template.render(context, request)
        }

    return JsonResponse(data=data)


def shashlychnik_select_order(request):
    user = request.user
    staff = Staff.objects.get(user=user)
    order_id = request.POST.get('order_id', None)
    data = {
        'success': False
    }
    if order_id:
        context = {
            'selected_order': get_object_or_404(Order, id=order_id),
            'order_content': [{'number': number,
                               'item': item} for number, item in
                              enumerate(OrderContent.objects.filter(order__id=order_id,
                                                                    menu_item__can_be_prepared_by__title__iexact='Shashlychnik'),
                                        start=1)],
            'staff_category': staff.staff_category
        }
        template = loader.get_template('shaw_queue/selected_order_content.html')
        data = {
            'success': True,
            'html': template.render(context, request)
        }

    return JsonResponse(data=data)


def voice_all(request):
    try:
        today_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                            is_ready=True)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске заказов!'
        }
        client.captureException()
        return JsonResponse(data)
    for order in today_orders:
        order.is_voiced = False
        order.save()

    return HttpResponse()


@login_required()
@permission_required('shaw_queue.add_order')
def make_order(request):
    servery_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    #servery_ip = '127.0.0.1'
    content = json.loads(request.POST['order_content'])
    is_paid = json.loads(request.POST['is_paid'])
    paid_with_cash = json.loads(request.POST['paid_with_cash'])
    cook_choose = request.POST['cook_choose']

    if len(content) == 0:
        data = {
            'success': False,
            'message': 'Order is empty!'
        }
        return JsonResponse(data)

    try:
        servery = Servery.objects.get(ip_address=servery_ip)
    except MultipleObjectsReturned:
        data = {
            'success': False,
            'message': 'Multiple serveries returned!'
        }
        client.captureException()
        return JsonResponse(data)
    except:
        data = {
            'success': False,
            'message': 'Something wrong happened while getting servery!'
        }
        client.captureException()
        return JsonResponse(data)

    order_next_number = 0
    try:
        order_last_daily_number = Order.objects.filter(open_time__contains=datetime.date.today()).aggregate(
            Max('daily_number'))
    except EmptyResultSet:
        data = {
            'success': False,
            'message': 'Empty set of orders returned!'
        }
        client.captureException()
        return JsonResponse(data)
    except:
        data = {
            'success': False,
            'message': 'Something wrong happened while getting set of orders!'
        }
        client.captureException()
        return JsonResponse(data)

    if order_last_daily_number:
        if order_last_daily_number['daily_number__max'] is not None:
            order_next_number = order_last_daily_number['daily_number__max'] + 1
        else:
            order_next_number = 1

    try:
        order = Order(open_time=datetime.datetime.now(), daily_number=order_next_number, is_paid=is_paid,
                      paid_with_cash=paid_with_cash)
    except:
        data = {
            'success': False,
            'message': 'Something wrong happened while creating new order!'
        }
        client.captureException()
        return JsonResponse(data)

    # cooks = Staff.objects.filter(user__last_login__contains=datetime.date.today(), staff_category__title__iexact='Cook')
    try:
        cooks = Staff.objects.filter(available=True, staff_category__title__iexact='Cook')
    except:
        data = {
            'success': False,
            'message': 'Something wrong happened while getting set of cooks!'
        }
        client.captureException()
        return JsonResponse(data)
    # reordering_flag = False
    # while
    # cooks_order_content = OrderContent.objects.filter(order__prepared_by=cooks,
    #                                                   order__open_time__contains=datetime.date.today(),
    #                                                   order__is_canceled=False, order__close_time__isnull=True)

    data = {
        "daily_number": order.daily_number
    }

    if len(cooks) == 0:
        data = {
            'success': False,
            'message': 'Нет доступных поваров!'
        }
        return JsonResponse(data)

    has_cook_content = False
    for item in content:
        menu_item = Menu.objects.get(id=item['id'])
        if menu_item.can_be_prepared_by.title == 'Cook':
            has_cook_content = True

    if has_cook_content:
        if cook_choose == 'auto':
            min_index = 0
            min_count = 100
            for cook_index in range(0, len(cooks)):
                try:
                    cooks_order_content = OrderContent.objects.filter(order__prepared_by=cooks[cook_index],
                                                                      order__open_time__contains=datetime.date.today(),
                                                                      order__is_canceled=False,
                                                                      order__close_time__isnull=True,
                                                                      menu_item__can_be_prepared_by__title__iexact='Cook')
                except:
                    data = {
                        'success': False,
                        'message': 'Something wrong happened while getting cook\'s content!'
                    }
                    return JsonResponse(data)

                if min_count > len(cooks_order_content):
                    min_count = len(cooks_order_content)
                    min_index = cook_index

            order.prepared_by = cooks[min_index]
        else:
            try:
                order.prepared_by = Staff.objects.get(id=int(cook_choose))
            except MultipleObjectsReturned:
                data = {
                    'success': False,
                    'message': 'Multiple staff returned while binding cook to order!'
                }
                client.captureException()
                return JsonResponse(data)
            except:
                data = {
                    'success': False,
                    'message': 'Something wrong happened while getting set of orders!'
                }
                client.captureException()
                return JsonResponse(data)

    content_to_send = []
    order.servery = servery
    order.save()

    total = 0
    content_presence = False
    shashlyk_presence = False
    supplement_presence = False
    for item in content:
        for i in range(0, int(item['quantity'])):
            try:
                new_order_content = OrderContent(order=order, menu_item_id=item['id'], note=item['note'])
            except:
                order.delete()
                data = {
                    'success': False,
                    'message': 'Something wrong happened while creating new order!'
                }
                client.captureException()
                return JsonResponse(data)
            new_order_content.save()
            menu_item = Menu.objects.get(id=item['id'])
            if menu_item.can_be_prepared_by.title == 'Cook':
                content_presence = True
            if menu_item.can_be_prepared_by.title == 'Shashlychnik':
                shashlyk_presence = True
            if menu_item.can_be_prepared_by.title == 'Operator':
                supplement_presence = True
            total += menu_item.price

        content_to_send.append(
            {
                'item_id': item['id'],
                'quantity': item['quantity']
            }
        )

    order.total = total
    order.content_completed = not content_presence
    order.shashlyk_completed = not shashlyk_presence
    order.supplement_completed = not supplement_presence
    order.save()
    if order.is_paid:
        print("Sending request to " + order.servery.ip_address)
        print(order)
        if FORCE_TO_LISTNER:
            send_order_to_listner(order)
        else:
            if not send_order_to_1c(order, False):
                send_order_to_listner(order)

        print("Request sent.")
    data["success"] = True
    data["total"] = order.total
    data["content"] = json.dumps(content_to_send)
    data["message"] = ''
    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.change_order')
def close_order(request):
    order_id = json.loads(request.POST.get('order_id', None))
    try:
        order = Order.objects.get(id=order_id)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске заказа!'
        }
        client.captureException()
        return JsonResponse(data)
    order.close_time = datetime.datetime.now()
    order.is_ready = True
    order.save()
    data = {
        'success': True,
        'received': 'Order №{} is closed.'.format(order.daily_number)
    }

    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.change_order')
def cancel_order(request):
    order_id = request.POST.get('id', None)
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске заказа!'
            }
            client.captureException()
            return JsonResponse(data)

        try:
            order.canceled_by = Staff.objects.get(user=request.user)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске персонала!'
            }
            client.captureException()
            return JsonResponse(data)
        order.is_canceled = True
        order.save()
        data = {
            'success': True
        }
    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.can_cook')
def next_to_prepare(request):
    user = request.user
    user_avg_prep_duration = OrderContent.objects.filter(staff_maker__user=user, start_timestamp__isnull=False,
                                                         finish_timestamp__isnull=False).values(
        'menu_item__id').annotate(
        production_duration=Avg(F('finish_timestamp') - F('start_timestamp'))).order_by('production_duration')

    available_cook_count = Staff.objects.filter(user__last_login__contains=datetime.date.today(),
                                                staff_category__title__iexact='cook').aggregate(
        Count('id'))  # Change to logged.

    free_content = OrderContent.objects.filter(order__open_time__contains=datetime.date.today(),
                                               order__close_time__isnull=True,
                                               order__is_canceled=False,
                                               menu_item__can_be_prepared_by__title__iexact='cook',
                                               start_timestamp__isnull=True).order_by(
        'order__open_time')[:available_cook_count['id__count']]

    in_progress_content = OrderContent.objects.filter(order__open_time__contains=datetime.date.today(),
                                                      order__close_time__isnull=True,
                                                      order__is_canceled=False,
                                                      start_timestamp__isnull=False,
                                                      finish_timestamp__isnull=True,
                                                      staff_maker__user=user,
                                                      is_in_grill=False,
                                                      is_canceled=False).order_by(
        'order__open_time')[:1]

    if len(free_content) > 0:
        if len(in_progress_content) == 0:
            free_content_ids = [content.id for content in free_content]
            id_to_prepare = -1
            for product in user_avg_prep_duration:
                if product['menu_item__id'] in free_content_ids:
                    id_to_prepare = product['menu_item__id']
                    break

            if id_to_prepare == -1:
                id_to_prepare = free_content_ids[0]

            context = {
                'next_product': OrderContent.objects.get(id=id_to_prepare),
                'in_progress': None,
                'current_time': datetime.datetime.now(),
                'staff_category': StaffCategory.objects.get(staff__user=request.user),
            }
        else:
            context = {
                'next_product': None,
                'in_progress': in_progress_content[0],
                'current_time': datetime.datetime.now(),
                'staff_category': StaffCategory.objects.get(staff__user=request.user),
            }
    else:
        if len(in_progress_content) != 0:
            context = {
                'next_product': None,
                'in_progress': in_progress_content[0],
                'current_time': datetime.datetime.now(),
                'staff_category': StaffCategory.objects.get(staff__user=request.user),

            }
        else:
            context = {
                'next_product': None,
                'in_progress': None,
                'current_time': datetime.datetime.now(),
                'staff_category': StaffCategory.objects.get(staff__user=request.user),
            }

    template = loader.get_template('shaw_queue/next_to_prepare_ajax.html')
    data = {
        'html': template.render(context, request)
    }
    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.can_cook')
def take(request):
    # print 'Trying to take 1.'
    product_id = request.POST.get('id', None)
    # print request.POST
    data = {
        'success': json.dumps(False)
    }
    if product_id:
        product = OrderContent.objects.get(id=product_id)
        if product.staff_maker is None:
            staff_maker = Staff.objects.get(user=request.user)
            product.staff_maker = staff_maker
            product.start_timestamp = datetime.datetime.now()
            product.save()
            data = {
                'success': json.dumps(True)
            }
        else:
            data = {
                'success': json.dumps(False),
                'staff_maker': 'TEST_MAKER'
            }
    # print 'Trying to take 2.'

    return JsonResponse(data)


# @login_required()
# @permission_required('shaw_queue.can_cook')
def to_grill(request):
    product_id = request.POST.get('id', None)
    if product_id:
        product = OrderContent.objects.get(pk=product_id)
        product.grill_timestamp = datetime.datetime.now()
        product.is_in_grill = True
        if product.staff_maker is None:
            staff_maker = Staff.objects.get(user=request.user)
            product.staff_maker = staff_maker
            product.start_timestamp = datetime.datetime.now()
        product.save()
        order_content = OrderContent.objects.filter(order_id=product.order_id)

        shashlychnik_products = OrderContent.objects.filter(order=product.order,
                                                            menu_item__can_be_prepared_by__title__iexact='Shashlychnik')
        cook_products = OrderContent.objects.filter(order=product.order,
                                                    menu_item__can_be_prepared_by__title__iexact='Cook')

        # Check if all shashlyk is frying.
        shashlyk_is_grilling = True
        for product in shashlychnik_products:
            if not product.is_in_grill:
                shashlyk_is_grilling = False

        product.order.is_grilling_shash = shashlyk_is_grilling

        # Check if all shawarma is frying.
        content_is_grilling = True
        for product in cook_products:
            if not product.is_in_grill:
                content_is_grilling = False

        product.order.is_grilling = content_is_grilling
        if content_is_grilling or shashlyk_is_grilling:
            product.order.save()
    data = {
        'success': True,
        'product_id': product_id,
        'staff_maker': '{} {}'.format(request.user.first_name, request.user.last_name)
    }

    return JsonResponse(data)


@login_required()
def grill_timer(request):
    grilling = OrderContent.objects.filter(order__open_time__contains=datetime.date.today(),
                                           order__close_time__isnull=True,
                                           order__is_canceled=False,
                                           start_timestamp__isnull=False,
                                           finish_timestamp__isnull=True,
                                           staff_maker__user=request.user,
                                           is_in_grill=True,
                                           is_canceled=False)
    template = loader.get_template('shaw_queue/grill_slot_ajax.html')
    tzinfo = datetime.tzinfo(tzname=TIME_ZONE)
    context = {
        'in_grill': [{'time': str(datetime.datetime.now().replace(tzinfo=tzinfo) - product.grill_timestamp.replace(
            tzinfo=tzinfo))[:-str(datetime.datetime.now().replace(tzinfo=tzinfo) - product.grill_timestamp.replace(
            tzinfo=tzinfo)).find('.')],
                      'product': product} for product in grilling]
    }
    data = {
        'html': template.render(context, request)
    }
    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.can_cook')
def finish_cooking(request):
    product_id = request.POST.get('id', None)
    if product_id:
        product = OrderContent.objects.get(pk=product_id)
        product.is_in_grill = False
        product.finish_timestamp = datetime.datetime.now()
        product.save()
        order_content = OrderContent.objects.filter(order_id=product.order_id)

        shashlychnik_products = OrderContent.objects.filter(order=product.order,
                                                            menu_item__can_be_prepared_by__title__iexact='Shashlychnik')
        cook_products = OrderContent.objects.filter(order=product.order,
                                                    menu_item__can_be_prepared_by__title__iexact='Cook')

        # Check if all shashlyk is frying.
        shashlyk_is_finished = True
        for product in shashlychnik_products:
            if product.finish_timestamp is None:
                shashlyk_is_finished = False

        product.order.shashlyk_completed = shashlyk_is_finished

        # Check if all shawarma is frying.
        content_is_finished = True
        for product in cook_products:
            if product.finish_timestamp is None:
                content_is_finished = False

        product.order.content_completed = content_is_finished

        if content_is_finished or shashlyk_is_finished:
            product.order.save()

        data = {
            'success': True,
            'product_id': product_id,
            'order_number': product.order.daily_number,
            'staff_maker': '{} {}'.format(request.user.first_name, request.user.last_name)
        }
    else:
        data = {
            'success': False,
            'product_id': product_id,
            'staff_maker': '{} {}'.format(request.user.first_name, request.user.last_name)
        }

    return JsonResponse(data)


# @login_required()
# @permission_required('shaw_queue.can_cook')
def finish_all_content(request):
    user = request.user
    staff = Staff.objects.get(user=user)
    order_id = request.POST.get('id', None)
    if order_id:
        order = Order.objects.get(id=order_id)
        shashlychnik_products = OrderContent.objects.filter(order=order,
                                                            menu_item__can_be_prepared_by__title__iexact='Shashlychnik')
        cook_products = OrderContent.objects.filter(order=order,
                                                    menu_item__can_be_prepared_by__title__iexact='Cook')
        products = OrderContent.objects.filter(order=order,
                                               menu_item__can_be_prepared_by__title__iexact=staff.staff_category.title)
        for product in products:
            product.is_in_grill = False
            product.finish_timestamp = datetime.datetime.now()
            if product.start_timestamp is None:
                product.start_timestamp = datetime.datetime.now()
            if product.staff_maker is None:
                product.staff_maker = Staff.objects.get(user=request.user)
            product.save()

        # Check if all shashlyk is frying.
        shashlyk_is_finished = True
        for product in shashlychnik_products:
            if product.finish_timestamp is None:
                shashlyk_is_finished = False

        order.shashlyk_completed = shashlyk_is_finished

        # Check if all shawarma is frying.
        content_is_finished = True
        for product in cook_products:
            if product.finish_timestamp is None:
                content_is_finished = False

        order.content_completed = content_is_finished
        # print "saving"
        order.save()
        data = {
            'success': True
        }
    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


# @login_required()
# @permission_required('shaw_queue.can_cook')
def grill_all_content(request):
    user = request.user
    staff = Staff.objects.get(user=user)
    order_id = request.POST.get('order_id', None)
    if order_id:
        order = Order.objects.get(id=order_id)
        shashlychnik_products = OrderContent.objects.filter(order=order,
                                                            menu_item__can_be_prepared_by__title__iexact='Shashlychnik')
        cook_products = OrderContent.objects.filter(order=order,
                                                    menu_item__can_be_prepared_by__title__iexact='Cook')
        products = OrderContent.objects.filter(order=order,
                                               menu_item__can_be_prepared_by__title__iexact=staff.staff_category.title)
        for product in products:
            product.start_timestamp = datetime.datetime.now()
            product.grill_timestamp = datetime.datetime.now()
            product.is_in_grill = True
            product.staff_maker = Staff.objects.get(user=request.user)
            product.save()

        # Check if all shashlyk is frying.
        all_is_grilling = True
        for product in shashlychnik_products:
            if not product.is_in_grill:
                all_is_grilling = False

        order.is_grilling_shash = all_is_grilling

        # Check if all shawarma is frying.
        all_is_grilling = True
        for product in cook_products:
            if not product.is_in_grill:
                all_is_grilling = False

        order.is_grilling = all_is_grilling
        # print "saving"
        order.save()
        data = {
            'success': True
        }
    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.can_cook')
def finish_supplement(request):
    product_id = request.POST.get('id', None)
    if product_id:
        product = OrderContent.objects.get(id=product_id)
        product.start_timestamp = datetime.datetime.now()
        product.finish_timestamp = datetime.datetime.now()
        product.staff_maker = Staff.objects.get(user=request.user)
        product.save()
        order_content = OrderContent.objects.filter(order_id=product.order_id)
        flag = True
        for item in order_content:
            if item.finish_timestamp is None:
                flag = False
        if flag:
            product.order.supplement_completed = True
            product.order.save()

        data = {
            'success': True,
            'product_id': product_id,
            'staff_maker': '{} {}'.format(request.user.first_name, request.user.last_name)
        }
    else:
        data = {
            'success': False,
            'product_id': product_id,
            'staff_maker': '{} {}'.format(request.user.first_name, request.user.last_name)
        }

    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.change_order')
def ready_order(request):
    order_id = request.POST.get('id', None)
    servery_choose = request.POST.get('servery_choose', None)
    if order_id:
        order = Order.objects.get(id=order_id)
        order.supplement_completed = True
        order.is_ready = True
        check_auto = servery_choose == 'auto' or servery_choose is None
        if not check_auto:
            servery = Servery.objects.get(id=servery_choose)
            order.servery = servery

        order.save()
        data = {
            'success': True
        }
    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.change_order')
def pay_order(request):
    order_id = request.POST.get('id', None)
    ids = json.loads(request.POST.get('ids', None))
    values = json.loads(request.POST.get('values', None))
    paid_with_cash = json.loads(request.POST['paid_with_cash'])
    if order_id:
        for index, item_id in enumerate(ids):
            try:
                item = OrderContent.objects.get(id=item_id)
            except:
                data = {
                    'success': False,
                    'message': 'Что-то пошло не так при поиске продуктов!'
                }
                return JsonResponse(data)
            item.quantity = float(values[index])
            item.save()

        try:
            order = Order.objects.get(id=order_id)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске заказа!'
            }
            return JsonResponse(data)
        order.is_paid = True
        order.paid_with_cash = paid_with_cash

        total = 0
        content_presence = False
        supplement_presence = False
        try:
            content = OrderContent.objects.filter(order=order)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске продуктов!'
            }
            return JsonResponse(data)
        for item in content:
            menu_item = item.menu_item
            if menu_item.can_be_prepared_by.title == 'Cook':
                content_presence = True
            if menu_item.can_be_prepared_by.title == 'Operator':
                supplement_presence = True
            total += menu_item.price * item.quantity
        order.total = total
        # order.supplement_completed = not supplement_presence
        # order.content_completed = not content_presence
        order.save()
        print("Sending request to " + order.servery.ip_address)
        # print order
        requests.post('http://' + order.servery.ip_address + ':' + LISTNER_PORT, json=prepare_json_check(order))
        print("Request sent.")
        data = {
            'success': True
        }
    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.change_order')
def cancel_item(request):
    product_id = request.POST.get('id', None)
    if product_id:
        try:
            item = OrderContent.objects.get(id=product_id)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске продуктов!'
            }
            return JsonResponse(data)
        item.canceled_by = request.user
        item.is_canceled = True
        item.save()
        data = {
            'success': True
        }
    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


@login_required()
def statistic_page(request):
    template = loader.get_template('shaw_queue/statistics.html')
    avg_preparation_time = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=False,
                                                is_canceled=False).values(
        'open_time', 'close_time').aggregate(preparation_time=Avg(F('close_time') - F('open_time')))
    min_preparation_time = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=False,
                                                is_canceled=False).values(
        'open_time', 'close_time').aggregate(preparation_time=Min(F('close_time') - F('open_time')))
    max_preparation_time = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=False,
                                                is_canceled=False).values(
        'open_time', 'close_time').aggregate(preparation_time=Max(F('close_time') - F('open_time')))
    context = {
        'total_orders': len(Order.objects.filter(open_time__contains=datetime.date.today())),
        'canceled_orders': len(
            Order.objects.filter(open_time__contains=datetime.date.today(), is_canceled__isnull=True)),
        'avg_prep_time': str(avg_preparation_time['preparation_time']).split('.', 2)[0],
        'min_prep_time': str(min_preparation_time['preparation_time']).split('.', 2)[0],
        'max_prep_time': str(max_preparation_time['preparation_time']).split('.', 2)[0],
        'cooks': [{'person': cook,
                   'prepared_orders_count': len(
                       Order.objects.filter(prepared_by=cook, open_time__contains=datetime.date.today(),
                                            close_time__isnull=False, is_canceled=False)),
                   'prepared_products_count': len(OrderContent.objects.filter(order__prepared_by=cook,
                                                                              order__open_time__contains=datetime.date.today(),
                                                                              order__close_time__isnull=False,
                                                                              order__is_canceled=False,
                                                                              menu_item__can_be_prepared_by__title__iexact='Cook')),
                   'avg_prep_time': str(
                       Order.objects.filter(prepared_by=cook, open_time__contains=datetime.date.today(),
                                            close_time__isnull=False, is_canceled=False).values(
                           'open_time', 'close_time').aggregate(preparation_time=Avg(F('close_time') - F('open_time')))[
                           'preparation_time']).split('.', 2)[0],
                   'min_prep_time': str(
                       Order.objects.filter(prepared_by=cook, open_time__contains=datetime.date.today(),
                                            close_time__isnull=False, is_canceled=False).values(
                           'open_time', 'close_time').aggregate(preparation_time=Min(F('close_time') - F('open_time')))[
                           'preparation_time']).split('.', 2)[0],
                   'max_prep_time': str(
                       Order.objects.filter(prepared_by=cook, open_time__contains=datetime.date.today(),
                                            close_time__isnull=False, is_canceled=False).values(
                           'open_time', 'close_time').aggregate(preparation_time=Max(F('close_time') - F('open_time')))[
                           'preparation_time']).split('.', 2)[0]
                   }
                  for cook in Staff.objects.filter(staff_category__title__iexact='Cook').order_by('user__first_name')]
    }
    return HttpResponse(template.render(context, request))


@login_required()
def statistic_page_ajax(request):
    start_date = request.POST.get('start_date', None)
    start_date_conv = datetime.datetime.strptime(start_date, "%Y/%m/%d %H:%M")  # u'2018/01/04 22:31'
    end_date = request.POST.get('end_date', None)
    end_date_conv = datetime.datetime.strptime(end_date, "%Y/%m/%d %H:%M")  # u'2018/01/04 22:31'
    template = loader.get_template('shaw_queue/statistics_ajax.html')
    try:
        avg_preparation_time = Order.objects.filter(open_time__gte=start_date_conv, open_time__lte=end_date_conv,
                                                    close_time__isnull=False, is_canceled=False).values(
            'open_time', 'close_time').aggregate(preparation_time=Avg(F('close_time') - F('open_time')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении среднего времени готовки!'
        }
        return JsonResponse(data)

    try:
        min_preparation_time = Order.objects.filter(open_time__gte=start_date_conv, open_time__lte=end_date_conv,
                                                    close_time__isnull=False, is_canceled=False).values(
            'open_time', 'close_time').aggregate(preparation_time=Min(F('close_time') - F('open_time')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении минимального времени готовки!'
        }
        return JsonResponse(data)

    try:
        max_preparation_time = Order.objects.filter(open_time__gte=start_date_conv, open_time__lte=end_date_conv,
                                                    close_time__isnull=False, is_canceled=False).values(
            'open_time', 'close_time').aggregate(preparation_time=Max(F('close_time') - F('open_time')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении максимального времени готовки!'
        }
        return JsonResponse(data)

    try:
        context = {
            'total_orders': len(Order.objects.filter(open_time__gte=start_date_conv, open_time__lte=end_date_conv)),
            'canceled_orders': len(
                Order.objects.filter(open_time__contains=datetime.date.today(), is_canceled__isnull=True)),
            'avg_prep_time': str(avg_preparation_time['preparation_time']).split('.', 2)[0],
            'min_prep_time': str(min_preparation_time['preparation_time']).split('.', 2)[0],
            'max_prep_time': str(max_preparation_time['preparation_time']).split('.', 2)[0],
            'cooks': [{'person': cook,
                       'prepared_orders_count': len(Order.objects.filter(prepared_by=cook,
                                                                         open_time__gte=start_date_conv,
                                                                         open_time__lte=end_date_conv,
                                                                         close_time__isnull=False, is_canceled=False)),
                       'prepared_products_count': len(OrderContent.objects.filter(order__prepared_by=cook,
                                                                                  order__open_time__gte=start_date_conv,
                                                                                  order__open_time__lte=end_date_conv,
                                                                                  order__close_time__isnull=False,
                                                                                  order__is_canceled=False,
                                                                                  menu_item__can_be_prepared_by__title__iexact='Cook')),
                       'avg_prep_time': str(Order.objects.filter(prepared_by=cook, open_time__gte=start_date_conv,
                                                                 open_time__lte=end_date_conv, close_time__isnull=False,
                                                                 is_canceled=False).values(
                           'open_time', 'close_time').aggregate(preparation_time=Avg(F('close_time') - F('open_time')))[
                                                'preparation_time']).split('.', 2)[0],
                       'min_prep_time': str(Order.objects.filter(prepared_by=cook, open_time__gte=start_date_conv,
                                                                 open_time__lte=end_date_conv, close_time__isnull=False,
                                                                 is_canceled=False).values(
                           'open_time', 'close_time').aggregate(preparation_time=Min(F('close_time') - F('open_time')))[
                                                'preparation_time']).split('.', 2)[0],
                       'max_prep_time': str(Order.objects.filter(prepared_by=cook, open_time__gte=start_date_conv,
                                                                 open_time__lte=end_date_conv, close_time__isnull=False,
                                                                 is_canceled=False).values(
                           'open_time', 'close_time').aggregate(preparation_time=Max(F('close_time') - F('open_time')))[
                                                'preparation_time']).split('.', 2)[0]
                       }
                      for cook in
                      Staff.objects.filter(staff_category__title__iexact='Cook').order_by('user__first_name')]
        }
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при подготовки шаблона!'
        }
        return JsonResponse(data)
    data = {
        'html': template.render(context, request)
    }
    return JsonResponse(data=data)


@login_required()
def opinion_statistics(request):
    template = loader.get_template('shaw_queue/opinion_statistics.html')
    avg_mark = OrderOpinion.objects.filter(post_time__contains=datetime.date.today()).values('mark').aggregate(
        avg_mark=Avg('mark'))
    min_mark = OrderOpinion.objects.filter(post_time__contains=datetime.date.today()).values('mark').aggregate(
        min_mark=Min('mark'))
    max_mark = OrderOpinion.objects.filter(post_time__contains=datetime.date.today()).values('mark').aggregate(
        max_mark=Max('mark'))
    context = {
        'total_orders': len(OrderOpinion.objects.filter(post_time__contains=datetime.date.today())),
        'avg_mark': avg_mark['avg_mark'],
        'min_mark': min_mark['min_mark'],
        'max_mark': max_mark['max_mark'],
        'opinions': [opinion for opinion in
                     OrderOpinion.objects.filter(post_time__contains=datetime.date.today()).order_by('post_time')]
    }
    return HttpResponse(template.render(context, request))


@login_required()
def opinion_statistics_ajax(request):
    start_date = request.POST.get('start_date', None)
    start_date_conv = datetime.datetime.strptime(start_date, "%Y/%m/%d %H:%M")  # u'2018/01/04 22:31'
    end_date = request.POST.get('end_date', None)
    end_date_conv = datetime.datetime.strptime(end_date, "%Y/%m/%d %H:%M")  # u'2018/01/04 22:31'
    template = loader.get_template('shaw_queue/opinion_statistics_ajax.html')
    try:
        avg_mark = OrderOpinion.objects.filter(post_time__gte=start_date_conv,
                                               post_time__lte=end_date_conv).values('mark').aggregate(
            avg_mark=Avg('mark'))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении средней оценки!'
        }
        client.captureException()
        return JsonResponse(data)

    try:
        min_mark = OrderOpinion.objects.filter(post_time__gte=start_date_conv,
                                               post_time__lte=end_date_conv).values('mark').aggregate(
            min_mark=Min('mark'))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении минимальной оценки!'
        }
        client.captureException()
        return JsonResponse(data)

    try:
        max_mark = OrderOpinion.objects.filter(post_time__gte=start_date_conv,
                                               post_time__lte=end_date_conv).values('mark').aggregate(
            max_mark=Max('mark'))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении максимальной оценки!'
        }
        return JsonResponse(data)

    try:
        context = {
            'total_orders': len(
                OrderOpinion.objects.filter(post_time__gte=start_date_conv, post_time__lte=end_date_conv)),
            'avg_mark': avg_mark['avg_mark'],
            'min_mark': min_mark['min_mark'],
            'max_mark': max_mark['max_mark'],
            'opinions': [opinion for opinion in
                         OrderOpinion.objects.filter(post_time__gte=start_date_conv,
                                                     post_time__lte=end_date_conv).order_by(
                             'order__open_time')]
        }
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при построении шаблона!'
        }
        client.captureException()
        return JsonResponse(data)

    data = {
        'html': template.render(context, request)
    }
    return JsonResponse(data=data)


@login_required()
def pause_statistic_page(request):
    template = loader.get_template('shaw_queue/pause_statistics.html')
    avg_duration_time = PauseTracker.objects.filter(start_timestamp__contains=datetime.date.today(),
                                                    end_timestamp__contains=datetime.date.today()).values(
        'start_timestamp', 'end_timestamp').aggregate(duration=Avg(F('end_timestamp') - F('start_timestamp')))
    min_duration_time = PauseTracker.objects.filter(start_timestamp__contains=datetime.date.today(),
                                                    end_timestamp__contains=datetime.date.today()).values(
        'start_timestamp', 'end_timestamp').aggregate(duration=Min(F('end_timestamp') - F('start_timestamp')))
    max_duration_time = PauseTracker.objects.filter(start_timestamp__contains=datetime.date.today(),
                                                    end_timestamp__contains=datetime.date.today()).values(
        'start_timestamp', 'end_timestamp').aggregate(duration=Max(F('end_timestamp') - F('start_timestamp')))
    context = {
        'total_pauses': len(PauseTracker.objects.filter(start_timestamp__contains=datetime.date.today(),
                                                        end_timestamp__contains=datetime.date.today())),
        'avg_duration': str(avg_duration_time['duration']).split('.', 2)[0],
        'min_duration': str(min_duration_time['duration']).split('.', 2)[0],
        'max_duration': str(max_duration_time['duration']).split('.', 2)[0],
        'pauses': [{
            'staff': pause.staff,
            'start_timestamp': str(pause.start_timestamp).split('.', 2)[0],
            'end_timestamp': str(pause.end_timestamp).split('.', 2)[0],
            'duration': str(pause.end_timestamp - pause.start_timestamp).split('.', 2)[0]
        }
            for pause in PauseTracker.objects.filter(start_timestamp__contains=datetime.date.today(),
                                                     end_timestamp__contains=datetime.date.today()).order_by(
                'start_timestamp')]
    }
    return HttpResponse(template.render(context, request))


@login_required()
def pause_statistic_page_ajax(request):
    start_date = request.POST.get('start_date', None)
    start_date_conv = datetime.datetime.strptime(start_date, "%Y/%m/%d %H:%M")  # u'2018/01/04 22:31'
    end_date = request.POST.get('end_date', None)
    end_date_conv = datetime.datetime.strptime(end_date, "%Y/%m/%d %H:%M")  # u'2018/01/04 22:31'
    template = loader.get_template('shaw_queue/pause_statistics_ajax.html')
    try:
        avg_duration_time = PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                        end_timestamp__lte=end_date_conv).values(
            'start_timestamp', 'end_timestamp').aggregate(duration=Avg(F('start_timestamp') - F('end_timestamp')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении средней продолжительности пауз!'
        }
        return JsonResponse(data)

    try:
        min_duration_time = PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                        end_timestamp__lte=end_date_conv).values(
            'start_timestamp', 'end_timestamp').aggregate(duration=Min(F('start_timestamp') - F('start_timestamp')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении минимальной продолжительности пауз!'
        }
        return JsonResponse(data)

    try:
        max_duration_time = PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                        end_timestamp__lte=end_date_conv).values(
            'start_timestamp', 'end_timestamp').aggregate(duration=Max(F('start_timestamp') - F('start_timestamp')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении максимальной продолжительности пауз!'
        }
        return JsonResponse(data)

    try:
        context = {
            'total_pauses': len(PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                            end_timestamp__lte=end_date_conv)),
            'avg_duration': str(avg_duration_time['duration']).split('.', 2)[0],
            'min_duration': str(min_duration_time['duration']).split('.', 2)[0],
            'max_duration': str(max_duration_time['duration']).split('.', 2)[0],
            'pauses': [{
                'staff': pause.staff,
                'start_timestamp': str(pause.start_timestamp).split('.', 2)[0],
                'end_timestamp': str(pause.end_timestamp).split('.', 2)[0],
                'duration': str(pause.end_timestamp - pause.start_timestamp).split('.', 2)[0]
            }
                for pause in PauseTracker.objects.filter(start_timestamp__contains=datetime.date.today(),
                                                         end_timestamp__contains=datetime.date.today()).order_by(
                    'start_timestamp')]
        }
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при построении шаблона!'
        }
        client.captureException()
        return JsonResponse(data)
    data = {
        'html': template.render(context, request)
    }
    return JsonResponse(data=data)


def prepare_json_check(order):
    aux_query = OrderContent.objects.filter(order=order).values('menu_item__title', 'menu_item__guid_1c',
                                                                'menu_item__price', 'order__paid_with_cash').annotate(
        total=Count('menu_item__title'))
    rows = []
    pay_rows = []
    number = 1
    sum = 0
    for item in aux_query:
        rows.append({
            "НомерСтроки": number,
            "КлючСвязи": number,
            "Количество": item['total'],
            "КоличествоУпаковок": item['total'],
            "НеобходимостьВводаАкцизнойМарки": False,
            "Номенклатура": {
                "TYPE": "СправочникСсылка.Номенклатура",
                "UID": item['menu_item__guid_1c']
            },
            "ПродажаПодарка": False,
            "РегистрацияПродажи": False,
            "Резервировать": False,
            "Склад": {
                "TYPE": "СправочникСсылка.Склады",
                "UID": "cc442ddc-767b-11e6-82c6-28c2dd30392b"
            },
            "СтавкаНДС": {
                "TYPE": "ПеречислениеСсылка.СтавкиНДС",
                "UID": "БезНДС"
            },
            "Сумма": item['menu_item__price'] * item['total'],
            "Цена": item['menu_item__price']
        })
        number += 1
        sum += item['menu_item__price'] * item['total']

    if order.prepared_by:
        cook_name = "{}".format(order.prepared_by.user.first_name)
    else:
        cook_name = ""
    order_number = str(order.daily_number % 100)

    print("Cash: {}".format(aux_query[0]['order__paid_with_cash']))
    if aux_query[0]['order__paid_with_cash']:
        pay_rows.append({
            "НомерСтроки": 1,
            "ВидОплаты": {
                "TYPE": "СправочникСсылка.ВидыОплатЧекаККМ",
                "UID": "5715e4bd-767b-11e6-82c6-28c2dd30392b"
            },
            "Сумма": sum,
            "ДанныеПереданыВБанк": False
        })
    else:
        pay_rows.append({
            "НомерСтроки": 1,
            "ВидОплаты": {
                "TYPE": "СправочникСсылка.ВидыОплатЧекаККМ",
                "UID": "8414dfc8-7683-11e6-8251-002215bf2d6a"
            },
            "ЭквайринговыйТерминал": {
                "TYPE": "СправочникСсылка.ЭквайринговыеТерминалы",
                "UID": "8414dfc9-7683-11e6-8251-002215bf2d6a"
            },
            "Сумма": sum,
            "ДанныеПереданыВБанк": False
        })

    aux_dict = {
        "OBJECT": True,
        "NEW": "Документы.ЧекККМ.СоздатьДокумент()",
        "SAVE": True,
        "Проведен": False,
        "Ссылка": {
            "TYPE": "ДокументСсылка.ЧекККМ",
            "UID": "0000-0000-0000-0000"
        },
        "ПометкаУдаления": False,
        "Дата": {
            "TYPE": "Дата",
            "UID": "ДДДДДД"
        },
        "Номер": "ЯЯЯЯЯЯ",
        "АналитикаХозяйственнойОперации": {
            "TYPE": "СправочникСсылка.АналитикаХозяйственныхОпераций",
            "UID": "5715e4c9-767b-11e6-82c6-28c2dd30392b"
        },
        "БонусыНачислены": False,
        "ВидОперации": {
            "TYPE": "ПеречислениеСсылка.ВидыОперацийЧекККМ",
            "UID": "Продажа"
        },
        "КассаККМ": {
            "TYPE": "СправочникСсылка.КассыККМ",
            "UID": "8414dfc5-7683-11e6-8251-002215bf2d6a"
        },
        "Магазин": {
            "TYPE": "СправочникСсылка.Магазины",
            "UID": "cc442ddb-767b-11e6-82c6-28c2dd30392b"
        },
        "НомерЧекаККМ": None,
        "Организация": {
            "TYPE": "СправочникСсылка.Организации",
            "UID": "1d68a28e-767b-11e6-82c6-28c2dd30392b"
        },
        "Ответственный": {
            "TYPE": "СправочникСсылка.Пользователи",
            "UID": "1d68a28d-767b-11e6-82c6-28c2dd30392b"
        },
        "ОтработанПереход": False,
        "СкидкиРассчитаны": True,
        "СуммаДокумента": sum,
        "ЦенаВключаетНДС": False,
        "ОперацияСДенежнымиСредствами": False,
        "Товары": {
            "TYPE": "ТаблицаЗначений",
            "COLUMNS": {
                "НомерСтроки": None,
                "ЗаказПокупателя": None,
                "КлючСвязи": None,
                "КлючСвязиСерийныхНомеров": None,
                "КодСтроки": None,
                "Количество": None,
                "КоличествоУпаковок": None,
                "НеобходимостьВводаАкцизнойМарки": None,
                "Номенклатура": None,
                "Продавец": None,
                "ПродажаПодарка": None,
                "ПроцентАвтоматическойСкидки": None,
                "ПроцентРучнойСкидки": None,
                "РегистрацияПродажи": None,
                "Резервировать": None,
                "Склад": None,
                "СтавкаНДС": None,
                "СтатусУказанияСерий": None,
                "Сумма": None,
                "СуммаАвтоматическойСкидки": None,
                "СуммаНДС": None,
                "СуммаРучнойСкидки": None,
                "СуммаСкидкиОплатыБонусом": None,
                "Упаковка": None,
                "Характеристика": None,
                "Цена": None,
                "Штрихкод": None
            },
            "ROWS": rows
        },
        "Оплата": {
            "TYPE": "ТаблицаЗначений",
            "COLUMNS": {
                "НомерСтроки": None,
                "ВидОплаты": None,
                "ЭквайринговыйТерминал": None,
                "Сумма": None,
                "ПроцентКомиссии": None,
                "СуммаКомиссии": None,
                "СсылочныйНомер": None,
                "НомерЧекаЭТ": None,
                "НомерПлатежнойКарты": None,
                "ДанныеПереданыВБанк": None,
                "СуммаБонусовВСкидках": None,
                "КоличествоБонусов": None,
                "КоличествоБонусовВСкидках": None,
                "БонуснаяПрограммаЛояльности": None,
                "ДоговорПлатежногоАгента": None,
                "КлючСвязиОплаты": None
            },
            "ROWS": pay_rows
        },
        "Повар": cook_name,
        "НомерОчереди": order_number
    }
    print("JSON formed!")
    return json.dumps(aux_dict, ensure_ascii=False)


def get_1c_menu(request):
    try:
        result = requests.get('http://' + SERVER_1C_IP + ':' + SERVER_1C_PORT + GETLIST_URL,
                              auth=(SERVER_1C_USER.encode('utf8'), SERVER_1C_PASS))
    except ConnectionError:
        data = {
            'success': False,
            'message': 'Connection error occured while sending to 1C!'
        }
        client.captureException()
        return JsonResponse(data)
    except:
        data = {
            'success': False,
            'message': 'Something wrong happened while sending to 1C!'
        }
        print("Unexpected error:", sys.exc_info()[0])
        client.captureException()
        raise
        return JsonResponse(data)

    json_data = result.json()
    data = json_data
    undistributed_category = MenuCategory.objects.get(eng_title="Undistributed")
    can_be_prepared = StaffCategory.objects.get(title="Operator")
    for item in data["Goods"]:
        menu_item = Menu.objects.filter(guid_1c=item["GUID"])
        if len(menu_item) > 0:
            menu_item[0].price = item["Price"]
            menu_item[0].save()
        else:

            menu_item = Menu(guid_1c=item["GUID"], price=item["Price"], title=item["Name"],
                             category=undistributed_category, avg_preparation_time=datetime.timedelta(minutes=1),
                             can_be_prepared_by=can_be_prepared)
            menu_item.save()

    return HttpResponse()


def send_order_to_1c(order, is_return):
    order_dict = {
        'servery_number': order.servery.guid_1c,
        'cash': order.paid_with_cash,
        'cashless': not order.paid_with_cash,
        'internet_order': False,
        'queue_number': order.daily_number,
        'cook': order.prepared_by.user.first_name,
        'return_of_goods': is_return,
        'total': order.total,
        'Goods': []
    }
    curr_order_content = OrderContent.objects.filter(order=order)
    for item in curr_order_content:
        count = OrderContent.objects.filter(menu_item__guid_1c=item.menu_item.guid_1c, order=order).aggregate(count=Count('id'))[
            'count']
        order_dict['Goods'].append(
            {
                'Name': item.menu_item.title,
                'Count': count,
                'GUID': item.menu_item.guid_1c
            }
        )

    try:
        result = requests.post('http://' + SERVER_1C_IP + ':' + SERVER_1C_PORT + ORDER_URL,
                               auth=(SERVER_1C_USER.encode('utf8'), SERVER_1C_PASS),
                               json=order_dict)
    except ConnectionError:
        data = {
            'success': False,
            'message': 'Connection error occured while sending order data to 1C!'
        }
        client.captureException()
        return JsonResponse(data)
    except:
        data = {
            'success': False,
            'message': 'Something wrong happened while sending order data to 1C!'
        }
        client.captureException()
        return JsonResponse(data)

    if result.status_code == 200:
        order.sent_to_1c = True
        try:
            order.guid_1c = result.json()['GUID']
        except KeyError:
            data = {
                'success': False,
                'message': 'No order GUID in 1C response!'
            }
            client.captureException()
            return JsonResponse(data)

        order.save()
        return True
    else:
        if result.status_code == 400:
            return False
        if result.status_code == 399:
            return False


def send_order_to_listner(order):
    try:
        requests.post('http://' + order.servery.ip_address + ':' + LISTNER_PORT, json=prepare_json_check(order))
    except ConnectionError:
        order.delete()
        data = {
            'success': False,
            'message': 'Connection error occured while sending to 1C!'
        }
        client.captureException()
        return JsonResponse(data)
    except:
        order.delete()
        data = {
            'success': False,
            'message': 'Something wrong happened while sending to 1C!'
        }
        client.captureException()
        return JsonResponse(data)

    return True


def order_1c_payment(request):
    order_guid = request.POST.get('GUID', None)
    payment_result = request.POST.get('payment_result', None)
    order = Order.objects.get(guid_1c=order_guid)
    order.paid_in_1c = payment_result
    order.save()
    return HttpResponse()
