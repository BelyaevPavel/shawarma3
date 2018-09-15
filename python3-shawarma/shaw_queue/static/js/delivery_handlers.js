/**
 * Created by paul on 15.08.18.
 */
// function handleDragStart(e) {
//     this.style.opacity = '0.4';  // this / e.target is the source node.
// }
//
// var cols = document.querySelectorAll('.delivery-block-container');
// [].forEach.call(cols, function (col) {
//     col.addEventListener('dragstart', handleDragStart, false);
// });

$(document).ready(function () {
    UpdateWorkspace();
});

$(window).resize(function () {
    var modal_is_opened = false;
    CalculateGrid();
    console.log("Handler for .resize() called.");
});

function OverrideDeliverySubmition() {
    $('#delivery-order-form').on('submit', function (event) {
        event.preventDefault();
        console.log("form submitted!");  // sanity check
        SendDeliveryOrder();
    });
}

function OverrideIncomingCallSubmition() {
    $('#incoming-call-form').on('submit', function (event) {
        event.preventDefault();
        console.log("form submitted!");  // sanity check
        SendIncomingCall();
    });
}

function CalculateGrid() {
    var workspace = $('#delivery-workspace');
    var block = $('.delivery-block-container');
    var grid_columns = Math.round(workspace.width() / (block.width() + 10));
    var grid_rows = Math.round(workspace.height() / (block.height() + 10));
    var columns_template = "repeat(" + grid_columns + ", " + block.width() + "px)";
    var rows_template = "repeat(" + grid_rows + ", " + block.height() + "px)";
    workspace.css('grid-template-columns', columns_template);
    workspace.css('grid-template-rows', rows_template);
    // workspace.gridTemplateColumns = columns_template;
    // workspace.gridTemplateRows = rows_template;
    // console.log("Columns " + grid_columns);
    // console.log("Rows " + grid_rows);
    // console.log("Columns template " + columns_template);
    // console.log("Rows template " + rows_template);
}

function HideSidebar(SidebarID, ShowButtonID) {
    $('#' + SidebarID).hide();
    $('#' + SidebarID).width(0);
    $('#' + ShowButtonID).show();
    $('#' + ShowButtonID).css('width', '68px');
    var workspace = $('#delivery-workspace');
    var sidebars_width = $('#delivery-left-column').width() + $('#delivery-right-column').width();
    console.log('calc(100% - ' + sidebars_width + 'px - ' + $('#show-left-column').css('width') + ' - ' + $('#show-right-column').css('width') + ')');
    workspace.css('width', 'calc(100% - ' + sidebars_width + 'px - ' + $('#show-left-column').css('width') + ' - ' + $('#show-right-column').css('width') + ')');
    CalculateGrid();
}

function ShowSidebar(SidebarID, ShowButtonID) {
    $('#' + SidebarID).show();
    $('#' + SidebarID).width(300);
    $('#' + ShowButtonID).hide();
    $('#' + ShowButtonID).css('width', '0px');
    var workspace = $('#delivery-workspace');
    var sidebars_width = $('#delivery-left-column').width() + $('#delivery-right-column').width();
    console.log('calc(100% - ' + sidebars_width + 'px - ' + $('#show-left-column').css('width') + ' - ' + $('#show-right-column').css('width') + ')');
    workspace.css('width', 'calc(100% - ' + sidebars_width + 'px - ' + $('#show-left-column').css('width') + ' - ' + $('#show-right-column').css('width') + ')');
    CalculateGrid();
}

function ShowMenu(DeliveryOrderPK = -1) {
    var modal_window = $('#modal-menu');
    if (DeliveryOrderPK != -1)
        var pk_data = {'delivery_order_pk': DeliveryOrderPK};
    else
        var pk_data = {};
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#urls').attr('menu-url'),
            data: pk_data,
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    modal_window.html(data['html']);
                    modal_window.css("display", "block");
                    modal_is_opened = true;
                }
                else {
                    alert(data['message']);
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
}


function CreateDeliveryOrder(DeliveryOrderPK = -1, CustomerPK = -1, DeliveryPK = -1, OrderPK = -1) {
    if (DeliveryOrderPK != -1)
        var pk_data = {'delivery_order_pk': DeliveryOrderPK};
    else
        var pk_data = {};
    if (CustomerPK != -1)
        pk_data['customer_pk'] = CustomerPK;
    if (DeliveryPK != -1)
        pk_data['delivery_pk'] = DeliveryPK;
    if (OrderPK != -1)
        pk_data['order_pk'] = OrderPK;
    var modal_window = $('#modal-delivery-order');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#urls').attr('create-order-url'),
            dataType: 'json',
            data: pk_data,
            success: function (data) {
                if (data['success']) {
                    modal_window.html(data['html']);
                    modal_window.css("display", "block");
                    modal_is_opened = true;
                    OverrideDeliverySubmition();
                }
                else {
                    alert(data['message']);
                }
            },
            complete: function () {
            }
        }
    ).fail(function () {
        alert('Необработанное исключение!');
    });
}


function SendDeliveryOrder() {
    var pk = $('#delivery-order-form').attr('object-pk');
    var modal_window = $('#modal-delivery-order');
    var form_data = {
        'delivery': $('#id_delivery').val(),
        'order': $('#id_order').val(),
        'customer': $('#id_customer').val(),
        'address': $('#id_address').val(),
        'obtain_timepoint': $('#id_obtain_timepoint').val(),
        'delivered_timepoint': $('#id_delivered_timepoint').val(),
        'prep_start_timepoint': $('#id_prep_start_timepoint').val(),
        'preparation_duration': $('#id_preparation_duration').val(),
        'delivery_duration': $('#id_delivery_duration').val(),
        'note': $('#id_note').val(),
    };
    if (pk)
        form_data['delivery_order_pk'] = pk;
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#urls').attr('create-order-url'),
            data: form_data,
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    location.reload();
                }
                else {
                    modal_window.html(data['html']);
                    OverrideDeliverySubmition();
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
}


function CreateIncomingCall() {
    var modal_window = $('#modal-delivery-order');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#urls').attr('incoming-call-url'),
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    modal_window.html(data['html']);
                    modal_window.css("display", "block");
                    modal_is_opened = true;
                    OverrideIncomingCallSubmition();
                }
                else {
                    alert(data['message']);
                }
            },
            complete: function () {
            }
        }
    ).fail(function () {
        alert('Необработанное исключение!');
    });
}


function SendIncomingCall() {
    var pk = $('#delivery-order-form').attr('object-pk');
    var modal_window = $('#modal-delivery-order');
    var form_data = {
        'name': $('#id_name').val(),
        'phone_number': $('#id_phone_number').val(),
        'email': $('#id_email').val(),
        'note': $('#id_note').val(),
    };
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#urls').attr('incoming-call-url'),
            data: form_data,
            dataType: 'json',
            success: function (data) {
                modal_window.html(data['html']);
                $('#current-order-data').attr('customer-pk', $('#incoming-call-form').attr('customer-pk'));
                OverrideIncomingCallSubmition();
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
}


function CreateCustomer(PhoneNumber, Name) {

}


function UpdateWorkspace() {
    var workspace = $('#delivery-workspace');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#urls').attr('workspace-update'),
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    workspace.html(data['html']);
                }
                else {
                    alert(data['message']);
                }
            },
            complete: function () {
                setTimeout(UpdateWorkspace, 10000);
            }
        }
    ).fail(function () {
        alert('Необработанное исключение!');
    });
}