from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^menu/$', views.menu, name='menu'),
    url(r'^contacts/$', views.contacts, name='contacts'),
    url(r'^about/$', views.about, name='about'),
    url(r'^confirm_order/$', views.create_order, name='confirm_order'),
    url(r'^check_order/$', views.check_order, name='check_order'),
    url(r'^check_order_ajax/$', views.check_order_ajax, name='check_order_ajax'),
]