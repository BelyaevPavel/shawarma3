/**
 * Created by paul on 12.07.17.
 */
function ReadyOrder(id) {
    var url = $('#urls').attr('data-ready-url');
    var confirmation = confirm("Заказ готов?");
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
    }
}

function PayOrderCash(id) {
    var url = $('#urls').attr('data-pay-url');
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
    var confirmation = confirm("К оплате: " + total_cost);
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
                'paid_with_cash': JSON.stringify(true)
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

function PayOrderCard(id) {
    var url = $('#urls').attr('data-pay-url');
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
                'paid_with_cash': JSON.stringify(false)
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
