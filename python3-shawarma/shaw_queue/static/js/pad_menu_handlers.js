const menuBlocks = $('.pad-menu__block');
const basket = $('.new-menu__basket');
const totalDisplay = $('#total-display');
const noteInput = $('#item-note');
let currOrder = new Array(0);
let toppings = new Array(0);
let current_retries = 0;
const max_retries = 135;
let total = 0;

$(document).ready(function () {
    $('.pad-menu__button').click(UpdateToppings);
    $('#cook_auto').prop('checked', true);

    noteInput.keyup(
        function (event) {
            ss();
        }
    );

})

function GoToSubmenu(menuBlockId) {
    menuBlocks.hide();
    $('#' + menuBlockId).show();
}

function AddToOrder(id, title, price) {
    const quantity = 1;
    const note = noteInput.val();
    const index = FindItem(id, note, toppings);
    if (index == null) {
        currOrder.push(
            {
                'id': id,
                'title': title,
                'price': price,
                'quantity': quantity,
                'note': note,
                'toppings': toppings.slice(),
            }
        );
    } else {
        currOrder[index]['quantity'] = parseInt(quantity) + parseInt(currOrder[index]['quantity']);
    }
    CalculateTotal();
    DrawOrderTable();
}

function RegisterTopping(id, title, price) {
    let found = false;
    for (let i = 0; i < toppings.length; i++)
        if (toppings[i]['id'] == id) {
            toppings.splice(i, 1);
            found = true;
            break;
        }
    if (!found)
        toppings.push({
            'id': id,
            'title': title,
            'price': price
        });
    console.log(toppings);
}

function ClearToppings() {
    toppings = [];
    console.log(currOrder);
}

function UpdateToppings() {
    let visibleBlock = $('.pad-menu__block:target .pad-menu__button').removeClass('pad-menu__button_enabled');
    for (let i = 0; i < toppings.length; i++)
        visibleBlock.filter('[topping_id=' + toppings[i]['id'] + ']').addClass('pad-menu__button_enabled');
    console.log(currOrder);
}

function FindItem(id, note, toppings) {
    let index = null;
    for (let i = 0; i < currOrder.length; i++) {
        if (currOrder[i]['id'] === id && currOrder[i]['note'] === note) {
            let match = true
            if (currOrder[i]['toppings'].length === undefined) {
                if (toppings.length !== 0)
                    match = false;
            } else {
                if (currOrder[i]['toppings'].length === toppings.length) {
                    for (let j = 0; j < currOrder[i]['toppings'].length; j++) {
                        match = false;
                        for (let k = 0; k < toppings.length; k++) {
                            if (currOrder[i]['toppings'][j]['id'] === toppings[j]['id']) {
                                match = true;
                                break;
                            }
                        }
                        if (!match)
                            break;
                    }
                } else
                    match = false;
            }
            if (match) {
                index = i;
                break;
            }
        }
    }
    return index;
}

function CalculateTotal() {
    total = 0;
    for (let i = 0; i < currOrder.length; i++) {
        let singlePrice = currOrder[i]['price'];
        for (let j = 0; j < currOrder[i]['toppings'].length; j++)
            singlePrice += currOrder[i]['toppings'][j]['price'];
        total += singlePrice * currOrder[i]['quantity'];
    }
    console.log("Total=", total);
    totalDisplay.text(total);
}

function DrawOrderTable() {
    let newHtml = "";
    for (let i = 0; i < currOrder.length; i++) {
        newHtml += "<div class=\"new-menu__basket-item\">";
        newHtml += "<div class=\"new-menu__basket-title\"><span>" + currOrder[i]['title'] +
            "</span><span>x" + currOrder[i]['quantity'] + "</span><span>" + currOrder[i]['price'] +
            " p.</span><button class=\"small-btn danger\" onclick='MinusOneItem(" + i + ")'>-1</button></div>";
        newHtml += "<div class=\"new-menu__basket-toppings\">";
        for (let j = 0; j < currOrder[i]['toppings'].length; j++)
            newHtml += "<div class=\"new-menu__basket-topping\">" +
                "<span>" + currOrder[i]['toppings'][j]['title'] + "</span><span>" + currOrder[i]['toppings'][j]['price'] + " p.</span>" +
                "<button class=\"small-btn danger\" onclick='RemoveTopping(" + i + "," + j + ")'>-1</button>" +
                "</div>"
        if (currOrder[i]['note'])
            newHtml += "<div class=\"new-menu__basket-topping\"><span>" + currOrder[i]['note'] + "</span></div>"
        newHtml += "</div>";
        newHtml += "</div>";
    }
    basket.html(newHtml);
}

