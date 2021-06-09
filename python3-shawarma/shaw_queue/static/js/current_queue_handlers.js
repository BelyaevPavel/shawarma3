/**
 * Created by paul on 10.07.17.
 */
$(document).ready( function () {
    $('#current-shaw_queue').addClass('header-active');
    refresher();
    // Get the modal
    var modal = document.getElementById('modal-edit');

    // Get the <span> element that closes the modal
    var span = document.getElementById("close-modal-edit");

    // When the user clicks on <span> (x), close the modal
    span.onclick = function () {
        CloseModalEdit();
    };
    // spanStatus.onclick = function () {
    //     CloseModalStatus();
    // };

    // When the user clicks anywhere outside of the modal, close it
    window.onclick = function (event) {
        if (event.target == modal) {
            CloseModalEdit();
        }
        // else {
        //     if (event.target == modalStatus) {
        //         CloseModalStatus();
        //     }
        // }
    }
}
);
var modal_is_opened = false;
var currOrder = []

function refresher() {

    $.ajax({
        url: 'ajax/current_queue_ajax.html',
        success: function (data) {
            if(!modal_is_opened){
                $('div.page-content').html(data['html']);
            }
        },
        complete: function () {
            setTimeout(refresher, 10000);
        }
    });
}

function SetContentPage(order_id, page_number) {
    var content_part = $('#content-part');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#order-specifics-urls').attr('data-get-content-page'),
            data: {"order_id": order_id, "page_number": page_number},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    currOrder = JSON.parse(data['order']);
                    content_part.html(data['html']);
                    content_part.css("display", "block");
                    modal_is_opened = true;
                    DrawOrderTable();
                }
                else{
                    alert(data['message']);
                }
            },
            complete: function () {
            }
        }
    ).fail(function () {
        alert('Необработанное исключение!');
    });
}

function OrderSpecifics(order_id) {
    var order_specifics = $('#modal-order-specifics');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#urls').attr('order-specifics-url'),
            data: {"order_id": order_id},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    currOrder = JSON.parse(data['order']);
                    order_specifics.html(data['html']);
                    order_specifics.css("display", "block");
                    modal_is_opened = true;
                    DrawOrderTable();
                }
                else{
                    alert(data['message']);
                }
            },
            complete: function () {
            }
        }
    ).fail(function () {
        alert('Необработанное исключение!');
    });
}

function CloseOrderSpecifics() {
    var order_specifics = $('#modal-order-specifics');
    order_specifics.html('');
    order_specifics.css("display", "none");
    modal_is_opened = false;
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

function CloseAll() {
    var confirmation = confirm("Закрыть все готовые заказы?");
    if (confirmation == true) {
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
            type: 'POST',
            url: $('#urls').attr('close-all-url'),
            data: {'close_unpaid': $('#close-unpaid').is(':checked')},
            dataType: 'json',
            success: function (data) {
                if (!data['success'])
                    alert(data['message']);

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
                    if (data['success']) {
                        alert('Заказ отменён!');
                    }
                    else {
                        alert(data['message']);
                    }
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
    refresher();
}

// Order Specifics handles part
function ReadyOrder(id) {
    var url = $('#order-specifics-urls').attr('data-ready-url');
    //var confirmation = confirm("Заказ готов?");
    //if (confirmation) {
        console.log(id + ' ' + url);
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'id': id,
                'servery_choose': $('[name=servery_choose]:checked').val()
            },
            dataType: 'json',
            success: function (data) {
                location.href = $('#current-queue').parent().attr('href');
                //if (data['success']) {
                //    alert('Success!');
                //}
            }
        });
    //}
}

