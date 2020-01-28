/**
 * Created by paul on 12.07.17.
 */
function ReadyOrder(id) {
    var url = $('#urls').attr('data-ready-url');
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
function EditOrder(id) {
    var url = $('#urls').attr('edit-order-url');
    //var confirmation = confirm("Заказ готов?");
    //if (confirmation) {
    console.log(id + ' ' + url);
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
        type: 'GET',
        url: url,
        data: {
            'order_id': id,
            'modal_mode': true
        },
        dataType: 'json',
        success: function (data) {
            if (data['success']) {
                $('#modal-menu').html(data['html']);
                $('#modal-menu').css("display", "block");
                currOrder = data['order_content'];
                CalculateTotal();
                DrawOrderTable();
            }
        }
    });
    //}
}

function PayOrderCash(id) {
    var url = $('#urls').attr('data-pay-url');
    var quantity_inputs_values = $('.quantityInput').map(
        function () {
            return parseFloat((this.value).replace(/,/g, '.'));
        }).get();
    var quantity_inputs_ids = $('.quantityInput').map(
        function () {
            return $(this).attr('item-id');
        }).get();
    var prices = $('.quantityInput').map(
        function () {
            return parseFloat($(this).attr('cost'));
        }).get();
    var total_cost = 0;
    for (var i = 0; i < quantity_inputs_values.length; i++) {
        total_cost += prices[i] * quantity_inputs_values[i];
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
                if (data['success']) {
                    alert("К оплате: " + data['total']);
                    location.href = $('#current-queue').parent().attr('href');
                }
                else {
                    alert(data['message']);
                }
                //if (data['success']) {
                //    alert('Success!');
                //}
            }
        });
    }
}

function CalculateCurrentCost() {
    // var message = ($.map($('input.quantityInput'), function (elem, i) {
    //     return parseFloat(elem.value)*parseFloat(elem.attr('cost')) || 0;
    // }).reduce(function (a, b) {
    //     return a + b;
    // }, 0));
    var message = 0;
    $('input.quantityInput').each(function () {
        console.log(message + " " + parseFloat($(this).val().replace(/,/g, '.')) + " " + parseFloat($(this).attr('cost')));
        message = message + parseFloat($(this).val().replace(/,/g, '.')) * parseFloat($(this).attr('cost'));
    });
    message = parseFloat(message).toFixed(2);
    alert(message + " р.");
}

function UpdateItemQuantity(event) {
    var url = $('#urls').attr('data-update-quantity-url');
    var quantity_inputs_values = parseFloat((event.target.value).replace(/,/g, '.'));
    var quantity_inputs_ids = $(event.target).attr('item-id');

    console.log(quantity_inputs_ids + " " + quantity_inputs_values + " " + $(event.target).is(':valid'));
    if ($(event.target).is(':valid')) {
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
            type: 'POST',
            url: url,
            data: {
                'new_quantity': JSON.stringify(quantity_inputs_values),
                'item_id': JSON.stringify(quantity_inputs_ids)
            },
            dataType: 'json',
            success: function (data) {
                if (!data['success']) {
                   alert(data['message']);
                }
                else {
                    $('#total-td').text(data['new_total']);
                }
            }
        });
    }
    else {
        alert('Количество введено неверно!');
    }

}

function PayOrderCard(id) {
    var url = $('#urls').attr('data-pay-url');
    var quantity_inputs_values = $('.quantityInput').map(
        function () {
            return parseFloat((this.value).replace(/,/g, '.'));
        }).get();
    var quantity_inputs_ids = $('.quantityInput').map(
        function () {
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
    $.get('/shaw_queue/order/print/' + order_id + '/');
}

function CancelItem(id) {
    var url = $('#urls').attr('data-cancel-item-url');
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
                // if (data['success']) {
                //     alert('Успех!');
                // }
            },
            complete: function () {
                location.reload();
            }
        });
    }
}


function FinishCooking(id) {
    var url = $('#urls').attr('data-finish-item-url');
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
    var url = $('#urls').attr('data-grill-all-content-url');
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
    var url = $('#urls').attr('data-finish-all-content-url');
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