function MinusOneItem(index) {
    if (currOrder[index]['quantity'] - 1 > 0) {
        currOrder[index]['quantity'] -= 1;
    } else {
        currOrder[index]['quantity'] = 0;
        currOrder.splice(index, 1);
    }
    CalculateTotal();
    DrawOrderTable();
}

function RemoveTopping(itemIndex, toppingIndex) {
    currOrder[itemIndex]['toppings'].splice(toppingIndex, 1);
    CalculateTotal();
    DrawOrderTable();
}

function SendOrder() {
    if (currOrder.length > 0) {
        current_retries = 0;
        const OK = $('#status-OK-button');
        const cancel = $('#status-cancel-button');
        const retry = $('#status-retry-button');
        const retry_cash = $('#status-retry-cash-button');
        const change_label = $('#order-change-label');
        const change = $('#order-change');
        const change_display = $('#change-display');
        const status = $('#status-display');
        const payment_choose = $('[name=payment_choose]:checked');
        const loading_indiactor = $('#loading-indicator');
        const is_modal = $('#is-modal');
        const confirmation = confirm("Подтвердить заказ?");
        const form = $('.subm');

        if (confirmation == true) {
            ShowModalStatus();
            OK.prop('disabled', true);
            cancel.prop('disabled', true);
            retry.prop('disabled', true);
            loading_indiactor.show();
            status.text('Отправка заказа...');
            if (payment_choose.val() == "paid_with_cash") {
                change.show();
                change.select();
                change_label.show();
                change_display.show();
            }
            const order_data = {
                "order_content": JSON.stringify(currOrder),
                "payment": $('[name=payment_choose]:checked').val(),
                "cook_choose": $('[name=cook_choose]:checked').val(),
                "discount": $('[name=discount]:checked').val() ? parseFloat($('[name=discount]:checked').val()) : 0
            };
            const order_id = $('#order_id').val();
            if (order_id)
                order_data["order_id"] = order_id;

            $('.subm').prop('disabled', true);
            $.ajaxSetup({
                beforeSend: function (xhr, settings) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken)
                }
            });
            $.ajax({
                    type: 'POST',
                    url: form.attr('data-send-url'),
                    data: order_data,
                    dataType: 'json',
                    success: function (data) {
                        if (data['success']) {
                            if (payment_choose.val() != "not_paid") {
                                if (payment_choose.val() == "paid_with_cash") {
                                    status.text('Заказ №' + data.display_number + ' добавлен! Введите полученную сумму:');
                                    //var cash = prompt('Заказ №' + data.daily_number + ' добавлен!, Введите полученную сумму:', "");
                                    //alert("Сдача: " + (parseInt(cash) - total))
                                } else {
                                    status.text('Заказ №' + data.display_number + ' добавлен! Активация платёжного терминала...');
                                    //alert('Заказ №' + data.daily_number + ' добавлен!');
                                }
                                setTimeout(function () {
                                    StatusRefresher(data['guid']);
                                }, 1000);
                            } else {
                                status.text('Заказ №' + data.display_number + ' добавлен!');
                                OK.prop('disabled', false);
                                cancel.prop('disabled', true);
                                retry.prop('disabled', true);
                                if (is_modal.val() == 'True') {
                                    OK.off('click');
                                    OK.unbind('click', OKHandeler);
                                    OK.click(function () {
                                        DeliveryOKHandeler(data['pk']);
                                    });
                                }
                                OK.focus();
                                loading_indiactor.hide();
                            }

                        } else {
                            status.text(data['message']);
                            OK.prop('disabled', true);
                            cancel.prop('disabled', false);
                            retry.prop('disabled', false);
                            loading_indiactor.hide();
                        }
                    }
                }
            ).fail(function () {
                loading_indiactor.hide();
                status.text('Необработанное исключение!');
            });
        }
    } else {
        alert("Пустой заказ!");
    }
}

