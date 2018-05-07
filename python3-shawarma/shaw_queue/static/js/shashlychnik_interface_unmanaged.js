/**
 * Created by paul on 27.04.18.
 */

$(document).ready(function () {
    Refresher();
});
var csrftoken = $("[name=csrfmiddlewaretoken]").val();

function Refresher() {
    //console.log("NextRefresher");
    var url = $('#urls').attr('data-ajax');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
        type: 'POST',
        url: url,
        dataType: 'json',
        data: {},
        success: function (data) {
            //console.log("success");
            //console.log(data['html']);
            $('#content').html(data['html']);
        },
        complete: function () {
            setTimeout(Refresher, 5000);
        }
    }).fail(function () {
    });
}


function FinishAllContent(id) {
    var url = $('#urls').attr('data-finish-all-content-url');
    var confirmation = true;
    if (confirmation) {
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
                //alert('Положите в заказ №' + data['order_number']);
            },
            complete: function () {
                location.reload();
            }
        });
    }
}