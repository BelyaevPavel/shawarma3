# -*- coding: utf-8 -*-
from django.core.files import temp
from django.http.response import HttpResponseRedirect

from .models import Menu, Order, Staff, StaffCategory, MenuCategory, OrderContent, Servery, OrderOpinion, PauseTracker, \
    ServicePoint, Printer, Customer, CallData, DiscountCard, Delivery, DeliveryOrder
from django.template import loader
from django.core.exceptions import EmptyResultSet, MultipleObjectsReturned, PermissionDenied, ObjectDoesNotExist, \
    ValidationError
from django.core.paginator import Paginator
from requests.exceptions import ConnectionError, ConnectTimeout, Timeout
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout, login, views as auth_views
from django.db.models import Max, Min, Count, Avg, F, Sum, Q, ExpressionWrapper, DateTimeField
from django.utils import timezone
from django.core.mail import send_mail
from threading import Thread
from hashlib import md5
from shawarma.settings import TIME_ZONE, LISTNER_URL, LISTNER_PORT, PRINTER_URL, SERVER_1C_PORT, SERVER_1C_IP, \
    GETLIST_URL, SERVER_1C_USER, SERVER_1C_PASS, ORDER_URL, FORCE_TO_LISTNER, DEBUG_SERVERY, RETURN_URL, \
    CAROUSEL_IMG_DIR, CAROUSEL_IMG_URL, SMTP_LOGIN, SMTP_PASSWORD, SMTP_FROM_ADDR, SMTP_TO_ADDR
from raven.contrib.django.raven_compat.models import client
from random import sample
from itertools import chain
import time
import requests
import datetime
import logging
import pytz
import json
import sys
import os
import subprocess

logger = logging.getLogger(__name__)
flag_marker = False
waiting_numbers = {}

from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic import ListView, DetailView
from django.views import View
from django.forms import modelformset_factory
from .forms import DeliveryForm, DeliveryOrderForm, IncomingCallForm, CustomerForm


class CustomerList(ListView):
    model = Customer


class CustomerDetailView(DetailView):
    model = Customer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


class CustomerCreate(CreateView):
    model = Customer
    fields = ['name', 'phone_number', 'email', 'note']


class CustomerUpdate(UpdateView):
    model = Customer
    fields = ['name', 'phone_number', 'email', 'note']


class CustomerDelete(DeleteView):
    model = Customer
    success_url = reverse_lazy('customer-list')


class DiscountCardList(ListView):
    model = DiscountCard


class DiscountCardView(DetailView):
    model = DiscountCard

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


class DiscountCardCreate(CreateView):
    model = DiscountCard
    fields = ['number', 'discount', 'guid_1c', 'customer']


class DiscountCardUpdate(UpdateView):
    model = DiscountCard
    fields = ['number', 'discount', 'guid_1c', 'customer']


class DiscountCardDelete(DeleteView):
    model = DiscountCard
    success_url = reverse_lazy('discount-card-list')


class DeliveryList(ListView):
    model = Delivery


# class DeliveryView(DetailView):
#     model = Delivery
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['now'] = timezone.now()
#         return context


class DeliveryCreate(CreateView):
    model = Delivery
    form_class = DeliveryForm


class DeliveryUpdate(UpdateView):
    model = Delivery
    form_class = DeliveryForm


class DeliveryDelete(DeleteView):
    model = Delivery
    success_url = reverse_lazy('delivery-list')


class DeliveryOrderList(ListView):
    model = DeliveryOrder


class DeliveryOrderView(DetailView):
    model = DeliveryOrder

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context


class DeliveryOrderCreate(CreateView):
    model = DeliveryOrder
    initial = {
        'obtain_timepoint': timezone.datetime.now()
    }
    # form_class = DeliveryOrderForm
    fields = '__all__'


