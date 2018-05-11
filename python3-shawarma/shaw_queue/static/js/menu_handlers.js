/**
 * Created by paul on 15.07.17.
 */
$(document).ready(function () {
    $('#menu').addClass('header-active');
    $('.menu-item').hide();
    $('.subm').prop('disabled', false);

    // Get the modal
    var modal = document.getElementById('modal-edit');

    // Get the <span> element that closes the modal
    var span = document.getElementById("close-modal");

    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
        CloseModal();
    };

    // When the user clicks anywhere outside of the modal, close it
    window.onclick = function(event) {
        if (event.target == modal) {
            CloseModal();
        }
    }
});

var currOrder = [];
var total = 0;
var res = ""
var csrftoken = $("[name=csrfmiddlewaretoken]").val();

$(function () {
    $('.subm').on('click', function (event) {
        if (currOrder.length > 0) {
            var confirmation = confirm("Подтвердить заказ?");
            var form = $('.subm');

            if (confirmation == true) {
                $('.subm').prop('disabled', true);
                $.ajaxSetup({
                    beforeSend: function (xhr, settings) {
                        xhr.setRequestHeader("X-CSRFToken", csrftoken)
                    }
                });
                $.ajax({
                        type: 'POST',
                        url: form.attr('data-send-url'),
                        data: {
                            "order_content": JSON.stringify(currOrder),
                            "payment": $('[name=payment_choose]:checked').val(),
                            "cook_choose": $('[name=cook_choose]:checked').val()
                        },
                        dataType: 'json',
                        success: function (data) {
                            if (data['success']) {
                                if ($('[name=payment_choose]:checked').val() == "paid_with_cash") {
                                    var cash = prompt('Заказ №' + data.daily_number + ' добавлен!, Введите полученную сумму:', "");
                                    alert("Сдача: " + (parseInt(cash) - total))
                                }
                                else {
                                    alert('Заказ №' + data.daily_number + ' добавлен!');
                                }
                                currOrder = [];
                                DrawOrderTable();
                                CalculateTotal();
                                $('#cook_auto').prop('checked', true);

                            }
                            else {
                                alert(data['message']);
                            }
                            location.reload();
                        }
                    }
                ).fail(function () {
                    alert('Необработанное исключение!');
                });
            }
            else {
                event.preventDefault();
            }
        }
        else {
            alert("Пустой заказ!");
        }
    });
});


function Remove(index) {
    var quantity = $('#count-to-remove-' + index).val();
    if (currOrder[index]['quantity'] - quantity <= 0)
        currOrder.splice(index, 1);
    else
        currOrder[index]['quantity'] = parseInt(currOrder[index]['quantity']) - parseInt(quantity);
    CalculateTotal();
    DrawOrderTable();
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
}

function PlusOneItem(index) {
    var quantity = $('#item-quantity');
    currOrder[index]['quantity'] += 1;
    quantity.val(currOrder[index]['quantity']);
    CalculateTotal();
    DrawOrderTable();
}

function MinusOneItem(index) {
    var quantity = $('#item-quantity');
    var modal = document.getElementById('modal-edit');
    if(currOrder[index]['quantity'] - 1 > 0)
    {
        currOrder[index]['quantity'] -= 1;
        quantity.val(currOrder[index]['quantity']);
    }
    else {
        currOrder[index]['quantity'] = 0;
        currOrder.splice(index, 1);
        CloseModal();
    }
    CalculateTotal();
    DrawOrderTable();
}

function UpdateQuantity(index) {
    var quantity = $('#item-quantity');
    var modal = document.getElementById('modal-edit');
    var aux_quantity = parseFloat((quantity.val()).replace(/,/g, '.'));
    if(aux_quantity > 0){
        currOrder[index]['quantity'] = aux_quantity;
        quantity.val(currOrder[index]['quantity']);
    }
    else {
        currOrder[index]['quantity'] = 0;
        currOrder.splice(index, 1);
        CloseModal();
    }
    CalculateTotal();
    DrawOrderTable();
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
    $('table.currentOrderTable tbody tr').remove();
    for (var i = 0; i < currOrder.length; i++) {
        $('table.currentOrderTable').append(
            // '<tr class="currentOrderRow" index="' + i + '"><td class="currentOrderTitleCell" onclick="ShowModal(' + i + ')">' +
            // '<div>' + currOrder[i]['title'] + '</div><div class="noteText">' + currOrder[i]['note'] + '</div>' +
            // '</td><td class="currentOrderActionCell">' + 'x' + currOrder[i]['quantity'] +
            // '<input type="text" value="1" class="quantityInput" id="count-to-remove-' + i + '">' +
            // '<button class="btnRemove" onclick="Remove(' + i + ')">Убрать</button>' +
            // '<input type="text" value="' + currOrder[i]['note'] + '" class="live-search-box" id="note-' + i + '" onkeyup="ss(' + i + ','+currOrder[i]['id']+')">' +
            // '' +
            // '</td></tr>'
            '<tr class="currentOrderRow" index="' + i + '"><td class="currentOrderTitleCell" onclick="ShowModal(' + i + ')">' +
            '<div>' + currOrder[i]['title'] + '</div><div class="noteText">' + currOrder[i]['note'] + '</div>' +
            '</td><td class="currentOrderActionCell">' + 'x' + currOrder[i]['quantity'] +'</td></tr>'
        );
    }
}

function ShowModal(index) {
    var title = $('#item-title');
    var quantity = $('#item-quantity');
    var note = $('#item-note');
    var plus = $('#plus-button');
    var minus = $('#minus-button');

    title.text(currOrder[index]['title']);
    quantity.val(currOrder[index]['quantity']);
    quantity.blur(
        function () {
            UpdateQuantity(index);
        }
    );
    note.val(currOrder[index]['note']);
    note.keyup(
        function () {
            ss(index, currOrder[index]['id']);
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

    // Get the modal
    var modal = document.getElementById('modal-edit');

    modal.style.display = "block";
    note.focus();
}

function CloseModal() {
    var title = $('#item-title');
    var quantity = $('#item-quantity');
    var note = $('#item-note');
    var plus = $('#plus-button');
    var minus = $('#minus-button');
    var modal = document.getElementById('modal-edit');

    quantity.off("blur");
    note.off("keyup");
    note.off("blur");
    plus.off("click");
    minus.off("click");

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
            url: $('#urls').attr('data-search-comment'),
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
                    left: dropdown_list.width()+10,
                    top: 5,
                    position: 'absolute',
                    cursor: 'pointer'
                });
                $('#close-cross').click(function () {
                    $('#dropdown-list').remove();
                });
            }
        }
    ).fail(function () {
        alert('У вас нет права добавлять заказ!');
    });


    $('.live-search-list li').each(function () {

        if ($(this).filter('[data-search-term *= ' + searchTerm + ']').length > 0 || searchTerm.length < 1) {
            $(this).show();
        } else {
            $(this).hide();
        }

    });
}

function isScrolledIntoView(elem){
    var $elem = $(elem);
    var $window = $(window);

    var docViewTop = window.scrollY;
    var docViewBottom = docViewTop + window.innerHeight;

    var elemTop = $elem.offset().top;
    var elemBottom = elemTop + $elem.height();

    return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
}
