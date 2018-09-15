from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.welcomer, name='welcomer'),    
    url(r'^reload_menu', views.get_1c_menu, name='reload_menu'),
    url(r'^order_status', views.recive_1c_order_status, name='order_status'),       
    url(r'^menu', views.menu, name='menu'),
    url(r'^delivery_interface', views.delivery_interface, name='delivery_interface'),
    url(r'^cook_pause', views.cook_pause, name="cook_pause"),
    url(r'^aux_control_page', views.aux_control_page, name="aux_control_page"),
    url(r'^order/1c_payment_result/$', views.order_1c_payment, name="order_1c_payment"),
    url(r'^order/print/(?P<order_id>[0-9]+)/$', views.print_order, name="order_print"),
    url(r'^order/voice/(?P<order_id>[0-9]+)/$', views.voice_order, name="voice_order"),
    url(r'^order/(?P<order_id>[0-9]+)/$', views.order_content, name="order_content"),
    url(r'^close_all/$', views.close_all, name="close_all"),
    url(r'^voice_all/$', views.voice_all, name="voice_all"),
    url(r'^ajax/delivery_workspace_update', views.delivery_workspace_update, name="delivery-workspace-update"),
    url(r'^ajax/delivery_order', views.DeliveryOrderViewAJAX.as_view(), name="delivery-order-ajax"),
    url(r'^ajax/search_comment', views.search_comment, name="search_comment"),
    url(r'^ajax/unvoice', views.unvoice_order, name="unvoice_order"),
    url(r'^ajax/select_order', views.select_order, name="select_order"),
    url(r'^ajax/order_specifics', views.order_specifics, name="order_specifics"),
    url(r'^ajax/start_long_poll', views.long_poll_handler, name="start_long_poll"),
    url(r'^ajax/respond_long_poll', views.flag_changer, name="respond_long_poll"),
    url(r'^ajax/update_commodity', views.update_commodity, name="update_commodity"),
    url(r'^ajax/get_content_page', views.get_content_page, name="get_content_page"),
    url(r'^ajax/status_refresh', views.status_refresher, name="status_refresh"),
    url(r'^ajax/make_order', views.make_order, name="make_order"),
    url(r'^ajax/buyer_queue', views.buyer_queue_ajax, name="buyer_queue_ajax"),
    url(r'^ajax/close_order', views.close_order, name="close_order"),
    url(r'^ajax/ready_order', views.ready_order, name="ready_order"),
    url(r'^ajax/pay_order', views.pay_order, name="pay_order"),
    url(r'^ajax/cancel_item', views.cancel_item, name="cancel_item"),
    url(r'^ajax/cancel_order', views.cancel_order, name="cancel_order"),
    url(r'^ajax/next_to_prepare', views.next_to_prepare, name="next_to_prepare"),
    url(r'^ajax/take', views.take, name="take"),
    url(r'^ajax/to_grill', views.to_grill, name="to_grill"),
    url(r'^ajax/grill_timer', views.grill_timer, name="grill_timer"),
    url(r'^ajax/finish_cooking', views.finish_cooking, name="finish_cooking"),
    url(r'^ajax/grill_all_content', views.grill_all_content, name="grill_all_content"),
    url(r'^ajax/finish_all_content', views.finish_all_content, name="finish_all_content"),
    url(r'^ajax/finish_supplement', views.finish_supplement, name="finish_supplement"),
    url(r'^ajax/current_queue', views.current_queue_ajax, name="current_queue_ajax"),
    url(r'^ajax/statistics', views.statistic_page_ajax, name="update_statistics"),
    url(r'^ajax/opinion_statistics', views.opinion_statistics_ajax, name="update_opinion_statistics"),
    url(r'^ajax/pause_statistics', views.pause_statistic_page_ajax, name="update_pause_statistics"),
    url(r'^ajax/s_order_shashlychnik', views.shashlychnik_select_order, name="select_order_shashlychnik"),
    url(r'^current_queue', views.current_queue, name="current_queue"),
    url(r'^production_queue', views.production_queue, name="production_queue"),
    url(r'^order_history', views.order_history, name="order_history"),
    url(r'^cook_interface', views.cook_interface, name="cook_interface"),
    url(r'^c_i_a', views.c_i_a, name="cook_interface_ajax"),
    url(r'^shashlychnik_interface', views.shashlychnik_interface, name="shashlychnik_interface"),
    url(r'^s_i_ajax', views.s_i_a, name="shashlychnik_interface_ajax"),
    url(r'^redirection', views.redirection, name="redirection"),
    url(r'^buyer_queue', views.buyer_queue, name="buyer_queue"),
    url(r'^statistics', views.statistic_page, name="statistics"),
    url(r'^opinion_statistics', views.opinion_statistics, name="opinion_statistics"),
    url(r'^pause_statistics', views.pause_statistic_page, name="pause_statistics"),
    url(r'^logout_link', views.logout_view, name="logout_link"),
    url(r'^evaluation', views.evaluation, name="evaluation"),
    url(r'^evaluate', views.evaluate, name="evaluate"),
    url(r'^customers/$', views.CustomerList.as_view(), name='customer-list'),
    url(r'customer/add/$', views.CustomerCreate.as_view(), name='customer-add'),
    url(r'customer/(?P<pk>[0-9]+)/$', views.CustomerUpdate.as_view(), name='customer-update'),
    url(r'customer/(?P<pk>[0-9]+)/delete/$', views.CustomerDelete.as_view(), name='customer-delete'),
    url(r'^discount_cards/$', views.DiscountCardList.as_view(), name='discount-card-list'),
    url(r'discount_card/add/$', views.DiscountCardCreate.as_view(), name='discount-card-add'),
    url(r'discount_card/(?P<pk>[0-9]+)/$', views.DiscountCardUpdate.as_view(), name='discount-card-update'),
    url(r'discount_card/(?P<pk>[0-9]+)/delete/$', views.DiscountCardDelete.as_view(), name='discount-card-delete'),
    url(r'^deliveries/$', views.DeliveryList.as_view(), name='delivery-list'),
    url(r'delivery/add/$', views.DeliveryCreate.as_view(), name='delivery-add'),
    url(r'delivery/(?P<pk>[0-9]+)/$', views.DeliveryUpdate.as_view(), name='delivery-update'),
    url(r'delivery/(?P<pk>[0-9]+)/delete/$', views.DeliveryDelete.as_view(), name='delivery-delete'),
    url(r'^delivery_orders/$', views.DeliveryOrderList.as_view(), name='delivery-order-list'),
    url(r'delivery_order/add/$', views.DeliveryOrderCreate.as_view(), name='delivery-order-add'),
    url(r'delivery_order/(?P<pk>[0-9]+)/$', views.DeliveryOrderUpdate.as_view(), name='delivery-order-update'),
    url(r'delivery_order/(?P<pk>[0-9]+)/delete/$', views.DeliveryOrderDelete.as_view(), name='delivery-order-delete'),
    url(r'incoming_call/$', views.IncomingCall.as_view(), name='incoming-call'),
]