class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    """

    def form_invalid(self, form):
        response = super(AjaxableResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        else:
            return response

    def form_valid(self, form):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super(AjaxableResponseMixin, self).form_valid(form)
        if self.request.is_ajax():
            data = {
                'pk': self.object.pk,
            }
            return JsonResponse(data)
        else:
            return response


class DeliveryOrderViewAJAX(AjaxableResponseMixin, CreateView):
    # model = DeliveryOrder
    # fields = '__all__'
    def get(self, request):
        delivery_order_pk = request.GET.get('delivery_order_pk', None)
        customer_pk = request.GET.get('customer_pk', None)
        delivery_pk = request.GET.get('delivery_pk', None)
        order_pk = request.GET.get('order_pk', None)
        customers = Customer.objects.all()
        initial_data = {}
        template = loader.get_template('shaw_queue/deliveryorder_form.html')
        if delivery_order_pk is not None:
            context = {
                'object_pk': delivery_order_pk,
                'form': DeliveryOrderForm(instance=DeliveryOrder.objects.get(pk=delivery_order_pk))
            }
        else:
            initial_data['obtain_timepoint'] = timezone.datetime.now()
            if customer_pk is not None:
                initial_data['customer'] = Customer.objects.get(pk=customer_pk)
            if delivery_pk is not None:
                initial_data['delivery'] = Delivery.objects.get(pk=delivery_pk)
            if order_pk is not None:
                initial_data['order'] = Order.objects.get(pk=order_pk)
            context = {
                'form': DeliveryOrderForm(initial=initial_data)
            }

        for field in context['form'].fields:
            context['form'].fields[field].widget.attrs['class'] = 'form-control'
            print(context['form'].fields[field].widget.attrs)
        data = {
            'success': True,
            'html': template.render(context, request)
        }
        return JsonResponse(data=data)

    def post(self, request):
        delivery_order_pk = request.POST.get('delivery_order_pk', None)
        if delivery_order_pk is not None:
            form = DeliveryOrderForm(request.POST, instance=DeliveryOrder.objects.get(pk=delivery_order_pk))
        else:
            form = DeliveryOrderForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            form.save()
            print("Is valid.")
            data = {
                'success': True
            }
            return JsonResponse(data)
        else:
            template = loader.get_template('shaw_queue/deliveryorder_form.html')

            context = {
                'form': form
            }
            for field in context['form'].fields:
                context['form'].fields[field].widget.attrs['class'] = 'form-control'
                errors = context['form'].errors.get(field, None)
                if errors is not None:
                    context['form'].fields[field].widget.attrs['class'] += ' is-invalid'
                else:
                    context['form'].fields[field].widget.attrs['class'] += ' is-valid'

                print(context['form'].fields[field].widget.attrs)
            data = {
                'success': False,
                'html': template.render(context, request)
            }
            return JsonResponse(data)
            # return HttpResponseRedirect(redirect_to='/shaw_queue/delivery_interface/')


class DeliveryOrderUpdate(UpdateView):
    model = DeliveryOrder
    fields = ['delivery', 'order', 'customer', 'obtain_timepoint', 'delivered_timepoint', 'prep_start_timepoint',
              'preparation_duration', 'delivery_duration', 'note']


class DeliveryOrderDelete(DeleteView):
    model = DeliveryOrder
    success_url = reverse_lazy('delivery-order-list')


class IncomingCall(View):
    def get(self, request):
        template = loader.get_template('shaw_queue/incoming_call.html')
        context = {
            'form': IncomingCallForm()
        }
        for field in context['form'].fields:
            context['form'].fields[field].widget.attrs['class'] = 'form-control'
            print(context['form'].fields[field].widget.attrs)
        data = {
            'success': True,
            'html': template.render(context, request)
        }

        return JsonResponse(data)

    def post(self, request):
        # TODO: Rework 'if' sequence
        customer_pk = request.POST.get('pk', 'None')
        phone_number = request.POST.get('phone_number', '')
        customer = None
        if phone_number != '':
            try:
                customer = Customer.objects.get(phone_number=phone_number)
            except MultipleObjectsReturned:
                client.captureException()
            except Customer.DoesNotExist:
                pass

            if customer is not None:
                form = CustomerForm(instance=customer)
            else:
                form = CustomerForm(request.POST)
        else:
            if customer_pk != 'None':
                try:
                    customer = Customer.objects.get(pk=customer_pk)
                except MultipleObjectsReturned:
                    client.captureException()
                except Customer.DoesNotExist:
                    pass

                if customer is not None:
                    form = CustomerForm(instance=customer)
                else:
                    form = CustomerForm(request.POST)
            else:
                form = CustomerForm(request.POST)

        if customer is not None:
            template = loader.get_template('shaw_queue/incoming_call.html')
            customer_orders = DeliveryOrder.objects.filter(customer=customer).order_by('-obtain_timepoint')[:3]

            context = {
                'customer_pk': customer.pk,
                'form': CustomerForm(instance=customer),
                'customer_orders': [
                    {
                        'delivery_order': delivery_order,
                        'content': OrderContent.objects.filter(order=delivery_order.order)
                    } for delivery_order in customer_orders
                    ]
            }
            for field in context['form'].fields:
                context['form'].fields[field].widget.attrs['class'] = 'form-control'
                errors = context['form'].errors.get(field, None)
                if errors is not None:
                    context['form'].fields[field].widget.attrs['class'] += ' is-invalid'
                else:
                    context['form'].fields[field].widget.attrs['class'] += ' is-valid'

                print(context['form'].fields[field].widget.attrs)
            data = {
                'success': True,
                'html': template.render(context, request)
            }
            return JsonResponse(data)

        else:
            if form.is_valid():
                form.save()
                template = loader.get_template('shaw_queue/incoming_call.html')
                customer = Customer.objects.get(phone_number=phone_number)
                context = {
                    'customer_pk': customer.pk,
                    'form': form
                }
                for field in context['form'].fields:
                    context['form'].fields[field].widget.attrs['class'] = 'form-control'
                    errors = context['form'].errors.get(field, None)
                    if errors is not None:
                        context['form'].fields[field].widget.attrs['class'] += ' is-invalid'
                    else:
                        context['form'].fields[field].widget.attrs['class'] += ' is-valid'

                    print(context['form'].fields[field].widget.attrs)
                data = {
                    'success': False,
                    'html': template.render(context, request)
                }
                return JsonResponse(data)
            else:
                template = loader.get_template('shaw_queue/incoming_call.html')

                context = {
                    'customer_pk': None,
                    'form': form
                }
                for field in context['form'].fields:
                    context['form'].fields[field].widget.attrs['class'] = 'form-control'
                    errors = context['form'].errors.get(field, None)
                    if errors is not None:
                        context['form'].fields[field].widget.attrs['class'] += ' is-invalid'
                    else:
                        context['form'].fields[field].widget.attrs['class'] += ' is-valid'

                    print(context['form'].fields[field].widget.attrs)
                data = {
                    'success': False,
                    'html': template.render(context, request)
                }
                return JsonResponse(data)


class DeliveryView(View):
    template = loader.get_template('shaw_queue/delivery_form.html')

    def get(self, request):
        context = {
            'form': DeliveryForm()
        }
        for field in context['form'].fields:
            context['form'].fields[field].widget.attrs['class'] = 'form-control'
            print(context['form'].fields[field].widget.attrs)
        data = {
            'success': True,
            'html': self.template.render(context, request)
        }

        return JsonResponse(data)

    def post(self, request):
        car_driver = request.POST.get('car_driver', None)
        delivery_pk = request.POST.get('delivery_pk', None)
        delivery = None
        if delivery_pk is not None:
            try:
                delivery = Delivery.objects.get(pk=delivery_pk)
            except Delivery.MultipleObjectsReturned:
                client.captureException()
            except Delivery.DoesNotExist:
                pass

            if delivery is not None:
                form = DeliveryForm(instance=delivery)
            else:
                form = DeliveryForm(request.POST)
        else:
            form = DeliveryForm(request.POST)

        if delivery is not None:
            delivery_orders = DeliveryOrder.objects.filter(delivery=delivery).order_by('-obtain_timepoint')[:3]

            context = {
                'customer_pk': delivery.pk,
                'form': DeliveryForm(instance=delivery),
                'delivery_orders': [
                    {
                        'delivery_order': delivery_order,
                        'content': OrderContent.objects.filter(order=delivery_order.order)
                    } for delivery_order in delivery_orders
                    ]
            }
            for field in context['form'].fields:
                context['form'].fields[field].widget.attrs['class'] = 'form-control'
                errors = context['form'].errors.get(field, None)
                if errors is not None:
                    context['form'].fields[field].widget.attrs['class'] += ' is-invalid'
                else:
                    context['form'].fields[field].widget.attrs['class'] += ' is-valid'

                print(context['form'].fields[field].widget.attrs)
            data = {
                'success': True,
                'html': self.template.render(context, request)
            }
            return JsonResponse(data)

        else:
            if form.is_valid():
                delivery = form.save(commit=False)
                try:
                    delivery_last_daily_number = Delivery.objects.filter(
                        creation_timepoint__contains=datetime.date.today()).aggregate(Max('daily_number'))
                except EmptyResultSet:
                    data = {
                        'success': False,
                        'message': 'Empty set of deliveries returned!'
                    }
                    client.captureException()
                    return JsonResponse(data)
                except:
                    data = {
                        'success': False,
                        'message': 'Something wrong happened while getting set of deliveries!'
                    }
                    client.captureException()
                    return JsonResponse(data)

                if delivery_last_daily_number:
                    if delivery_last_daily_number['daily_number__max'] is not None:
                        delivery_next_number = delivery_last_daily_number['daily_number__max'] + 1
                    else:
                        delivery_next_number = 1
                delivery.daily_number = delivery_next_number
                delivery.creation_timepoint = timezone.now()
                delivery.save()
                context = {
                    'object_pk': delivery.pk,
                    'form': form
                }
                for field in context['form'].fields:
                    context['form'].fields[field].widget.attrs['class'] = 'form-control'
                    errors = context['form'].errors.get(field, None)
                    if errors is not None:
                        context['form'].fields[field].widget.attrs['class'] += ' is-invalid'
                    else:
                        context['form'].fields[field].widget.attrs['class'] += ' is-valid'

                    print(context['form'].fields[field].widget.attrs)
                data = {
                    'success': True,
                    'html': self.template.render(context, request)
                }
                return JsonResponse(data)
            else:

                context = {
                    'object_pk': None,
                    'form': form
                }
                for field in context['form'].fields:
                    context['form'].fields[field].widget.attrs['class'] = 'form-control'
                    errors = context['form'].errors.get(field, None)
                    if errors is not None:
                        context['form'].fields[field].widget.attrs['class'] += ' is-invalid'
                    else:
                        context['form'].fields[field].widget.attrs['class'] += ' is-valid'

                    print(context['form'].fields[field].widget.attrs)
                data = {
                    'success': False,
                    'html': self.template.render(context, request)
                }
                return JsonResponse(data)


def ats_listner(request):
    tel = request.GET.get('queue_id', None)
    caller_id = request.GET.get('caller_id', None)
    call_uid = request.GET.get('uid', None)
    operator_id = request.GET.get('operator_id', None)
    event_code = request.GET.get('event_code', None)  # 1 - from_queue, 2 - accept_call, 3 - discarb_call
    print("{} {} {} {} {}".format(tel, caller_id, call_uid, operator_id, event_code))
    if event_code is not None:
        try:
            event_code = int(event_code)
        except ValueError:
            logger.error('Неправильный код события {}!'.format(event_code))
            return HttpResponse('Wrong event code provided.')
        except:
            logger.error('Неправильный код события {}!'.format(event_code))
            client.captureException()
            return HttpResponse('Wrong event code provided.')

    if event_code < 1 and event_code > 3:
        return HttpResponse('Wrong event code provided.')

    if tel is not None and caller_id is not None and call_uid is not None and operator_id is not None and event_code is not None:
        try:
            customer = Customer.objects.get(phone_number=caller_id)
        except Customer.DoesNotExist:
            if event_code == 1:
                customer = Customer(phone_number=caller_id)
                customer.save()
            else:
                return HttpResponse('Failed to find customer.')

        try:
            call_manager = Staff.objects.get(pk=operator_id)
        except Staff.DoesNotExist:
            return HttpResponse('Failed to find call manager.')

        if event_code == 2 or event_code == 3:
            try:
                call_data = CallData.objects.get(ats_id=call_uid)
            except CallData.DoesNotExist:
                client.captureException()
                logger.error('Failed to find call data for uid {}!'.format(call_uid))
                return HttpResponse('Failed to find call data.')
            except CallData.MultipleObjectsReturned:
                client.captureException()
                logger.error('Multiple call records returned for uid {}!'.format(call_uid))
                return HttpResponse('Multiple call records returned.')
            except:
                client.captureException()
                logger.error('Something wrong happened while searching call data for uid {}!'.format(call_uid))
                return HttpResponse('Something wrong happened while searching call data.')

            call_data.accepted = True
        else:
            call_data = CallData(ats_id=call_uid, timepoint=datetime.datetime.now(), customer=customer,
                                 call_manager=call_manager)

        try:
            call_data.full_clean()
        except ValidationError as e:
            client.captureException()
            exception_messages = ""
            for message in e.messages:
                exception_messages += message
                logger.error('Call data has not pass validation: {}'.format(message))
            return HttpResponse('Call data has not pass validation: {}'.format(exception_messages))

        call_data.save()
        return HttpResponse('Success')
    else:
        return HttpResponse('Fail')


@login_required()
def check_incoming_calls(request):
    call_manager = Staff.objects.get(user=request.user)
    last_call = CallData.objects.filter(call_manager=call_manager, accepted=False,
                                        timepoint__contains=datetime.date.today()).order_by('timepoint').last()
    if last_call is not None:
        data = {
            'success': True,
            'caller_pk': last_call.customer.pk
        }
        return JsonResponse(data)
    else:
        data = {
            'success': False
        }
        return JsonResponse(data)


@login_required()
def redirection(request):
    staff_category = StaffCategory.objects.get(staff__user=request.user)
    if staff_category.title == 'Cook':
        return HttpResponseRedirect('cook_interface')
    if staff_category.title == 'Cashier':
        return HttpResponseRedirect('menu')
    if staff_category.title == 'Operator':
        return HttpResponseRedirect('current_queue')
    # if staff_category.title == 'Administration':
    #     return HttpResponseRedirect('statistics')


def cook_pause(request):
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'
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
        staff.service_point = None
        staff.save()

        mail_subject = str(staff) + ' ушел на перерыв'
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
        result = define_service_point(device_ip)
        if result['success']:
            staff.service_point = result['service_point']
            staff.save()
        else:
            return JsonResponse(result)

        mail_subject = str(staff) + ' начал работать'

    Thread(target=send_email, args=(mail_subject, staff, device_ip)).start()
    # send_email(mail_subject, staff, device_ip)

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
    delivery_mode = json.loads(request.GET.get('delivery_mode', 'false'))
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'
    try:
        menu_items = Menu.objects.order_by('title')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске последней паузы!'
        }
        client.captureException()
        return JsonResponse(data)
    if delivery_mode:
        template = loader.get_template('shaw_queue/modal_menu_page.html')
    else:
        template = loader.get_template('shaw_queue/menu_page.html')
    result = define_service_point(device_ip)
    if result['success']:
        try:
            context = {
                'user': request.user,
                'available_cookers': Staff.objects.filter(available=True, staff_category__title__iexact='Cook',
                                                          service_point=result['service_point']),
                'staff_category': StaffCategory.objects.get(staff__user=request.user),
                'menu_items': menu_items,
                'menu_categories': MenuCategory.objects.order_by('weight'),
                'delivery_mode': delivery_mode
            }
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске генерации меню!'
            }
            client.captureException()
            return JsonResponse(data)
    else:
        return JsonResponse(result)

    if delivery_mode == False:
        context['is_modal'] = False
        return HttpResponse(template.render(context, request))
    else:
        context['is_modal'] = True
        data = {
            'success': True,
            'html': template.render(context, request)
        }
        return JsonResponse(data)


def search_comment(request):
    content_id = request.POST.get('id', '')
    comment_part = request.POST.get('note', '')
    data = {
        'html': ''
    }
    if len(comment_part) > 0:
        try:
            comments = OrderContent.objects.filter(note__icontains=comment_part).values('note').annotate(
                count=Count('note')).order_by('-count')[:5]
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
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'

    result = define_service_point(device_ip)
    if result['success']:
        try:
            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                               is_canceled=False, is_ready=False,
                                               servery__service_point=result['service_point']).order_by('open_time')
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
                                                is_canceled=False,
                                                servery__service_point=result['service_point']).order_by('open_time')
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске готовых заказов!'
            }
            client.captureException()
            return JsonResponse(data)
        try:
            carousel_images = [CAROUSEL_IMG_URL + name for name in os.listdir(CAROUSEL_IMG_DIR)]
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при загрузке изображений для карусели!'
            }
            client.captureException()
            return JsonResponse(data)
    else:
        return JsonResponse(result)
    context = {
        'open_orders': [{'servery': order.servery, 'daily_number': order.daily_number} for order in open_orders],
        'ready_orders': [{'servery': order.servery, 'daily_number': order.daily_number} for order in
                         ready_orders],
        'display_open_orders': [{'servery': order.servery.display_title, 'daily_number': order.daily_number % 100} for
                                order in
                                open_orders],
        'display_ready_orders': [{'servery': order.servery.display_title, 'daily_number': order.daily_number % 100} for
                                 order in
                                 ready_orders],
        'carousel_images': carousel_images
    }
    template = loader.get_template('shaw_queue/buyer_queue.html')
    return HttpResponse(template.render(context, request))


def buyer_queue_ajax(request):
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'

    result = define_service_point(device_ip)

    if result['success']:
        try:
            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                               is_canceled=False, is_ready=False,
                                               servery__service_point=result['service_point']).order_by('open_time')
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
                                                is_canceled=False,
                                                servery__service_point=result['service_point']).order_by('open_time')
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске готовых заказов!'
            }
            client.captureException()
            return JsonResponse(data)
    else:
        return JsonResponse(result)

    context = {
        'open_orders': [{'servery': order.servery, 'daily_number': order.daily_number} for order in open_orders],
        'ready_orders': [{'servery': order.servery, 'daily_number': order.daily_number} for order in
                         ready_orders],
        'display_open_orders': [{'servery': order.servery.display_title, 'daily_number': order.daily_number % 100} for
                                order in
                                open_orders],
        'display_ready_orders': [{'servery': order.servery.display_title, 'daily_number': order.daily_number % 100} for
                                 order in
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
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'

    shawarma_filter = True
    if request.COOKIES.get('with_shawarma', 'True') == 'False':
        shawarma_filter = False

    shashlyk_filter = True
    if request.COOKIES.get('with_shashlyk', 'True') == 'False':
        shashlyk_filter = False

    paid_filter = True
    if request.COOKIES.get('paid', 'True') == 'False':
        paid_filter = False

    not_paid_filter = True
    if request.COOKIES.get('not_paid', 'True') == 'False':
        not_paid_filter = False

    result = define_service_point(device_ip)
    if result['success']:
        current_day_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                                  is_canceled=False, is_ready=False,
                                                  servery__service_point=result['service_point']).order_by('open_time')
        serveries = Servery.objects.filter(service_point=result['service_point'])
        serveries_dict = {}
        for servery in serveries:
            serveries_dict['{}'.format(servery.id)] = True
            if request.COOKIES.get('servery_{}'.format(servery.id), 'True') == 'False':
                serveries_dict['{}'.format(servery.id)] = False
        try:
            if paid_filter:
                if not_paid_filter:
                    if shawarma_filter:
                        if shashlyk_filter:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                        else:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True,
                                                               with_shawarma=shawarma_filter,
                                                               with_shashlyk=shashlyk_filter,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                    else:
                        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                           close_time__isnull=True, with_shawarma=shawarma_filter,
                                                           with_shashlyk=shashlyk_filter,
                                                           is_canceled=False, is_ready=False,
                                                           servery__service_point=result['service_point']).order_by(
                            'open_time')
                else:
                    if shawarma_filter:
                        if shashlyk_filter:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True, is_paid=True,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                        else:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True, is_paid=True,
                                                               with_shawarma=shawarma_filter,
                                                               with_shashlyk=shashlyk_filter,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                    else:
                        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                           close_time__isnull=True, with_shawarma=shawarma_filter,
                                                           with_shashlyk=shashlyk_filter, is_paid=True,
                                                           is_canceled=False, is_ready=False,
                                                           servery__service_point=result['service_point']).order_by(
                            'open_time')
            else:
                if not_paid_filter:
                    if shawarma_filter:
                        if shashlyk_filter:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True, is_paid=False,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                        else:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True, is_paid=False,
                                                               with_shawarma=shawarma_filter,
                                                               with_shashlyk=shashlyk_filter,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                    else:
                        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                           close_time__isnull=True, with_shawarma=shawarma_filter,
                                                           with_shashlyk=shashlyk_filter, is_paid=False,
                                                           is_canceled=False, is_ready=False,
                                                           servery__service_point=result['service_point']).order_by(
                            'open_time')
                else:
                    open_orders = Order.objects.none()

            open_orders = filter_orders(current_day_orders, shawarma_filter, shashlyk_filter, paid_filter,
                                        not_paid_filter, serveries_dict)

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
                                                supplement_completed=True, is_ready=True,
                                                servery__service_point=result['service_point']).order_by('open_time')

            ready_orders = filter_orders(ready_orders, shawarma_filter, shashlyk_filter, paid_filter,
                                         not_paid_filter, serveries_dict)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске готовых заказов!'
            }
            client.captureException()
            return JsonResponse(data)
    else:
        return JsonResponse(result)

    # print open_orders
    # print ready_orders

    template = loader.get_template('shaw_queue/current_queue_grid.html')
    context = {
        'open_orders': [{'order': open_order,
                         'printed': open_order.printed,
                         'cook_part_ready_count': OrderContent.objects.filter(order=open_order,
                                                                              is_canceled=False).filter(
                             menu_item__can_be_prepared_by__title__iexact='cook').filter(
                             finish_timestamp__isnull=False).aggregate(count=Count('id')),
                         'cook_part_count': OrderContent.objects.filter(order=open_order, is_canceled=False).filter(
                             menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                         'shashlychnik_part_ready_count': OrderContent.objects.filter(order=open_order,
                                                                                      is_canceled=False).filter(
                             menu_item__can_be_prepared_by__title__iexact='shashlychnik').filter(
                             finish_timestamp__isnull=False).aggregate(count=Count('id')),
                         'shashlychnik_part_count': OrderContent.objects.filter(order=open_order,
                                                                                is_canceled=False).filter(
                             menu_item__can_be_prepared_by__title__iexact='shashlychnik').aggregate(count=Count('id')),
                         'operator_part': OrderContent.objects.filter(order=open_order, is_canceled=False).filter(
                             menu_item__can_be_prepared_by__title__iexact='operator').values('menu_item__title',
                                                                                             'note').annotate(
                             count_titles=Count('menu_item__title'))
                         } for open_order in open_orders],
        'ready_orders': [{'order': open_order,
                          'cook_part_ready_count': OrderContent.objects.filter(order=open_order,
                                                                               is_canceled=False).filter(
                              menu_item__can_be_prepared_by__title__iexact='cook').filter(
                              finish_timestamp__isnull=False).aggregate(count=Count('id')),
                          'cook_part_count': OrderContent.objects.filter(order=open_order, is_canceled=False).filter(
                              menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                          'shashlychnik_part_ready_count': OrderContent.objects.filter(order=open_order,
                                                                                       is_canceled=False).filter(
                              menu_item__can_be_prepared_by__title__iexact='shashlychnik').filter(
                              finish_timestamp__isnull=False).aggregate(count=Count('id')),
                          'shashlychnik_part_count': OrderContent.objects.filter(order=open_order,
                                                                                 is_canceled=False).filter(
                              menu_item__can_be_prepared_by__title__iexact='shashlychnik').aggregate(count=Count('id')),
                          'operator_part': OrderContent.objects.filter(order=open_order, is_canceled=False).filter(
                              menu_item__can_be_prepared_by__title__iexact='operator').values('menu_item__title',
                                                                                              'note').annotate(
                              count_titles=Count('menu_item__title'))

                          } for open_order in ready_orders],
        'open_length': len(open_orders),
        'ready_length': len(ready_orders),
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
        'serveries': [{'servery': servery, 'filtered': request.COOKIES.pop('servery_' + str(servery.id), 'True')} for
                      servery in Servery.objects.filter(service_point=result['service_point'])],
        'paid_filtered': request.COOKIES.pop('paid', 'True'),
        'not_paid_filtered': request.COOKIES.pop('not_paid', 'True'),
        'with_shawarma_filtered': request.COOKIES.pop('with_shawarma', 'True'),
        'with_shashlyk_filtered': request.COOKIES.pop('with_shashlyk', 'True'),
    }
    # print context
    return HttpResponse(template.render(context, request))


@login_required()
def order_history(request):
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'

    result = define_service_point(device_ip)
    if result['success']:
        try:
            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=False,
                                               is_canceled=False, is_ready=True,
                                               servery__service_point=result['service_point']).order_by('-open_time')
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске последней паузы!'
            }
            client.captureException()
            return JsonResponse(data)
    else:
        return JsonResponse(result)

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
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'

    shawarma_filter = True
    if request.COOKIES.get('with_shawarma', 'True') == 'False':
        shawarma_filter = False

    shashlyk_filter = True
    if request.COOKIES.get('with_shashlyk', 'True') == 'False':
        shashlyk_filter = False

    paid_filter = True
    if request.COOKIES.get('paid', 'True') == 'False':
        paid_filter = False

    not_paid_filter = True
    if request.COOKIES.get('not_paid', 'True') == 'False':
        not_paid_filter = False

    result = define_service_point(device_ip)
    if result['success']:
        current_day_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                                  is_canceled=False, is_ready=False,
                                                  servery__service_point=result['service_point']).order_by('open_time')
        serveries = Servery.objects.filter(service_point=result['service_point'])
        serveries_dict = {}
        for servery in serveries:
            serveries_dict['{}'.format(servery.id)] = True
            if request.COOKIES.get('servery_{}'.format(servery.id), 'True') == 'False':
                serveries_dict['{}'.format(servery.id)] = False
        try:
            if paid_filter:
                if not_paid_filter:
                    if shawarma_filter:
                        if shashlyk_filter:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                        else:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True,
                                                               with_shawarma=shawarma_filter,
                                                               with_shashlyk=shashlyk_filter,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                    else:
                        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                           close_time__isnull=True, with_shawarma=shawarma_filter,
                                                           with_shashlyk=shashlyk_filter,
                                                           is_canceled=False, is_ready=False,
                                                           servery__service_point=result['service_point']).order_by(
                            'open_time')
                else:
                    if shawarma_filter:
                        if shashlyk_filter:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True, is_paid=True,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                        else:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True, is_paid=True,
                                                               with_shawarma=shawarma_filter,
                                                               with_shashlyk=shashlyk_filter,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                    else:
                        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                           close_time__isnull=True, with_shawarma=shawarma_filter,
                                                           with_shashlyk=shashlyk_filter, is_paid=True,
                                                           is_canceled=False, is_ready=False,
                                                           servery__service_point=result['service_point']).order_by(
                            'open_time')
            else:
                if not_paid_filter:
                    if shawarma_filter:
                        if shashlyk_filter:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True, is_paid=False,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                        else:
                            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                               close_time__isnull=True, is_paid=False,
                                                               with_shawarma=shawarma_filter,
                                                               with_shashlyk=shashlyk_filter,
                                                               is_canceled=False, is_ready=False,
                                                               servery__service_point=result[
                                                                   'service_point']).order_by('open_time')
                    else:
                        open_orders = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                           close_time__isnull=True, with_shawarma=shawarma_filter,
                                                           with_shashlyk=shashlyk_filter, is_paid=False,
                                                           is_canceled=False, is_ready=False,
                                                           servery__service_point=result['service_point']).order_by(
                            'open_time')
                else:
                    open_orders = Order.objects.none()

            open_orders = filter_orders(current_day_orders, shawarma_filter, shashlyk_filter, paid_filter,
                                        not_paid_filter, serveries_dict)
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
                                                supplement_completed=True, is_ready=True,
                                                servery__service_point=result['service_point']).order_by('open_time')

            ready_orders = filter_orders(ready_orders, shawarma_filter, shashlyk_filter, paid_filter,
                                         not_paid_filter, serveries_dict)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске последней паузы!'
            }
            client.captureException()
            return JsonResponse(data)
    else:
        return JsonResponse(result)

    template = loader.get_template('shaw_queue/current_queue_grid_ajax.html')
    try:
        context = {
            'open_orders': [{'order': open_order,
                             'printed': open_order.printed,
                             'cook_part_ready_count': OrderContent.objects.filter(order=open_order,
                                                                                  is_canceled=False).filter(
                                 menu_item__can_be_prepared_by__title__iexact='cook').filter(
                                 finish_timestamp__isnull=False).aggregate(count=Count('id')),
                             'cook_part_count': OrderContent.objects.filter(order=open_order, is_canceled=False).filter(
                                 menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                             'shashlychnik_part_ready_count': OrderContent.objects.filter(order=open_order,
                                                                                          is_canceled=False).filter(
                                 menu_item__can_be_prepared_by__title__iexact='shashlychnik').filter(
                                 finish_timestamp__isnull=False).aggregate(count=Count('id')),
                             'shashlychnik_part_count': OrderContent.objects.filter(order=open_order,
                                                                                    is_canceled=False).filter(
                                 menu_item__can_be_prepared_by__title__iexact='shashlychnik').aggregate(
                                 count=Count('id')),
                             'operator_part': OrderContent.objects.filter(order=open_order, is_canceled=False).filter(
                                 menu_item__can_be_prepared_by__title__iexact='operator').values('menu_item__title',
                                                                                                 'note').annotate(
                                 count_titles=Count('menu_item__title'))
                             } for open_order in open_orders],
            'ready_orders': [{'order': open_order,
                              'cook_part_ready_count': OrderContent.objects.filter(order=open_order,
                                                                                   is_canceled=False).filter(
                                  menu_item__can_be_prepared_by__title__iexact='cook').filter(
                                  finish_timestamp__isnull=False).aggregate(count=Count('id')),
                              'cook_part_count': OrderContent.objects.filter(order=open_order,
                                                                             is_canceled=False).filter(
                                  menu_item__can_be_prepared_by__title__iexact='cook').aggregate(count=Count('id')),
                              'shashlychnik_part_ready_count': OrderContent.objects.filter(order=open_order,
                                                                                           is_canceled=False).filter(
                                  menu_item__can_be_prepared_by__title__iexact='shashlychnik').filter(
                                  finish_timestamp__isnull=False).aggregate(count=Count('id')),
                              'shashlychnik_part_count': OrderContent.objects.filter(order=open_order,
                                                                                     is_canceled=False).filter(
                                  menu_item__can_be_prepared_by__title__iexact='shashlychnik').aggregate(
                                  count=Count('id')),
                              'operator_part': OrderContent.objects.filter(order=open_order, is_canceled=False).filter(
                                  menu_item__can_be_prepared_by__title__iexact='operator').values('menu_item__title',
                                                                                                  'note').annotate(
                                  count_titles=Count('menu_item__title'))

                              } for open_order in ready_orders],
            'open_length': len(open_orders),
            'ready_length': len(ready_orders),
            'staff_category': StaffCategory.objects.get(staff__user=request.user),
            'serveries': [{'servery': servery, 'filtered': request.COOKIES.get('servery_' + str(servery.id), 'True')}
                          for servery in Servery.objects.filter(service_point=result['service_point'])],
            'paid_filtered': request.COOKIES.pop('paid', 'True'),
            'not_paid_filtered': request.COOKIES.pop('not_paid', 'True'),
            'with_shawarma_filtered': request.COOKIES.pop('with_shawarma', 'True'),
            'with_shashlyk_filtered': request.COOKIES.pop('with_shashlyk', 'True'),
        }
        for servery in Servery.objects.filter(service_point=result['service_point']):
            request.COOKIES.pop('servery_' + str(servery.id), None)
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


def filter_orders(orders, shawarma_filter, shashlyk_filter, paid_filter, not_paid_filter, serveries):
    if paid_filter:
        if not_paid_filter:
            if shawarma_filter:
                if shashlyk_filter:
                    filtered_orders = orders
                else:
                    filtered_orders = orders.filter(Q(with_shashlyk=False),
                                                    Q(with_shawarma=True) | Q(with_shawarma=False))
            else:
                filtered_orders = orders.filter(Q(with_shawarma=False),
                                                Q(with_shashlyk=False) | Q(with_shashlyk=shashlyk_filter))
        else:
            if shawarma_filter:
                if shashlyk_filter:
                    filtered_orders = orders.filter(is_paid=True)
                else:
                    filtered_orders = orders.filter(Q(is_paid=True), Q(with_shashlyk=False),
                                                    Q(with_shawarma=True) | Q(with_shawarma=False))
            else:
                filtered_orders = orders.filter(Q(is_paid=True), Q(with_shawarma=False),
                                                Q(with_shashlyk=False) | Q(with_shashlyk=shashlyk_filter))
    else:
        if not_paid_filter:
            if shawarma_filter:
                if shashlyk_filter:
                    filtered_orders = orders.filter(is_paid=False)
                else:
                    filtered_orders = orders.filter(Q(is_paid=False), Q(with_shashlyk=False),
                                                    Q(with_shawarma=True) | Q(with_shawarma=False))
            else:
                filtered_orders = orders.filter(Q(is_paid=False), Q(with_shawarma=False),
                                                Q(with_shashlyk=False) | Q(with_shashlyk=shashlyk_filter))
        else:
            filtered_orders = Order.objects.none()

    # serveries should be a dictionary where keys are ids, and values are bool
    for servery_key in serveries.keys():
        if not serveries[servery_key]:
            filtered_orders = filtered_orders.exclude(servery_id=int(servery_key))
    return filtered_orders


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

    def unmanaged_queue(request):
        device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
        if DEBUG_SERVERY:
            device_ip = '127.0.0.1'

        result = define_service_point(device_ip)
        if result['success']:
            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                               with_shashlyk=True, is_canceled=False, is_grilling_shash=True,
                                               is_ready=False,
                                               servery__service_point=result['service_point']).order_by(
                'open_time')
            context = {
                'open_orders': [{'order': open_order,
                                 'shashlychnik_part': OrderContent.objects.filter(order=open_order).filter(
                                     menu_item__can_be_prepared_by__title__iexact='Shashlychnik').values(
                                     'menu_item__title', 'note').annotate(count_titles=Count('menu_item__title'))
                                 } for open_order in open_orders],
                'open_length': len(open_orders)
            }

            template = loader.get_template('shaw_queue/shashlychnik_queue.html')
        else:
            return Http404("Неудалось определить точку обслуживания.")

        return HttpResponse(template.render(context, request))

    return unmanaged_queue(request)


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

    def unmanaged_queue(request):
        device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
        if DEBUG_SERVERY:
            device_ip = '127.0.0.1'

        result = define_service_point(device_ip)
        if result['success']:
            open_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                               with_shashlyk=True, is_canceled=False, is_grilling_shash=True,
                                               is_ready=False, servery__service_point=result['service_point']).order_by(
                'open_time')
            context = {
                'open_orders': [{'order': open_order,
                                 'shashlychnik_part': OrderContent.objects.filter(order=open_order).filter(
                                     menu_item__can_be_prepared_by__title__iexact='Shashlychnik').values(
                                     'menu_item__title', 'note').annotate(count_titles=Count('menu_item__title'))
                                 } for open_order in open_orders],
                'open_length': len(open_orders)
            }

            template = loader.get_template('shaw_queue/shashlychnik_queue_ajax.html')
            data = {
                'html': template.render(context, request)
            }
        else:
            data = {
                'html': "<h1>Неудалось определить точку обслуживания.</h1>"
            }

        return JsonResponse(data=data)

    return unmanaged_queue(request)


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
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'
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

    result = define_service_point(device_ip)
    if result['success']:
        try:
            context = {
                'order_info': order_info,
                'maker': order_info.prepared_by,
                'staff_category': StaffCategory.objects.get(staff__user=request.user),
                'order_content': current_order_content,
                'ready': order_info.content_completed and order_info.supplement_completed and order_info.shashlyk_completed,
                'serveries': Servery.objects.filter(service_point=result['service_point'])
            }
        except MultipleObjectsReturned:
            data = {
                'success': False,
                'message': 'Множество экземпляров персонала возвращено!'
            }
            logger.error('{} Множество экземпляров персонала возвращено!'.format(request.user))
            client.captureException()
            return JsonResponse(data)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так!'
            }
            logger.error('{} Что-то пошло не так при поиске персонала!'.format(request.user))
            return JsonResponse(data)
    else:
        JsonResponse(result)

    return HttpResponse(template.render(context, request))


def order_content_page(request, paginator, page_number, order_info):
    context = {
        'order_info': order_info,
        'order_content': paginator.page(page_number).object_list,
        'page_range': paginator.page_range,
        'page': paginator.page(page_number)
    }

    page = paginator.page(page_number)

    current_order = {}

    for order_item in paginator.page(page_number).object_list:
        current_order["{}".format(order_item.id)] = {
            'id': order_item.menu_item.id,
            'title': order_item.menu_item.title,
            'price': order_item.menu_item.price,
            'quantity': order_item.quantity,
            'note': order_item.note,
            'editable_quantity': False if order_item.menu_item.can_be_prepared_by == 'Cook' else True
        }

    template = loader.get_template('shaw_queue/order_content_page.html')
    data = {
        'success': True,
        'html': template.render(context, request),
        'order': json.dumps(current_order)
    }
    return data


def get_content_page(request):
    order_id = request.POST.get('order_id', None)
    page_number = request.POST.get('page_number', None)
    order_info = get_object_or_404(Order, id=order_id)

    current_order_content = OrderContent.objects.filter(order=order_id, is_canceled=False).order_by('id')
    paginator = Paginator(current_order_content, 9)

    return JsonResponse(order_content_page(request, paginator, page_number, order_info))


def order_specifics(request):
    order_id = request.POST.get('order_id', None)
    page_number = request.POST.get('page_number', None)
    user = request.user
    staff = Staff.objects.get(user=user)
    order_info = get_object_or_404(Order, id=order_id)
    order_content = OrderContent.objects.filter(order_id=order_id).order_by('id')
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'
    flag = True
    for item in order_content:
        if item.finish_timestamp is None:
            flag = False
    if flag:
        order_info.content_completed = True
        order_info.supplement_completed = True
    order_info.save()
    current_order_content = OrderContent.objects.filter(order=order_id, is_canceled=False)
    p = Paginator(current_order_content, 9)

    # if page_number is not None:
    #     content_page = get_content_page(p, page_number)
    # else:
    #     content_page = get_content_page(p, 1)

    template = loader.get_template('shaw_queue/order_content_modal.html')

    result = define_service_point(device_ip)
    if result['success']:
        try:
            context = {
                'order_info': order_info,
                'maker': order_info.prepared_by,
                'staff_category': StaffCategory.objects.get(staff__user=request.user),
                'order_content': p.page(1).object_list,
                'page_range': p.page_range,
                'page': p.page(1),
                'ready': order_info.content_completed and order_info.supplement_completed and order_info.shashlyk_completed,
                'serveries': Servery.objects.filter(service_point=result['service_point'])
            }
        except MultipleObjectsReturned:
            data = {
                'success': False,
                'message': 'Множество экземпляров персонала возвращено!'
            }
            logger.error('{} Множество экземпляров персонала возвращено!'.format(request.user))
            client.captureException()
            return JsonResponse(data)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так!'
            }
            logger.error('{} Что-то пошло не так при поиске персонала!'.format(request.user))
            return JsonResponse(data)
    else:
        JsonResponse(result)

    current_order = {}

    for order_item in current_order_content:
        current_order["{}".format(order_item.id)] = {
            'id': order_item.menu_item.id,
            'title': order_item.menu_item.title,
            'price': order_item.menu_item.price,
            'quantity': order_item.quantity,
            'note': order_item.note,
            'editable_quantity': False if order_item.menu_item.can_be_prepared_by == 'Cook' else True
        }

    data = {
        'success': True,
        'html': template.render(context, request),
        'order': json.dumps(current_order)
    }

    return JsonResponse(data)


def update_commodity(request):
    commodity_id = request.POST.get('id', None)
    note = request.POST.get('note', None)
    quantity = request.POST.get('quantity', None)
    if commodity_id is not None:
        try:
            commodity = OrderContent.objects.get(id=commodity_id)
        except MultipleObjectsReturned:
            data = {
                'success': False,
                'message': 'Множество экземпляров персонала возвращено!'
            }
            logger.error('{} Множество экземпляров персонала возвращено!'.format(request.user))
            client.captureException()
            return JsonResponse(data)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так!'
            }
            logger.error('{} Что-то пошло не так при поиске персонала!'.format(request.user))
            return JsonResponse(data)

        if note is not None:
            commodity.note = note
        if quantity is not None:
            commodity.quantity = quantity
        commodity.save()

        data = {
            'success': True
        }
    else:
        data = {
            'success': False,
            'message': 'Отсутствует идентификатор товара!'
        }
        logger.error('{} Отсутствует идентификатор товара!'.format(request.user))

    return JsonResponse(data)


def aux_control_page(request):
    template = loader.get_template('shaw_queue/aux_controls.html')
    context = {}
    return HttpResponse(template.render(context, request))


def flag_changer(request):
    global waiting_numbers
    number = request.POST.get('number', None)
    if number is not None:
        if number in waiting_numbers.keys():
            waiting_numbers[number] = True
        data = {
            'success': True
        }
    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


def long_poll_handler(request):
    global waiting_numbers
    number = request.POST.get('number', None)
    if number is not None:
        waiting_numbers[number] = False
        while True:
            if waiting_numbers[number]:
                waiting_numbers[number] = False
                break
        data = {
            'message': 'The number is {}'.format(number)
        }
    else:
        data = {
            'message': 'There is no number in request'
        }
    return JsonResponse(data)


@login_required()
def delivery_interface(request):
    utc = pytz.UTC
    template = loader.get_template('shaw_queue/delivery_main.html')
    print("{} {}".format(timezone.datetime.now(), datetime.datetime.now()))
    staff = Staff.objects.get(user=request.user)
    print("staff_id = {}".format(staff.id))
    delivery_orders = DeliveryOrder.objects.filter(obtain_timepoint__contains=datetime.date.today()).order_by(
        'delivered_timepoint')
    deliveries = Delivery.objects.filter(creation_timepoint__contains=datetime.date.today()).order_by(
        'departure_timepoint')

    delivery_info = [
        {
            'delivery': delivery,
            'departure_time': (DeliveryOrder.objects.filter(delivery=delivery).annotate(
                suggested_depature_time=ExpressionWrapper(F('delivered_timepoint') - F('delivery_duration'),
                                                          output_field=DateTimeField())).order_by(
                'suggested_depature_time'))[0].suggested_depature_time.time() if len(DeliveryOrder.objects.filter(
                delivery=delivery)) else "--:--",
            'delivery_orders': DeliveryOrder.objects.filter(delivery=delivery),
            'delivery_orders_number': len(DeliveryOrder.objects.filter(delivery=delivery))
        } for delivery in deliveries
        ]
    processed_d_orders = [
        {
            'order': delivery_order,
            'enlight_warning': True if delivery_order.delivered_timepoint - (
                delivery_order.delivery_duration + delivery_order.preparation_duration) < utc.localize(
                datetime.datetime.now() - datetime.timedelta(
                    minutes=5)) and delivery_order.prep_start_timepoint is None else False,
            'enlight_alert': True if delivery_order.delivered_timepoint - (
                delivery_order.delivery_duration + delivery_order.preparation_duration) < utc.localize(
                datetime.datetime.now())
                                     and delivery_order.prep_start_timepoint is None else False,
            'available_cooks': Staff.objects.filter(available=True, staff_category__title__iexact='Cook',
                                                    service_point=delivery_order.order.servery.service_point)
        } for delivery_order in delivery_orders
        ]
    context = {
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
        'delivery_order_form': DeliveryOrderForm,
        'delivery_orders': processed_d_orders,  # delivery_orders,
        'delivery_info': delivery_info
    }
    return HttpResponse(template.render(context, request))


@login_required()
def delivery_workspace_update(request):
    utc = pytz.UTC
    template = loader.get_template('shaw_queue/delivery_workspace.html')
    print("{} {}".format(timezone.datetime.now(), datetime.datetime.now()))
    delivery_orders = DeliveryOrder.objects.filter(obtain_timepoint__contains=datetime.date.today()).order_by(
        'delivered_timepoint')
    processed_d_orders = [
        {
            'order': delivery_order,
            'enlight_warning': True if delivery_order.delivered_timepoint - (
                delivery_order.delivery_duration + delivery_order.preparation_duration) < utc.localize(
                datetime.datetime.now() - datetime.timedelta(
                    minutes=5)) and delivery_order.prep_start_timepoint is None else False,
            'enlight_alert': True if delivery_order.delivered_timepoint - (
                delivery_order.delivery_duration + delivery_order.preparation_duration) < utc.localize(
                datetime.datetime.now())
                                     and delivery_order.prep_start_timepoint is None else False,
            'available_cooks': Staff.objects.filter(available=True, staff_category__title__iexact='Cook',
                                                    service_point=delivery_order.order.servery.service_point)
        } for delivery_order in delivery_orders
        ]
    context = {
        'delivery_orders': processed_d_orders
    }
    # context = {
    #     'delivery_orders': delivery_orders
    # }
    data = {
        'success': True,
        'html': template.render(context, request)
    }
    return JsonResponse(data)


def print_order(request, order_id):
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'

    result = define_service_point(device_ip)

    if result['success']:
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

        printers = Printer.objects.filter(service_point=result['service_point'])
        chosen_printer = None
        for printer in printers:
            if printer.ip_address == device_ip:
                chosen_printer = printer

        if chosen_printer is None and len(printers) > 0:
            chosen_printer = printers[0]

        cmd = 'echo "{}"'.format(template.render(context, request)) + " | lp -h " + chosen_printer.ip_address
        scmd = cmd.encode('utf-8')
        os.system(scmd)
    else:
        return JsonResponse(result)

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
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'
    daily_number = request.POST.get('daily_number', None)
    data = {
        'success': False
    }
    if daily_number:
        result = define_service_point(device_ip)
        if result['success']:
            try:
                order = Order.objects.get(daily_number=daily_number, open_time__contains=datetime.date.today(),
                                          servery__service_point=result['service_point'])
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
        else:
            return JsonResponse(result)

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


@login_required()
def select_cook(request):
    cook_pk = request.POST.get('cook_pk', None)
    delivery_order_pk = request.POST.get('delivery_order_pk', None)
    cook = None
    order = None
    try:
        cook = Staff.objects.get(pk=cook_pk)
    except Staff.DoesNotExist:
        data = {
            'success': False,
            'message': 'Указанный повар не найден!'
        }
        client.captureException()
        return JsonResponse(data)
    except Staff.MultipleObjectsReturned:
        data = {
            'success': False,
            'message': 'Множество поваров найдено!'
        }
        client.captureException()
        return JsonResponse(data)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске персонала!'
        }
        client.captureException()
        return JsonResponse(data)

    try:
        order = Order.objects.get(deliveryorder__pk=delivery_order_pk)
    except Order.DoesNotExist:
        data = {
            'success': False,
            'message': 'Указанный заказ не найден!'
        }
        client.captureException()
        return JsonResponse(data)
    except Order.MultipleObjectsReturned:
        data = {
            'success': False,
            'message': 'Множество заказов найдено для данного заказа доставки!'
        }
        client.captureException()
        return JsonResponse(data)
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске заказа!'
        }
        client.captureException()
        return JsonResponse(data)

    try:
        order.prepared_by = cook
        order.save()
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при назначении заказа №{} повару {}!'.format(order.daily_number, cook)
        }
        client.captureException()
        return JsonResponse(data)

    data = {
        'success': True,
        'message': 'Заказ №{} назначен в готовку повару {}.'.format(order.daily_number, cook)
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
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'
    result = define_service_point(device_ip)
    if result['success']:
        try:
            today_orders = Order.objects.filter(open_time__contains=datetime.date.today(), close_time__isnull=True,
                                                is_ready=True, servery__service_point=result['service_point'])
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске заказов!'
            }
            client.captureException()
            return JsonResponse(data)
    else:
        return JsonResponse(result)
    for order in today_orders:
        order.is_voiced = False
        order.save()

    return HttpResponse()


@login_required()
@permission_required('shaw_queue.add_order')
def make_order(request):
    delivery_order_pk = request.POST.get('delivery_order_pk', None)
    file = open('log/cook_choose.log', 'a')
    servery_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        servery_ip = '127.0.0.1'
    result = define_service_point(servery_ip)
    content = json.loads(request.POST['order_content'])
    payment = request.POST['payment']
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
    if result['success']:
        try:
            order_last_daily_number = Order.objects.filter(open_time__contains=datetime.date.today(),
                                                           servery__service_point=result['service_point']).aggregate(
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
    else:
        return JsonResponse(result)

    if order_last_daily_number:
        if order_last_daily_number['daily_number__max'] is not None:
            order_next_number = order_last_daily_number['daily_number__max'] + 1
        else:
            order_next_number = 1

    is_paid = False
    paid_with_cash = False
    if payment != 'not_paid':
        if payment == 'paid_with_cash':
            paid_with_cash = True
            is_paid = True
        else:
            is_paid = True

    try:
        order = Order(open_time=datetime.datetime.now(), daily_number=order_next_number, is_paid=is_paid,
                      paid_with_cash=paid_with_cash, status_1c=0)
    except:
        data = {
            'success': False,
            'message': 'Something wrong happened while creating new order!'
        }
        client.captureException()
        return JsonResponse(data)

    # cooks = Staff.objects.filter(user__last_login__contains=datetime.date.today(), staff_category__title__iexact='Cook')
    try:
        if result['success']:
            cooks = Staff.objects.filter(available=True, staff_category__title__iexact='Cook',
                                         service_point=result['service_point'])
            cooks = sample(list(cooks), len(cooks))
        else:
            return JsonResponse(result)
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

    if has_cook_content and cook_choose != 'delivery':
        if cook_choose == 'auto':
            min_index = 0
            min_count = 100
            file.write("Заказ №{}\n".format(order.daily_number))
            for cook_index in range(0, len(cooks)):
                try:
                    cooks_order_content = OrderContent.objects.filter(order__prepared_by=cooks[cook_index],
                                                                      order__open_time__contains=datetime.date.today(),
                                                                      order__is_canceled=False,
                                                                      order__close_time__isnull=True,
                                                                      order__is_ready=False,
                                                                      menu_item__can_be_prepared_by__title__iexact='Cook')
                except:
                    data = {
                        'success': False,
                        'message': 'Something wrong happened while getting cook\'s content!'
                    }
                    return JsonResponse(data)

                file.write("{}: {}\n".format(cooks[cook_index], len(cooks_order_content)))

                if min_count > len(cooks_order_content):
                    min_count = len(cooks_order_content)
                    min_index = cook_index

            file.write("Выбранный повар: {}\n".format(cooks[min_index]))
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
        if item['quantity'] - int(item['quantity']) != 0:
            try:
                new_order_content = OrderContent(order=order, menu_item_id=item['id'], note=item['note'],
                                                 quantity=item['quantity'])
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
            total += menu_item.price * item['quantity']

        else:
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
    order.with_shawarma = content_presence
    order.with_shashlyk = shashlyk_presence
    order.content_completed = not content_presence
    order.shashlyk_completed = not shashlyk_presence
    order.supplement_completed = not supplement_presence
    order.save()

    if order.is_paid:
        print("Sending request to " + order.servery.ip_address)
        print(order)
        if FORCE_TO_LISTNER:
            data = send_order_to_listner(order)
        else:
            data = send_order_to_1c(order, False)
            if not data["success"]:
                print("Deleting order.")
                order.delete()

        print("Request sent.")
        if data["success"]:
            data["total"] = order.total
            data["content"] = json.dumps(content_to_send)
            data["message"] = ''
            data["daily_number"] = order.daily_number
            data["guid"] = order.guid_1c
            data["pk"] = order.pk
    else:
        data["success"] = True
        data["total"] = order.total
        data["content"] = json.dumps(content_to_send)
        data["message"] = ''
        data["daily_number"] = order.daily_number
        data["pk"] = order.pk

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
def close_all(request):
    device_ip = request.META.get('HTTP_X_REAL_IP', '') or request.META.get('HTTP_X_FORWARDED_FOR', '')
    if DEBUG_SERVERY:
        device_ip = '127.0.0.1'

    shawarma_filter = True
    if request.COOKIES.get('with_shawarma', 'True') == 'False':
        shawarma_filter = False

    shashlyk_filter = True
    if request.COOKIES.get('with_shashlyk', 'True') == 'False':
        shashlyk_filter = False

    paid_filter = True
    if request.COOKIES.get('paid', 'True') == 'False':
        paid_filter = False

    not_paid_filter = True
    if request.COOKIES.get('not_paid', 'True') == 'False':
        not_paid_filter = False

    result = define_service_point(device_ip)
    if result['success']:
        try:
            ready_orders = Order.objects.filter(open_time__contains=timezone.now().date(), close_time__isnull=True,
                                                is_ready=True, servery__service_point=result['service_point'])

            serveries = Servery.objects.filter(service_point=result['service_point'])
            serveries_dict = {}
            for servery in serveries:
                serveries_dict['{}'.format(servery.id)] = True
                if request.COOKIES.get('servery_{}'.format(servery.id), 'True') == 'False':
                    serveries_dict['{}'.format(servery.id)] = False

            ready_orders = filter_orders(ready_orders, shawarma_filter, shashlyk_filter, paid_filter, not_paid_filter,
                                         serveries_dict)

        except EmptyResultSet:
            data = {
                'success': False,
                'message': 'Заказов не найдено!'
            }
            client.captureException()
            return JsonResponse(data)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске заказов!'
            }
            client.captureException()
            return JsonResponse(data)
        for order in ready_orders:
            order.close_time = datetime.datetime.now()
            order.is_ready = True
            order.save()
    else:
        return JsonResponse(result)

    data = {
        'success': True
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
        if order.is_paid:
            result = send_order_return_to_1c(order)
            if result['success']:
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
                return JsonResponse(result)
        else:
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
        if staff.staff_category.title == 'Operator':
            products = shashlychnik_products
        else:
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
        if staff.staff_category.title == 'Operator':
            products = shashlychnik_products
        else:
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
    servery_id = request.POST['servery_id']

    if servery_id != 'auto':
        try:
            servery = Servery.objects.get(id=servery_id)
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

    total = 0
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
            item.quantity = round(float(values[index]), 3)
            total += item.menu_item.price * item.quantity
            item.save()

        try:
            order = Order.objects.get(id=order_id)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске заказа!'
            }
            return JsonResponse(data)
        cash_to_throw_out = 0
        rounding_discount = 0
        if order.with_shashlyk:
            rounding_discount = (round(total, 2) - order.discount) % 5
        order.discount += rounding_discount
        order.is_paid = True
        order.paid_with_cash = paid_with_cash
        if servery_id != 'auto':
            order.servery = servery

        total = 0
        content_presence = False
        supplement_presence = False
        try:
            content = OrderContent.objects.filter(order=order, is_canceled=False)
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
            if menu_item.can_be_prepared_by.title == 'Shashlychnik':
                if cash_to_throw_out > 0:
                    weight_to_throw_out = cash_to_throw_out / menu_item.price
                    if item.quantity - weight_to_throw_out > 0:
                        item.quantity -= weight_to_throw_out
                        item.save()
                        cash_to_throw_out -= weight_to_throw_out * menu_item.price

            if menu_item.can_be_prepared_by.title == 'Operator':
                supplement_presence = True
            total += menu_item.price * item.quantity
        order.total = round(total, 2)
        # order.supplement_completed = not supplement_presence
        # order.content_completed = not content_presence
        order.save()
        # print order

        print("Sending request to " + order.servery.ip_address)
        if FORCE_TO_LISTNER:
            data = send_order_to_listner(order)
        else:
            data = send_order_to_1c(order, False)
            if not data["success"]:
                print("Payment canceled.")
                order.is_paid = False
                order.save()
        data['total'] = order.total - order.discount
        print("Request sent.")

    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.change_order')
def cancel_item(request):
    product_id = request.POST.get('id', None)
    staff = Staff.objects.get(user=request.user)
    if product_id:
        try:
            item = OrderContent.objects.get(id=product_id)
        except:
            data = {
                'success': False,
                'message': 'Что-то пошло не так при поиске продуктов!'
            }
            return JsonResponse(data)
        item.canceled_by = staff
        item.is_canceled = True
        item.save()
        data = {
            'success': True
        }
        order = item.order
        curr_order_content = OrderContent.objects.filter(order=order, is_canceled=False)
        total = 0
        for order_item in curr_order_content:
            total += order_item.menu_item.price * order_item.quantity

        order.total = total
        order.save()
    else:
        data = {
            'success': False
        }

    return JsonResponse(data)


@login_required()
@permission_required('shaw_queue.view_statistics')
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
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
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
@permission_required('shaw_queue.view_statistics')
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
        aux = list(avg_preparation_time)
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
            'staff_category': StaffCategory.objects.get(staff__user=request.user),
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
@permission_required('shaw_queue.view_statistics')
def opinion_statistics(request):
    template = loader.get_template('shaw_queue/opinion_statistics.html')
    avg_mark = OrderOpinion.objects.filter(post_time__contains=datetime.date.today()).values('mark').aggregate(
        avg_mark=Avg('mark'))
    min_mark = OrderOpinion.objects.filter(post_time__contains=datetime.date.today()).values('mark').aggregate(
        min_mark=Min('mark'))
    max_mark = OrderOpinion.objects.filter(post_time__contains=datetime.date.today()).values('mark').aggregate(
        max_mark=Max('mark'))
    context = {
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
        'total_orders': len(OrderOpinion.objects.filter(post_time__contains=datetime.date.today())),
        'avg_mark': avg_mark['avg_mark'],
        'min_mark': min_mark['min_mark'],
        'max_mark': max_mark['max_mark'],
        'opinions': [opinion for opinion in
                     OrderOpinion.objects.filter(post_time__contains=datetime.date.today()).order_by('post_time')]
    }
    return HttpResponse(template.render(context, request))


@login_required()
@permission_required('shaw_queue.view_statistics')
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
            'staff_category': StaffCategory.objects.get(staff__user=request.user),
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
@permission_required('shaw_queue.view_statistics')
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
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
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
@permission_required('shaw_queue.view_statistics')
def pause_statistic_page_ajax(request):
    start_date = request.POST.get('start_date', None)
    if start_date is None or start_date == '':
        start_date_conv = datetime.datetime.today()
    else:
        start_date_conv = datetime.datetime.strptime(start_date, "%Y/%m/%d %H:%M")  # u'2018/01/04 22:31'

    end_date = request.POST.get('end_date', None)
    if end_date is None or end_date == '':
        end_date_conv = datetime.datetime.today()
    else:
        end_date_conv = datetime.datetime.strptime(end_date, "%Y/%m/%d %H:%M")  # u'2018/01/04 22:31'
    template = loader.get_template('shaw_queue/pause_statistics_ajax.html')
    try:
        avg_duration_time = PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                        end_timestamp__lte=end_date_conv).values(
            'start_timestamp', 'end_timestamp').aggregate(duration=Avg(F('end_timestamp') - F('start_timestamp')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении средней продолжительности пауз!'
        }
        return JsonResponse(data)

    try:
        min_duration_time = PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                        end_timestamp__lte=end_date_conv).values(
            'start_timestamp', 'end_timestamp').aggregate(duration=Min(F('end_timestamp') - F('start_timestamp')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении минимальной продолжительности пауз!'
        }
        return JsonResponse(data)

    try:
        max_duration_time = PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                        end_timestamp__lte=end_date_conv).values(
            'start_timestamp', 'end_timestamp').aggregate(duration=Max(F('end_timestamp') - F('start_timestamp')))
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при вычислении максимальной продолжительности пауз!'
        }
        return JsonResponse(data)

    try:
        engaged_staff = Staff.objects.filter(staff_category__title__iexact='Cook')
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске персонала!'
        }
        return JsonResponse(data)

    # try:
    context = {
        'staff_category': StaffCategory.objects.get(staff__user=request.user),
        'total_pauses': len(PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                        end_timestamp__lte=end_date_conv)),
        'avg_duration': str(avg_duration_time['duration']).split('.', 2)[0],
        'min_duration': str(min_duration_time['duration']).split('.', 2)[0],
        'max_duration': str(max_duration_time['duration']).split('.', 2)[0],
        # 'pauses': [{
        #                'staff': pause.staff,
        #                'start_timestamp': str(pause.start_timestamp).split('.', 2)[0],
        #                'end_timestamp': str(pause.end_timestamp).split('.', 2)[0],
        #                'duration': str(pause.end_timestamp - pause.start_timestamp).split('.', 2)[0]
        #            }
        #            for pause in PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
        #                                                     end_timestamp__lte=end_date_conv).order_by(
        #         'start_timestamp')],
        'pause_info': [{
                           'total_duration': PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                                         end_timestamp__lte=end_date_conv,
                                                                         staff=staff).aggregate(
                               duration=Sum(F('end_timestamp') - F('start_timestamp'))),
                           'staff': staff,
                           'pauses': [{
                                          'staff': pause.staff,
                                          'start_timestamp': str(pause.start_timestamp).split('.', 2)[0],
                                          'end_timestamp': str(pause.end_timestamp).split('.', 2)[0],
                                          'duration': str(pause.end_timestamp - pause.start_timestamp).split('.', 2)[0]
                                      }
                                      for pause in PauseTracker.objects.filter(start_timestamp__gte=start_date_conv,
                                                                               end_timestamp__lte=end_date_conv,
                                                                               staff=staff).order_by('start_timestamp')]
                       } for staff in engaged_staff]
    }
    # except:
    #     data = {
    #         'success': False,
    #         'message': 'Что-то пошло не так при построении шаблона!'
    #     }
    #     client.captureException()
    #     return JsonResponse(data)
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
    if order.prepared_by is not None:
        cook = order.prepared_by.user.first_name
    else:
        cook = '  '
    order_dict = {
        'servery_number': order.servery.guid_1c,
        'cash': order.paid_with_cash,
        'cashless': not order.paid_with_cash,
        'internet_order': False,
        'queue_number': order.daily_number % 100,
        'cook': cook,
        'return_of_goods': is_return,
        'total': order.total,
        'DC': '111',
        'Discount': order.discount,
        'Goods': []
    }
    curr_order_content = OrderContent.objects.filter(order=order).values('menu_item__title',
                                                                         'menu_item__guid_1c').annotate(
        count=Sum('quantity'))
    for item in curr_order_content:
        order_dict['Goods'].append(
            {
                'Name': item['menu_item__title'],
                'Count': round(item['count'], 3),
                'GUID': item['menu_item__guid_1c']
            }
        )
    try:
        result = requests.post('http://' + SERVER_1C_IP + ':' + SERVER_1C_PORT + ORDER_URL,
                               auth=(SERVER_1C_USER.encode('utf8'), SERVER_1C_PASS),
                               json=order_dict)
    except ConnectionError:
        data = {
            'success': False,
            'message': 'Возникла проблема соединения с 1C при отправке информации о заказе! Заказ удалён! Вы можете повторить попытку!'
        }
        client.captureException()
        return data
    except:
        data = {
            'success': False,
            'message': 'Возникло необработанное исключение при отправке информации о заказе в 1C! Заказ удалён! Вы можете повторить попытку!'
        }
        client.captureException()
        return data

    if result.status_code == 200:
        order.sent_to_1c = True
        try:
            order.guid_1c = result.json()['GUID']
        except KeyError:
            data = {
                'success': False,
                'message': 'Нет GUID в ответе 1С!'
            }
            client.captureException()
            return data

        order.save()

        return {"success": True}
    else:
        order.status_1c = result.status_code
        if result.status_code == 500:
            return {
                'success': False,
                'message': '500: Ошибка в обработке 1С! Заказ удалён! Вы можете повторить попытку!'
            }
        else:
            if result.status_code == 400:
                return {
                    'success': False,
                    'message': '400: Ошибка в запросе, отправленном в 1С! Заказ удалён! Вы можете повторить попытку!'
                }
            else:
                if result.status_code == 399:
                    return {
                        'success': False,
                        'message': '399: Сумма чека не совпадает! Заказ удалён! Вы можете повторить попытку!'
                    }
                else:
                    if result.status_code == 398:
                        return {
                            'success': False,
                            'message': '398: Не удалось записать чек! Заказ удалён! Вы можете повторить попытку!'
                        }
                    else:
                        return {
                            'success': False,
                            'message': '{} в ответе 1С! Заказ удалён! Вы можете повторить попытку!'.format(
                                result.status_code)
                        }


def send_order_return_to_1c(order):
    order_dict = {
        'Order': order.guid_1c
    }
    try:
        result = requests.post('http://' + SERVER_1C_IP + ':' + SERVER_1C_PORT + RETURN_URL,
                               auth=(SERVER_1C_USER.encode('utf8'), SERVER_1C_PASS),
                               json=order_dict)
    except ConnectionError:
        data = {
            'success': False,
            'message': 'Возникла проблема соединения с 1C при отправке информации о возврате заказа!'
        }
        client.captureException()
        return data
    except:
        data = {
            'success': False,
            'message': 'Возникло необработанное исключение при отправке информации о возврате заказа в 1C!'
        }
        client.captureException()
        return data

    if result.status_code == 200:
        order.sent_to_1c = True
        order.save()

        return {"success": True}
    else:
        if result.status_code == 500:
            return {
                'success': False,
                'message': '500: Ошибка в обработке 1С!'
            }
        else:
            if result.status_code == 400:
                return {
                    'success': False,
                    'message': '400: Ошибка в запросе, отправленном в 1С!'
                }
            else:
                if result.status_code == 399:
                    return {
                        'success': False,
                        'message': '399: Сумма в чека не совпала!'
                    }
                else:
                    if result.status_code == 398:
                        return {
                            'success': False,
                            'message': '398: Не удалось записать чек!'
                        }
                    else:
                        return {
                            'success': False,
                            'message': '{} в ответе 1С!'.format(result.status_code)
                        }


@csrf_exempt
def recive_1c_order_status(request):
    result = json.loads(request.body.decode('utf-8'))
    order_guid = result['GUID']
    status = result['Order_status']
    if order_guid is not None and status is not None:
        try:
            order = Order.objects.get(guid_1c=order_guid)
        except MultipleObjectsReturned:
            data = {
                'success': False,
                'message': 'Множество экземпляров точек возвращено!'
            }
            client.captureException()
            return HttpResponse()
        except:
            data = {
                'success': False,
                'message': 'Множество экземпляров точек возвращено!'
            }
            client.captureException()
            return HttpResponse()

        # All Good
        if status == 200:
            order.paid_in_1c = True
            order.status_1c = 200
            order.save()
        else:
            # Payment Failed
            if status == 397:
                order.status_1c = 397
                order.save()
            else:
                # Print Failed
                if status == 396:
                    order.status_1c = 396
                    order.save()
    return HttpResponse()


def status_refresher(request):
    order_guid = request.POST.get('order_guid', None)
    if order_guid is not None:
        try:
            order = Order.objects.get(guid_1c=order_guid)
        except MultipleObjectsReturned:
            data = {
                'success': False,
                'message': 'Множество экземпляров заказов возвращено!'
            }
            client.captureException()
            return JsonResponse(data)
        except:
            data = {
                'success': False,
                'message': 'Необработанное исключение при поиске заказа!'
            }
            client.captureException()
            return JsonResponse(data)

        if order.status_1c == 0:
            data = {
                'success': True,
                'message': 'Ожидается ответ от 1С!',
                'daily_number': order.daily_number,
                'status': order.status_1c,
                'guid': order.guid_1c
            }
            return JsonResponse(data)
        else:
            if order.status_1c == 200:
                data = {
                    'success': True,
                    'message': 'Оплата прошла успешно!',
                    'daily_number': order.daily_number,
                    'status': order.status_1c,
                    'guid': order.guid_1c
                }
                return JsonResponse(data)
            else:
                if order.status_1c == 397:
                    data = {
                        'success': True,
                        'message': 'Произошла ошибка при оплате! Заказ удалён! Вы можете повторить попытку!',
                        'daily_number': order.daily_number,
                        'status': order.status_1c,
                        'guid': order.guid_1c
                    }
                    order.delete()
                    return JsonResponse(data)
                else:
                    if order.status_1c == 396:
                        data = {
                            'success': True,
                            'message': 'Произошла ошибка при печати чека! Заказ удалён! Вы можете повторить попытку!',
                            'daily_number': order.daily_number,
                            'status': order.status_1c,
                            'guid': order.guid_1c
                        }
                        order.delete()
                        return JsonResponse(data)
                    else:
                        data = {
                            'success': True,
                            'message': '1С вернула статус {}! Заказ удалён! Вы можете повторить попытку!'.format(
                                order.status_1c),
                            'daily_number': order.daily_number,
                            'status': order.status_1c,
                            'guid': order.guid_1c
                        }
                        order.delete()
                        return JsonResponse(data)
    else:
        data = {
            'success': False,
            'message': 'В запросе отсутствует идентификатор заказа!'
        }
        return JsonResponse(data)


def send_order_to_listner(order):
    try:
        requests.post('http://' + order.servery.ip_address + ':' + LISTNER_PORT, json=prepare_json_check(order))
    except ConnectionError:
        data = {
            'success': False,
            'message': 'Connection error occured while sending to listner!'
        }
        client.captureException()
        return data
    except:
        data = {
            'success': False,
            'message': 'Something wrong happened while sending to listner!'
        }
        client.captureException()
        return data

    return {"success": True}


def order_1c_payment(request):
    order_guid = request.POST.get('GUID', None)
    payment_result = request.POST.get('payment_result', None)
    order = Order.objects.get(guid_1c=order_guid)
    order.paid_in_1c = payment_result
    order.save()
    return HttpResponse()


def define_service_point(ip):
    ip_blocks = ip.split('.')
    subnet_number = ip_blocks[2]
    try:
        service_point = ServicePoint.objects.get(subnetwork=subnet_number)
    except MultipleObjectsReturned:
        data = {
            'success': False,
            'message': 'Множество экземпляров точек возвращено!'
        }
        logger.error('Множество точек возвращено для ip {}!'.format(ip_blocks))
        client.captureException()
        return data
    except:
        data = {
            'success': False,
            'message': 'Что-то пошло не так при поиске точки!'
        }
        logger.error('Что-то пошло не так при поиске точки для ip {}!'.format(ip_blocks))
        client.captureException()
        return data
    return {'success': True, 'service_point': service_point}


def get_queue_info(staff, device_ip):
    result = define_service_point(device_ip)
    if result['success']:
        service_point = result['service_point']

    text = 'Время события: ' + str(datetime.datetime.now())[:-7] + '\r\n' + \
           'Место события: ' + str(service_point) + '\r\n\r\n'

    cooks = Staff.objects.filter(available=True, staff_category__title__iexact='Cook',
                                 service_point=service_point)
    if len(cooks) == 0:
        text += 'НЕТ АКТИВНЫХ ПОВАРОВ!'
    else:
        text += '|\t\t\t Повар \t\t\t|\t Заказов \t|\t Шаурмы \t|\r\n'

    for cook in cooks:
        cooks_order = Order.objects.filter(prepared_by=cook,
                                           open_time__contains=datetime.date.today(),
                                           is_canceled=False,
                                           close_time__isnull=True,
                                           is_ready=False).count()

        cooks_order_content = OrderContent.objects.filter(order__prepared_by=cook,
                                                      order__open_time__contains=datetime.date.today(),
                                                      order__is_canceled=False,
                                                      order__close_time__isnull=True,
                                                      order__is_ready=False,
                                                      menu_item__can_be_prepared_by__title__iexact='Cook').count()

        text += '\t' + str(cook) + '\t\t\t\t\t' + str(cooks_order) + '\t\t\t\t\t' + str(cooks_order_content) +'\r\n'

    return text


def send_email(subject, staff, device_ip):
    message = get_queue_info(staff, device_ip)

    try:
        send_mail(subject, message, SMTP_FROM_ADDR, [SMTP_TO_ADDR], fail_silently=False, auth_user=SMTP_LOGIN, auth_password=SMTP_PASSWORD)
    except:
        print('failed to send mail')
