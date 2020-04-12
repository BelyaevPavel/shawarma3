/**
 * Created by paul on 12.04.20.
 */
$(document).ready(function () {
    $('form').on('submit', function (event) {
        //event.preventDefault();
        localStorage.removeItem('currentOrder');
        localStorage.setItem('name', $('#id_name').val());
        localStorage.setItem('phone_number', $('#id_phone_number').val());
    });
    var storedOrder = localStorage.getItem('currentOrder');
    if (storedOrder != null) {
        currOrder = JSON.parse(storedOrder);
        $('#id_order_content').val(storedOrder);
        CalculateTotal();
        UpdateBasket();
    }
    var storedName = localStorage.getItem('name');
    if (storedName != null)
        $('#id_name').val(storedName);
    var storedPhoneNumber = localStorage.getItem('phone_number');
    if (storedPhoneNumber != null)
        $('#id_phone_number').val(storedPhoneNumber);
});