function ShowModalStatus() {
    const retry_cash = $('#status-retry-cash-button');
    const change_label = $('#order-change-label');
    const change = $('#order-change');

    // Get the modal
    const modal = document.getElementById('modal-status');
    retry_cash.hide();

    modal.style.display = "block";
}

function StatusRefresher(guid) {
    var status = $('#status-display');
    var OK = $('#status-OK-button');
    var cancel = $('#status-cancel-button');
    var retry = $('#status-retry-button');
    var retry_cash = $('#status-retry-cash-button');
    var payment_choose = $('[name=payment_choose]:checked');
    var loading_indiactor = $('#loading-indicator');
    if (current_retries < max_retries) {
        current_retries++;
        status.text('Попытка ' + current_retries + ' из ' + max_retries);
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken)
            }
        });
        $.ajax({
                type: 'POST',
                url: $('#menu-urls').attr('data-status-refresh-url'),
                data: {
                    "order_guid": guid
                },
                dataType: 'json',
                success: function (data) {
                    if (data['success']) {
                        switch (data['status']) {
                            case 0:
                                setTimeout(function () {
                                    StatusRefresher(data['guid']);
                                }, 1000);
                                break;
                            case 397:
                            case 396:
                            case 395:
                            case 394:
                            case 391:
                            case 390:
                                OK.prop('disabled', true);
                                cancel.prop('disabled', false);
                                retry.prop('disabled', false);
                                if (payment_choose.val() != "paid_with_cash")
                                    retry_cash.show();
                                break;
                            // case 396:
                            //     OK.prop('disabled', true);
                            //     cancel.prop('disabled', false);
                            //     retry.prop('disabled', false);
                            //     break;
                            case 393:
                            case 392:
                                if (payment_choose == "paid_with_cash")
                                    status.text('Заказ №' + data.daily_number + '. ' + data['message'] + ' Введите полученную сумму, отдайте клиенту сдачу и нажмите ОК');
                                else
                                    status.text('Заказ №' + data.daily_number + '. ' + data['message'] + ' проведён в 1С! Операция безналичного расчёта завершена успешно! Нажмите ОК');
                                OK.prop('disabled', false);
                                cancel.prop('disabled', true);
                                retry.prop('disabled', true);
                                OK.focus();
                                break;
                            case 200:
                                if (payment_choose.val() == "paid_with_cash")
                                    status.text('Заказ №' + data.daily_number + ' проведён в 1С! Введите полученную сумму, отдайте клиенту сдачу и нажмите ОК');
                                else
                                    status.text('Заказ №' + data.daily_number + ' проведён в 1С! Операция безналичного расчёта завершена успешно! Нажмите ОК');
                                OK.prop('disabled', false);
                                cancel.prop('disabled', true);
                                retry.prop('disabled', true);
                                OK.focus();
                                break;
                            default:
                                OK.prop('disabled', true);
                                cancel.prop('disabled', false);
                                retry.prop('disabled', false);
                                break;
                        }
                        if (data['status'] != 0)
                            loading_indiactor.hide();
                        if (data['status'] != 200)
                            status.text('Заказ №' + data.daily_number + '. ' + data['message']);
                    } else {
                        OK.prop('disabled', true);
                        cancel.prop('disabled', false);
                        retry.prop('disabled', false);
                        status.text(data['message']);
                        loading_indiactor.hide();
                    }
                }
            }
        ).fail(function () {
            OK.prop('disabled', false);
            cancel.prop('disabled', true);
            retry.prop('disabled', true);
            loading_indiactor.hide();
            status.text('Необработанное исключение!');
        });
    } else {
        OK.prop('disabled', false);
        cancel.prop('disabled', true);
        retry.prop('disabled', true);
        status.text('Превышено количество попыток!');
    }
}

