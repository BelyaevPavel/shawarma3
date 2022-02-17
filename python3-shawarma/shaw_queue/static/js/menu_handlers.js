/**
 * Created by paul on 15.07.17.
 */
var preorder_checkbox;
const channel = new BroadcastChannel('app-data');

$(document).ready(function () {
    $('#menu').addClass('header-active');
    $('.menu-item').hide();
    $('.subm').prop('disabled', false);
    $('#cook_none').prop('checked', true);
    $('[name="discount"]').prop('checked', false);
    preorder_checkbox = $('[name=preorder_checkbox]');
    preorder_checkbox.prop("checked", false);

    // Get the modal
    var modal = document.getElementById('modal-edit');
    var modalStatus = document.getElementById('modal-status');

    // Get the <span> element that closes the modal
    var span = document.getElementById("close-modal");
    var spanStatus = document.getElementById("close-modal-status");

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
});

var currOrder = [];
var current_retries = 0;
var max_retries = 135;
var total = 0;
var res = "";
var csrftoken = $("[name=csrfmiddlewaretoken]").val();

$(function () {
    $('.subm').on('click', SendOrder);
});

function SendOrder() {
    if (currOrder.length > 0) {
        current_retries = 0;
        var OK = $('#status-OK-button');
        var cancel = $('#status-cancel-button');
        var retry = $('#status-retry-button');
        var retry_cash = $('#status-retry-cash-button');
        var change_label = $('#order-change-label');
        var change = $('#order-change');
        var change_display = $('#change-display');
        var status = $('#status-display');
        var payment_choose = $('[name=payment_choose]:checked');
        var loading_indiactor = $('#loading-indicator');
        var is_modal = $('#is-modal');
        var confirmation = confirm("Подтвердить заказ?");
        var form = $('.subm');

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
            var order_data = {
                "order_content": JSON.stringify(currOrder),
                "payment": $('[name=payment_choose]:checked').val(),
                "cook_choose": $('[name=cook_choose]:checked').val(),
                "discount": $('[name=discount]:checked').val() ? parseFloat($('[name=discount]:checked').val()) : 0,
                "is_preorder": preorder_checkbox.prop("checked") ? 1 : 0
            };
            var order_id = $('#order_id').val();
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
                                }
                                else {
                                    status.text('Заказ №' + data.display_number + ' добавлен! Активация платёжного терминала...');
                                    //alert('Заказ №' + data.daily_number + ' добавлен!');
                                }
                                setTimeout(function () {
                                    StatusRefresher(data['guid']);
                                }, 1000);
                            }
                            else {
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

                        }
                        else {
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
    }
    else {
        alert("Пустой заказ!");
    }
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
                    }
                    else {
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
    }
    else {
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

function Remove(index) {
    var quantity = $('#count-to-remove-' + index).val();
    if (currOrder[index]['quantity'] - quantity <= 0)
        currOrder.splice(index, 1);
    else
        currOrder[index]['quantity'] = parseInt(currOrder[index]['quantity']) - parseInt(quantity);
    CalculateTotal();
    DrawOrderTable();
    channel.postMessage(JSON.stringify(currOrder));
}

function AddOne(id, title, price) {
    var quantity = 1;
    var note = '';
    var index = FindItem(id, note);
    if (index == null) {
        currOrder.push(
            {
                'id': id,
                'title': title,
                'price': price,
                'quantity': quantity,
                'note': note
            }
        );
    }
    else {
        currOrder[index]['quantity'] = parseInt(quantity) + parseInt(currOrder[index]['quantity']);
    }
    channel.postMessage(JSON.stringify(currOrder));
    CalculateTotal();
    DrawOrderTable();
}

function EditNote(id, note) {
    var newnote = prompt("Комментарий", note);
    if (newnote != null) {
        var index = FindItem(id, note);
        if (index != null) {
            currOrder[index]['note'] = newnote;
        }
    }
    DrawOrderTable();
}

function SelectSuggestion(id, note) {
    // var newnote = prompt("Комментарий", note);
    // if (newnote != null) {
    //     var index = FindItem(id, note);
    //     if (index != null) {
    //         currOrder[index]['note'] = newnote;
    //     }
    // }
    $('#note-' + id).val(note);
    $('#item-note').val(note);
    if (id != null) {
        currOrder[id]['note'] = $('#item-note').val();
    }
    DrawOrderTable();
    channel.postMessage(JSON.stringify(currOrder));
}

function Add(id, title, price) {
    var quantity = $('#count-' + id).val();
    var note = $('#note-' + id).val();
    $('#note-' + id).val('');
    $('#count-' + id).val('1');
    var index = FindItem(id, note);
    if (index == null) {
        currOrder.push(
            {
                'id': id,
                'title': title,
                'price': price,
                'quantity': quantity,
                'note': note
            }
        );
    }
    else {
        currOrder[index]['quantity'] = parseInt(quantity) + parseInt(currOrder[index]['quantity']);
    }
    CalculateTotal();
    DrawOrderTable();
    channel.postMessage(JSON.stringify(currOrder));
}

function PlusOneItem(index) {
    var quantity = $('#item-quantity');
    currOrder[index]['quantity'] += 1;
    quantity.val(currOrder[index]['quantity']);
    CalculateTotal();
    DrawOrderTable();
    channel.postMessage(JSON.stringify(currOrder));
}

function MinusOneItem(index) {
    var quantity = $('#item-quantity');
    var modal = document.getElementById('modal-edit');
    if (currOrder[index]['quantity'] - 1 > 0) {
        currOrder[index]['quantity'] -= 1;
        quantity.val(currOrder[index]['quantity']);
    }
    else {
        currOrder[index]['quantity'] = 0;
        currOrder.splice(index, 1);
        CloseModalEdit();
    }
    CalculateTotal();
    DrawOrderTable();
    channel.postMessage(JSON.stringify(currOrder));
}

function UpdateQuantity(index) {
    var quantity = $('#item-quantity');
    var modal = document.getElementById('modal-edit');
    var aux_quantity = parseFloat((quantity.val()).replace(/,/g, '.'));
    if (aux_quantity > 0) {
        currOrder[index]['quantity'] = aux_quantity;
        quantity.val(currOrder[index]['quantity']);
    }
    else {
        currOrder[index]['quantity'] = 0;
        currOrder.splice(index, 1);
        CloseModalEdit();
    }
    CalculateTotal();
    DrawOrderTable();
    channel.postMessage(JSON.stringify(currOrder));
}

function FindItem(id, note) {
    var index = null;
    for (var i = 0; i < currOrder.length; i++) {
        if (currOrder[i]['id'] == id && currOrder[i]['note'] == note) {
            index = i;
            break;
        }
    }
    return index;
}

// onclick="EditNote(' + currOrder[i]['id'] + ',\'' + currOrder[i]['note'] + '\')"
// <div id="dropdown-list-container"></div>
function DrawOrderTable() {
    $('#menu-order-display tbody tr').remove();
    for (var i = 0; i < currOrder.length; i++) {
        $('#menu-order-display').append(
            // '<tr class="currentOrderRow" index="' + i + '"><td class="currentOrderTitleCell" onclick="ShowModalEdit(' + i + ')">' +
            // '<div>' + currOrder[i]['title'] + '</div><div class="noteText">' + currOrder[i]['note'] + '</div>' +
            // '</td><td class="currentOrderActionCell">' + 'x' + currOrder[i]['quantity'] +
            // '<input type="text" value="1" class="quantityInput" id="count-to-remove-' + i + '">' +
            // '<button class="btnRemove" onclick="Remove(' + i + ')">Убрать</button>' +
            // '<input type="text" value="' + currOrder[i]['note'] + '" class="live-search-box" id="note-' + i + '" onkeyup="ss(' + i + ','+currOrder[i]['id']+')">' +
            // '' +
            // '</td></tr>'
            '<tr class="currentOrderRow" index="' + i + '"><td class="currentOrderTitleCell" onclick="ShowModalEdit(' + i + ')">' +
            '<div class="table-item-title">' + currOrder[i]['title'] + '</div><div class="noteText">' + currOrder[i]['note'] + '</div>' +
            '</td><td class="currentOrderActionCell">' + 'x' + currOrder[i]['quantity'] + '<button class="small-btn danger" onclick="MinusOneItem(' + i + ')">-1</button></td></tr>'
        );
    }
}

function ShowModalEdit(index) {
    var title = $('#item-title');
    var quantity = $('#item-quantity');
    var note = $('#item-note');
    var plus = $('#plus-button');
    var minus = $('#minus-button');

    var cheese = $('#cheese-button');
    var greens = $('#greens-button');
    var spicy = $('#spicy-button');
    var spicy30 = $('#spicy30-button');
    var yellow = $('#yellow-button');
    var noOnion = $('#noOnion-button');
    var saucePlus = $('#saucePlus-button');
    var sauceMinus = $('#sauceMinus-button');
    var noVegetables = $('#noVegetables-button');
    var frenchFries = $('#frenchFries-button');
    var chile = $('#chile-button');
    var mushrooms = $('#mushrooms-button');
    var jalapeno = $('#jalapeno-button');
    var bellPepper = $('#bellPepper-button');

    title.text(currOrder[index]['title']);
    quantity.val(currOrder[index]['quantity']);
    quantity.blur(
        function () {
            UpdateQuantity(index);
        }
    );
    quantity.keyup(
        function (event) {
            if (event.keyCode === 13) {
                UpdateQuantity(index);
                CloseModalEdit();
            }
        }
    );
    note.val(currOrder[index]['note']);
    note.keyup(
        function (event) {
            if (event.keyCode === 13) {
                SelectSuggestion(index, note.val());
                CloseModalEdit();
            }
            else {
                ss(index, currOrder[index]['id']);
            }
        }
    );
    note.blur(
        function () {
            SelectSuggestion(index, note.val());
        }
    );
    plus.click(
        function () {
            PlusOneItem(index);
        }
    );
    minus.click(
        function () {
            MinusOneItem(index);
        }
    );
    cheese.click(
        function () {
            var str = ' Сыр';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    greens.click(
        function () {
            var str = ' Зелень';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    spicy.click(
        function () {
            var str = ' Острая';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    spicy30.click(
        function () {
            var str = ' Чуть-Острая';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    yellow.click(
        function () {
            var str = ' Ж';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    noOnion.click(
        function () {
            var str = ' Без лука';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    saucePlus.click(
        function () {
            var str = ' Больше соуса';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    sauceMinus.click(
        function () {
            var str = ' Меньше соуса';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    noVegetables.click(
        function () {
            var str = ' Без овощей';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    frenchFries.click(
        function () {
            var str = ' Фри';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    chile.click(
        function () {
            var str = ' Чили';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    mushrooms.click(
        function () {
            var str = ' Грибы';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    jalapeno.click(
        function () {
            var str = ' Халапеньо';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );
    bellPepper.click(
        function () {
            var str = ' Болгарский перец';
            if (note.val().includes(str)) {
                note.val(note.val().replace(str, ''));
            }
            else {
                note.val(note.val() + str);
            }
            SelectSuggestion(index, note.val());
        }
    );

    // Get the modal
    var modal = document.getElementById('modal-edit');

    modal.style.display = "block";
    note.focus();
}

function CloseModalEdit() {
    var title = $('#item-title');
    var quantity = $('#item-quantity');
    var note = $('#item-note');
    var plus = $('#plus-button');
    var minus = $('#minus-button');

    var cheese = $('#cheese-button');
    var greens = $('#greens-button');
    var spicy = $('#spicy-button');
    var spicy30 = $('#spicy30-button');
    var yellow = $('#yellow-button');
    var noOnion = $('#noOnion-button');
    var saucePlus = $('#saucePlus-button');
    var sauceMinus = $('#sauceMinus-button');
    var noVegetables = $('#noVegetables-button');
    var frenchFries = $('#frenchFries-button');
    var chile = $('#chile-button');
    var mushrooms = $('#mushrooms-button');
    var jalapeno = $('#jalapeno-button');
    var bellPepper = $('#bellPepper-button');

    var modal = document.getElementById('modal-edit');

    quantity.off("blur");
    quantity.off("keyup");
    note.off("keyup");
    note.off("blur");
    plus.off("click");
    minus.off("click");

    cheese.off("click");
    greens.off("click");
    spicy.off("click");
    spicy30.off("click");
    yellow.off("click");
    noOnion.off("click");
    saucePlus.off("click");
    sauceMinus.off("click");
    noVegetables.off("click");
    frenchFries.off("click");
    chile.off("click");
    mushrooms.off("click");
    jalapeno.off("click");
    bellPepper.off("click");

    modal.style.display = "none";
}

function ShowModalStatus() {
    var retry_cash = $('#status-retry-cash-button');
    var change_label = $('#order-change-label');
    var change = $('#order-change');

    // Get the modal
    var modal = document.getElementById('modal-status');
    retry_cash.hide();

    modal.style.display = "block";
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

function CalculateTotal() {
    total = 0;
    for (var i = 0; i < currOrder.length; i++) {
        total += currOrder[i]['price'] * currOrder[i]['quantity'];
    }
    $('p.totalDisplay').each(function () {
        $(this).text(Number(total.toFixed(2)));
    });
}

function CalculateChange() {
    var cash_input = $('#order-change');
    var change_display = $('#change-display');
    var change = parseFloat((cash_input.val()).replace(/,/g, '.')) - total;
    change_display.text('Сдача ' + change + ' р.');
}

function ChangeCategory(category) {
    $('.menu-item').hide();
    $('[category=' + category + ']').show();
}

function ShowDialog(Text) {
    var promptbox = document.createElement('div');
    promptbox.setAttribute('id', 'promptbox');
    promptbox.setAttribute('class', 'promptbox');
    promptbox.innerHTML = '<input class="note-input" id="note-input"/>';
    promptbox.innerHTML = '<button class="note-OK" id="note-OK"/>';
    promptbox.innerHTML = '<button class="note-Cancel" id="note-Cancel"/>';
    $('#note-OK').onclick();
    $('#note-Cancel').onclick();
    $('#note-input').val(Text);
}

function SearchSuggestion(id) {
    var input = $('#note-' + id);
    var input_pos = input.position();
    var old_html = (input.parent()).html();
    var html_st = '<div id="dropdown-list"> sdf</div>';
    (input.parent()).html(old_html + html_st);
    $('#dropdown-list').css({
        left: input_pos.left,
        top: input_pos.top + input.height(),
        position: 'absolute',
        width: input.width()
    });
}

function ss(index, id) {
//     var input = $('#note-' + index);
//     var input_pos = input.position();
//     var searchTerm = $('#note-' + index).val();
    var input = $('#item-note');
    var input_pos = input.position();
    var searchTerm = $('#item-note').val();
    currOrder[index]['note'] = searchTerm;
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#menu-urls').attr('data-search-comment'),
            data: {
                "id": index,
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

function isScrolledIntoView(elem) {
    var $elem = $(elem);
    var $window = $(window);

    var docViewTop = window.scrollY;
    var docViewBottom = docViewTop + window.innerHeight;

    var elemTop = $elem.offset().top;
    var elemBottom = elemTop + $elem.height();

    return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
}
