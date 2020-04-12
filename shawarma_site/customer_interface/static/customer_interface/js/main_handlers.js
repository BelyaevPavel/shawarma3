/**
 * Created by paul on 10.04.20.
 */

var currOrder = [];
var total = 0;
$(document).ready(function () {
    $('.header-burger').click(function (event) {
        $('.header-burger,.header-menu').toggleClass('active');
        $('body').toggleClass('lock');
    });
    $('.basket-spoiler').click(function (event) {
        $('.basket-content').toggleClass('active');
        $('.basket-spoiler').toggleClass('active');
        $('body').toggleClass('lock');
        $('.basket-spoiler button').toggle();
        $('.basket-spoiler a').toggle();
        UpdateBasket();
    });
    $('#btn-clear-basket').click(function (event) {
        currOrder = [];
        localStorage.removeItem('currentOrder');
        CalculateTotal();
        UpdateBasket();
    });
    var storedOrder = localStorage.getItem('currentOrder');
    if (storedOrder != null) {
        currOrder = JSON.parse(storedOrder);
        $('#id_order_content').val(storedOrder);
        CalculateTotal();
        UpdateBasket();
    }
});

function AddOne(id, title, price) {
    console.log(id + ' ' + title + ' ' + price);
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
    UpdateBasket();
    SaveCurrentOrder();
}

function PlusOneItem(index) {
    //var quantity = $('#item-quantity');
    currOrder[index]['quantity'] += 1;
    //quantity.val(currOrder[index]['quantity']);
    CalculateTotal();
    UpdateBasket();
    SaveCurrentOrder();
}

function MinusOneItem(index) {
    // var quantity = $('#item-quantity');
    // var modal = document.getElementById('modal-edit');
    if (currOrder[index]['quantity'] - 1 > 0) {
        currOrder[index]['quantity'] -= 1;
        //quantity.val(currOrder[index]['quantity']);
    }
    else {
        currOrder[index]['quantity'] = 0;
        currOrder.splice(index, 1);
    }
    CalculateTotal();
    UpdateBasket();
    SaveCurrentOrder();
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

function UpdateBasket() {
    var quantity = 0;
    var basketContent = $('.basket-content');
    var basketContentContainer = $('.basket-content .container');
    var basketSpoiler = $('.basket-spoiler');
    basketContentContainer.html('');
    for (var i = 0; i < currOrder.length; i++) {
        basketContentContainer.append(
            '<div class="basket-content-item">' +
            '<div class="item-info">' +
            '<div class="item-name">' + currOrder[i]['title'] + '</div>' +
            '<div class="item-quantity">' + currOrder[i]['quantity'] + '</div>' +
            '</div>' +
            '<div class="item-actions">' +
            '<button class="btn btn-success" onclick="PlusOneItem(' + i + ')">+</button>' +
            '<button class="btn btn-danger" onclick="MinusOneItem(' + i + ')">-</button>' +
            '</div>' +
            '</div>'
        );
        quantity += currOrder[i]['quantity'];
    }
    if (quantity > 0) {
        $('.basket').show();
        if (basketSpoiler.hasClass('active')) {
            var spanValue = "Cумма: " + total + ' р.';
        }
        else {
            var spanValue = "Корзина: ";
            if (quantity < 5)
                spanValue += quantity + ' товара';
            else
                spanValue += quantity + ' товаров';

        }
    }
    else {
        $('.basket').hide();
        basketSpoiler.removeClass('active');
        basketContent.removeClass('active');
    }
    $('.basket-spoiler span').text(spanValue);
}

function CalculateTotal() {
    total = 0;
    for (var i = 0; i < currOrder.length; i++) {
        total += currOrder[i]['price'] * currOrder[i]['quantity'];
    }
}

function SaveCurrentOrder() {
    localStorage.setItem('currentOrder', JSON.stringify(currOrder));
}
