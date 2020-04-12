/**
 * Created by paul on 12.04.20.
 */

$(document).ready(function () {
    $('form').on('submit', function (event) {
        localStorage.setItem('phone_number', $('#id_phone_number').val());
    });
    $('.order-info-body').click(function () {
        $('.reloadSingle').toggleClass('active');
        $.ajax({
                type: 'GET',
                url: $('#urls').attr('check-order-url'),
                data: {'phone_number': $('#id_phone_number').val()},
                dataType: 'json',
                success: function (data) {
                    $('.reloadSingle').toggleClass('active');
                    if (data['success']) {
                        $('.order-info-body span').text(data['order_status']);
                    }
                    else {
                        $('.order-info-body span').text('Возникла ошибка!');
                        $('.order-info-body').toggleClass('danger');
                    }
                },
                complete: function () {
                },
                // handle a non-successful response
                error: function (xhr, errmsg, err) {
                    alert("Oops! We have encountered an error: " + errmsg); // add the error to the dom
                    console.log(xhr.status + ": " + xhr.responseText); // provide a bit more info about the error to the console
                }
            }
        ).fail(function () {
            alert('Необработанное исключение!');
        });
    });
    var storedPhoneNumber = localStorage.getItem('phone_number');
    if (storedPhoneNumber != null)
        $('#id_phone_number').val(storedPhoneNumber);
});