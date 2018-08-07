/**
 * Created by paul on 04.08.18.
 */

function StartLongPoll(Number) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
        type: 'POST',
        url: 'ajax/start_long_poll',
        data: {"number": Number},
        dataType: 'json',
        success: function (data) {
            alert(data['message']);
        },
        complete: function () {
            StartLongPoll(Number)
        }
    });
}

function RespondLongPoll(Number) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
        type: 'POST',
        url: 'ajax/respond_long_poll',
        data: {"number": Number},
        dataType: 'json',
        success: function () {
        },
        complete: function () {
        }
    });
}