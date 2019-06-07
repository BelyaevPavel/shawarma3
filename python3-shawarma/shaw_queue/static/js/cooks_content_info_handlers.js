$(document).ready(function () {
        refresher();
    }
);

function refresher() {
    //console.log('Refreshed');
    $.ajax({
        url: $('#urls').attr('data-refresh-url'),
        success: function (data) {
            $('#cooks-info-content').html(data['html']);
        },
        complete: function () {
            setTimeout(refresher, 1000);
        }
    });
}