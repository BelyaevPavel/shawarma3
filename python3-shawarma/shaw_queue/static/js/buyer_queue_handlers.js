/**
 * Created by paul on 21.07.17.
 */
var ready_order_numbers = [];
var is_voicing = false;
var csrftoken = $("[name=csrfmiddlewaretoken]").val();

var carousels = document.querySelectorAll('div.carousel');
var currentCarousel = 0;
var carouselInterval = setInterval(nextCarousel, 20000);
/* Интервал между картинками */

$(document).ready(function () {
        is_voicing = is_voicing_page;
        refresher();
        carousels = document.querySelectorAll('div.carousel');
    }
);

function nextCarousel() {
    carousels[currentCarousel].className = 'carousel';
    currentCarousel = (currentCarousel + 1) % carousels.length;
    carousels[currentCarousel].className = 'carousel demonstration';
}

function refresher() {
    //console.log('Refreshed');
    $.ajax({
        url: $('#urls').attr('data-refresh-url'),
        data: {
            'is_voicing': is_voicing ? 1 : 0
        },
        success: function (data) {
            $('#page-content').html(data['html']);
            var updated_ready_numbers = JSON.parse(data['ready']);
            var voiced_flags = JSON.parse(data['voiced']);
            // var difference = updated_ready_numbers.filter(function (el) {
            //     return !ready_order_numbers.includes(el)
            // });
            if (!is_voicing)
                process_numbers(updated_ready_numbers, voiced_flags);
            //console.log(difference);
            //sound_number(difference);
            /*for(var i=0; i<updated_ready_numbers.length; i++)
             {
             setTimeout(function () {
             aux = updated_ready_numbers[i];
             console.log(aux);
             sound_number(updated_ready_numbers[i]);
             $.ajaxSetup({
             beforeSend: function (xhr, settings) {
             xhr.setRequestHeader("X-CSRFToken", csrftoken)
             }
             });
             $.ajax({
             type: 'POST',
             url: $('#urls').attr('data-unvoice-url'),
             data: {"id": updated_ready_numbers[i]},
             dataType: 'json',
             success: function (data) {
             }
             }
             ).fail(function () {
             // alert('У вас нет прав!');
             });
             }, 3000);
             }*/

        },
        complete: function () {
            setTimeout(refresher, 1000);
        }
    });
}

// Test string:
// process_numbers(['55', '161', '110', '115', '16'], [false, false, false, false, false]);
function process_numbers(updated_ready_numbers, voiced_flags) {
    is_voicing = true;
    $.each(updated_ready_numbers, function (index, value) {
        if (!voiced_flags[index]) {
            setTimeout(function () {
                aux = value;
                console.log(aux);
                sound_number(value % 100);
                $.ajaxSetup({
                    beforeSend: function (xhr, settings) {
                        xhr.setRequestHeader("X-CSRFToken", csrftoken)
                    }
                });
                $.ajax({
                        type: 'POST',
                        url: $('#urls').attr('data-unvoice-url'),
                        data: {"daily_number": value},
                        dataType: 'json',
                        success: function (data) {
                            console.log('Success ' + aux);
                        }
                    }
                ).fail(function () {
                    console.log('Failed ' + aux);
                });
            }, 3500 * index);
        }
    });
    setTimeout(function () {
        is_voicing = false;
    }, 3500 * updated_ready_numbers.length);
}

function sound_number(value) {
    var str_value = value.toString();
    var aux_str_100 = '';
    var aux_str_10 = '';
    var aux_str = '#speaker-' + value;
    if ((value > 20 && value % 10 != 0) || value > 100) {
        if (str_value.length == 3) {
            aux_str_100 = '#speaker-' + parseInt(str_value[0]) * 100;
            aux_str_10 = '#speaker-' + parseInt(str_value[1]) * 10;
            aux_str = '#speaker-' + str_value[2];
            console.log(aux_str_100);
            console.log(aux_str_10);
            console.log(aux_str);
            console.log('Playing...');
            setTimeout(function () {
                $('#speaker-order')[0].play();
            }, 0);
            $('#speaker-order')[0].load();
            setTimeout(function () {
                $('#speaker-number')[0].play();
            }, 1250);
            $('#speaker-number')[0].load();
            setTimeout(function () {
                $(aux_str_100)[0].play();
            }, 1750);
            $(aux_str_100)[0].load();

            if (parseInt(str_value[1]) * 10 + parseInt(str_value[2]) > 20) {
                setTimeout(function () {
                    $(aux_str_10)[0].play();
                }, 2250);
                $(aux_str_10)[0].load();
                setTimeout(function () {
                    $(aux_str)[0].play();
                }, 3250);
                $(aux_str)[0].load();
            }
            else {
                setTimeout(function () {
                    $('#speaker-' + str_value[1] + str_value[2])[0].play();
                }, 2500);
                $('#speaker-' + str_value[1] + str_value[2])[0].load();
            }
        }
        else {
            aux_str_10 = '#speaker-' + parseInt(str_value[0]) * 10;
            aux_str = '#speaker-' + str_value[1];
            console.log(aux_str_10);
            console.log(aux_str);
            console.log('Playing...');
            setTimeout(function () {
                $('#speaker-order')[0].play();
            }, 0);
            $('#speaker-order')[0].load();
            setTimeout(function () {
                $('#speaker-number')[0].play();
            }, 1250);
            $('#speaker-number')[0].load();
            setTimeout(function () {
                $(aux_str_10)[0].play();
            }, 1750);
            $(aux_str_10)[0].load();
            setTimeout(function () {
                $(aux_str)[0].play();
            }, 2500);
            $(aux_str)[0].load();
        }

    }
    else {
        console.log(aux_str);
        console.log('Playing...');
        setTimeout(function () {
            $('#speaker-order')[0].play();
        }, 0);
        $('#speaker-order')[0].load();
        setTimeout(function () {
            $('#speaker-number')[0].play();
        }, 1250);
        $('#speaker-number')[0].load();
        setTimeout(function () {
            $(aux_str)[0].play();
        }, 1750);
        $(aux_str)[0].load();
    }
    //ready_order_numbers = ready_order_numbers.push(value);
}