function PayOrderCash(id) {
    var url = $('#order-specifics-urls').attr('data-pay-url');
    var quantity_inputs_values = $('.quantityInput').map(
        function()
        {
            return parseFloat((this.value).replace(/,/g, '.'));
        }).get();
    var quantity_inputs_ids = $('.quantityInput').map(
        function()
        {
            return $(this).attr('item-id');
        }).get();
    var prices = $('.quantityInput').map(
        function()
        {
            return parseFloat($(this).attr('cost'));
        }).get();
    var total_cost = 0;
    for(var i = 0; i<quantity_inputs_values.length; i++){
        total_cost +=prices[i]*quantity_inputs_values[i];
    }
    var confirmation = false;
    if (total_cost > 5000)
        confirmation = confirm("Сумма заказа превышает 5000 р. Вы уверены в корректности ввода?");
    else
        confirmation = confirm("Оплатить заказ?");
    if (confirmation) {
        console.log(id + ' ' + url);
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'id': id,
                'values': JSON.stringify(quantity_inputs_values),
                'ids': JSON.stringify(quantity_inputs_ids),
                'paid_with_cash': JSON.stringify(true),
                'servery_id': $('[name=servery_choose]:checked').val()
            },
            dataType: 'json',
            success: function (data) {
                if (data['success'])
                {
                    alert("К оплате: " + data['total']);
                    location.href = $('#current-queue').parent().attr('href');
                }
                else
                {
                    alert(data['message']);
                }
                //if (data['success']) {
                //    alert('Success!');
                //}
            }
        });
    }
}

function PayOrderCard(id) {
    var url = $('#order-specifics-urls').attr('data-pay-url');
    var quantity_inputs_values = $('.quantityInput').map(
        function()
        {
            return parseFloat((this.value).replace(/,/g, '.'));
        }).get();
    var quantity_inputs_ids = $('.quantityInput').map(
        function()
        {
            return $(this).attr('item-id');
        }).get();
    var confirmation = confirm("Заказ оплачен?");
    if (confirmation) {
        console.log(id + ' ' + url);
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'id': id,
                'values': JSON.stringify(quantity_inputs_values),
                'ids': JSON.stringify(quantity_inputs_ids),
                'paid_with_cash': JSON.stringify(false),
                'servery_id': $('[name=servery_choose]:checked').val()
            },
            dataType: 'json',
            success: function (data) {
                location.href = $('#current-queue').parent().attr('href');
                //if (data['success']) {
                //    alert('Success!');
                //}
            }
        });
    }
}

function PrintOrder(order_id) {
    $.get('/shaw_queue/order/print/'+order_id+'/');
}

function CancelItem(id, order_id) {
    var url = $('#order-specifics-urls').attr('data-cancel-item-url');
    var confirmation = confirm("Исключить из заказа?");
    if (confirmation) {
        console.log(id + ' ' + url);
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'id': id
            },
            dataType: 'json',
            success: function (data) {
                CloseOrderSpecifics();
                OrderSpecifics(order_id);
                // if (data['success']) {
                //     alert('Успех!');
                // }
            },
            complete: function () {
                //location.reload();
            }
        });
    }
}


function FinishCooking(id) {
    var url = $('#order-specifics-urls').attr('data-finish-item-url');
    console.log(id + ' ' + url);
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
        type: 'POST',
        url: url,
        data: {
            'id': id
        },
        dataType: 'json',
        success: function (data) {
            //alert('Success!' + data);
        },
        complete: function () {
            location.reload();
        }
    });
}


function GrillAllContent(id) {
    var url = $('#order-specifics-urls').attr('data-grill-all-content-url');
    var confirmation = true;
    if (confirmation) {
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'order_id': id
            },
            dataType: 'json',
            success: function (data) {
                //alert('Положите в заказ №' + data['order_number']);
            },
            complete: function () {
                location.reload();
            }
        });
    }
}


function FinishAllContent(id) {
    var url = $('#order-specifics-urls').attr('data-finish-all-content-url');
    var confirmation = true;
    if (confirmation) {
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'id': id
            },
            dataType: 'json',
            success: function (data) {
                //alert('Положите в заказ №' + data['order_number']);
            },
            complete: function () {
                location.reload();
            }
        });
    }
}