function OKHandeler() {
    currOrder = [];
    DrawOrderTable();
    CalculateTotal();
    $('#cook_auto').prop('checked', true);
    CloseModalStatus();
    console.log('OKHandler fired.');
    location.reload();
}

function DeliveryOKHandeler(order_pk) {
    var modal_window = $('#modal-menu');
    var customer_pk = $('#current-order-data').attr('customer-pk');
    //CreateDeliveryOrder(-1, customer_pk, -1, order_pk);
    $("#id_order").val(order_pk);
    $("#id_moderation_needed").val("False");
    currOrder = [];
    DrawOrderTable();
    CalculateTotal();
    $('#cook_auto').prop('checked', true);
    CloseModalStatus();
    // location.reload();
    modal_window.html('');
    modal_window.hide();
    CheckOrderIdPresence();
    console.log('DeliveryOKHandeler fired.');
}

function CancelHandler() {
    currOrder = [];
    DrawOrderTable();
    CalculateTotal();
    $('#cook_auto').prop('checked', true);
    CloseModalStatus();
    console.log('CancelHandler fired.');
    location.reload();
}

function RetryHandler() {
    CloseModalStatus();
    SendOrder();
}

function RetryCashHandler() {
    $('#paid_with_cash').prop('checked', true);
    CloseModalStatus();
    SendOrder();
}

function CloseModalStatus() {
    var change_label = $('#order-change-label');
    var change = $('#order-change');
    var change_display = $('#change-display');
    var retry_cash = $('#status-retry-cash-button');
    var modal = document.getElementById('modal-status');

    change.val(0);
    change.hide();
    change_label.hide();
    change_display.text("Сдача...");
    change_display.hide();
    retry_cash.hide();

    modal.style.display = "none";
}

function ss() {
//     var input = $('#note-' + index);
//     var input_pos = input.position();
//     var searchTerm = $('#note-' + index).val();
    const input = $('#item-note');
    const input_pos = input.position();
    const searchTerm = input.val();
    // currOrder[index]['note'] = searchTerm;
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#menu-urls').attr('data-search-comment'),
            data: {
                "id": 0,
                "note": searchTerm
            },
            dataType: 'json',
            success: function (data) {
                $('#dropdown-list-container').html(data['html']);
                var dropdown_list = $('#dropdown-list');
                var is_visible = isScrolledIntoView(dropdown_list);

                dropdown_list.css({
                    left: input_pos.left,
                    top: is_visible ? input_pos.top + input.height() - 10 : input_pos.top - dropdown_list.height() - input.height() - 25,
                    position: 'absolute'
                });
                dropdown_list.append('<div id="close-cross">x</div>');
                $('#close-cross').css({
                    left: dropdown_list.width() + 10,
                    top: 5,
                    position: 'absolute',
                    cursor: 'pointer'
                });
                $('#close-cross').click(function () {
                    $('#dropdown-list').remove();
                });
            }
        }
    ).fail(function (jqXHR, textStatus) {
        alert('Необработанное искюение!' + textStatus);
        console.log(jqXHR + ' ' + textStatus);
    });


    $('.live-search-list li').each(function () {

        if ($(this).filter('[data-search-term *= ' + searchTerm + ']').length > 0 || searchTerm.length < 1) {
            $(this).show();
        } else {
            $(this).hide();
        }

    });
}

function SelectSuggestion(id, note) {
    // var newnote = prompt("Комментарий", note);
    // if (newnote != null) {
    //     var index = FindItem(id, note);
    //     if (index != null) {
    //         currOrder[index]['note'] = newnote;
    //     }
    // }
    //$('#note-' + id).val(note);
    $('#dropdown-list-container').html('');
    $('#item-note').val(note);
    // if (id != null) {
    //     currOrder[id]['note'] = $('#item-note').val();
    // }
    // DrawOrderTable();
}

function isScrolledIntoView(elem) {
    const $elem = $(elem);
    const $window = $(window);

    const docViewTop = window.scrollY;
    const docViewBottom = docViewTop + window.innerHeight;

    const elemTop = $elem.offset().top;
    const elemBottom = elemTop + $elem.height();

    return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
}