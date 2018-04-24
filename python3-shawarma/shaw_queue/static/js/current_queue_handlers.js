/**
 * Created by paul on 10.07.17.
 */
$(document).ready( function () {
    $('#current-shaw_queue').addClass('header-active');
    refresher();
}
);

function refresher() {
    $.ajax({
        url: 'ajax/current_queue_ajax.html',
        success: function (data) {
            $('div.page-content').html(data['html']);
        },
        complete: function () {
            setTimeout(refresher, 10000);
        }
    });
}

function CloseOrder(order_id) {
    var confirmation = confirm("Закрыть заказ?");
    if (confirmation == true) {
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
                type: 'POST',
                url: $('#urls').attr('data-close-order-url'),
                data: {"order_id": order_id},
                dataType: 'json',
                success: function (data) {
                    //alert('Заказ закрыт!');
                },
                complete: function () {
                    location.reload();
                }
            }
        ).fail(function () {
            alert('У вас нет прав!');
        });
    }
    else {
        event.preventDefault();
    }
}

function PrintOrder(order_id) {
    var confirmation = confirm("Печатать заказ?");
    if (confirmation == true) {
        $.get('/shaw_queue/order/print/' + order_id + '/');
    }
}

function CancelOrder(order_id) {
    var confirmation = confirm("Отменить заказ?");
    if (confirmation == true) {
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
                type: 'POST',
                url: $('#urls').attr('data-cancel-order-url'),
                data: {"id": order_id},
                dataType: 'json',
                success: function (data) {
                    alert('Заказ отменён!');
                },
                complete: function () {
                    location.reload();
                }
            }
        ).fail(function () {
            alert('У вас нет прав!');
        });
    }
    else {
        event.preventDefault();
    }
}

function VoiceAll() {
    $.get($('#urls').attr('voice-all-url'));
}

function VoiceOrder(id) {
    $.get(id);
}

function RememberFilter(id){
    if ($('#'+id).is(':checked'))
        document.cookie = id+"=True";
    else
        document.cookie = id+"=False";
}
