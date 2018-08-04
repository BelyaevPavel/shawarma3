/**
 * Created by paul on 28.05.18.
 */

$(document).ready(function () {
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
});

function ShowModalEdit(index) {
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
    quantity.keyup(
        function (event) {
            if(event.keyCode === 13){
                UpdateQuantity(index);
                CloseModalEdit();
            }
        }
    );
    note.val(currOrder[index]['note']);
    note.keyup(
        function (event) {
            if(event.keyCode === 13){
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
    if(!currOrder[index]['editable_quantity'])
        plus.attr('disabled','true');
    else
        plus.attr('disabled','false');
    plus.click(
        function () {
            PlusOneItem(index);
        }
    );
    if(!currOrder[index]['editable_quantity'])
        minus.attr('disabled','true');
    else
        minus.attr('disabled','false');
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

function CloseModalEdit() {
    var title = $('#item-title');
    var quantity = $('#item-quantity');
    var note = $('#item-note');
    var plus = $('#plus-button');
    var minus = $('#minus-button');
    var modal = document.getElementById('modal-edit');

    quantity.off("blur");
    quantity.off("keyup");
    note.off("keyup");
    note.off("blur");
    plus.off("click");
    minus.off("click");

    modal.style.display = "none";
}

function UpdateCommodity(id, note, quantity) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#order-specifics-urls').attr('data-update-commodity'),
            data: {
                "id": id,
                "note": note,
                "quantity": quantity
            },
            dataType: 'json',
            success: function (data) {
                if (!data['success'])
                    alert(data['message']);
            }
        }
    ).fail(function () {
        alert('Необработанное исключение!');
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
    UpdateCommodity(id, note, currOrder[id]['quantity']);
    $('#note-' + id).val(note);
    $('#item-note').val(note);
    if (id != null) {
        currOrder[id]['note'] = $('#item-note').val();
    }
    DrawOrderTable();
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
            url: $('#order-specifics-urls').attr('data-search-comment'),
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
    ).fail(function () {
        alert('Необработанное исключение!');
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
    if (currOrder[index]['quantity'] - 1 > 0) {
        currOrder[index]['quantity'] -= 1;
        quantity.val(currOrder[index]['quantity']);
    }
    else {
        currOrder[index]['quantity'] = 0;
        currOrder.splice(index, 1);
        CloseModalEdit();
        CancelItem(index);
    }
    CalculateTotal();
    DrawOrderTable();
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
}

function DrawOrderTable() {
    Object.keys(currOrder).forEach(function (key) {
        var item_container = $('#item-container-'+key);
        var item_note = item_container.children('.item-title-container').children('.order-item-note-modal');
        var item_quantity = item_container.children('.item-quantity-container').children('.quantityInput');
        item_note.text(currOrder[key]['note']);
        item_quantity.val(currOrder[key]['quantity']);
        if(!currOrder[key]['editable_quantity'])
            item_quantity.attr('disabled','true');
        else
            item_quantity.attr('disabled','false');
    });
}

function CalculateTotal() {
    total = 0;
    Object.keys(currOrder).forEach(function (key) {
        total += currOrder[key]['price'] * currOrder[key]['quantity'];
    });
    $('#total-display').text(Number(total.toFixed(2)));
}