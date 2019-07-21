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

var workspace_update_timeout = 10000; // ms
var call_check_timeout = 10000; // ms
var modal_delivery_order_is_opened = false;
var modal_menu_is_opened = false;
var modal_menu_container = $('#modal-menu');
var modal_delivery_order_container = $('#modal-delivery-order');

$(document).ready(function () {
    UpdateWorkspace();
    CheckCalls();
});

$(window).resize(function () {
    var modal_is_opened = false;
    CalculateGrid();
    console.log("Handler for .resize() called.");
});

function Hide(elementId) {
    $("#" + elementId).hide();
}

function HideMenu() {
    Hide("modal-menu");
    modal_menu_is_opened = false;
    if (modal_delivery_order_is_opened)
        modal_delivery_order_container.show();
}

function HideDeliveryOrder() {
    Hide("modal-delivery-order");
    modal_delivery_order_is_opened = false;
}


function OverrideDeliveryOrderSubmition() {
    $('#delivery-order-form').on('submit', function (event) {
        event.preventDefault();
        console.log("delivery-order-form submitted!");  // sanity check
        SendDeliveryOrder();
    });
}

function OverrideIncomingCallSubmition() {
    $('#incoming-call-form').on('submit', function (event) {
        event.preventDefault();
        console.log("incoming-call-form submitted!");  // sanity check
        SendIncomingCall();
    });
}

function OverrideDeliverySubmition() {
    $('#delivery-form').on('submit', function (event) {
        event.preventDefault();
        console.log("delivery-form submitted!");  // sanity check
        SendDelivery();
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
    var sidebars_width = $('#delivery-left-column').outerWidth() + $('#delivery-right-column').outerWidth();
    var showLeftColumnWidth = $('#show-left-column').is(":hidden") ? 0 : $('#show-left-column').outerWidth();
    var showRightColumnWidth = $('#show-right-column').is(":hidden") ? 0 : $('#show-right-column').outerWidth();
    console.log('calc(100% - ' + sidebars_width + 'px - ' + showLeftColumnWidth + 'px - ' + showRightColumnWidth + 'px)');
    workspace.css('width', 'calc(100% - ' + sidebars_width + 'px - ' + showLeftColumnWidth + 'px - ' + showRightColumnWidth + 'px)');
    CalculateGrid();
}

function ShowSidebar(SidebarID, ShowButtonID) {
    $('#' + SidebarID).show();
    $('#' + SidebarID).width(300);
    $('#' + ShowButtonID).hide();
    $('#' + ShowButtonID).css('width', '0px');
    var workspace = $('#delivery-workspace');
    var sidebars_width = $('#delivery-left-column').outerWidth() + $('#delivery-right-column').outerWidth();
    var showLeftColumnWidth = $('#show-left-column').is(":hidden") ? 0 : $('#show-left-column').outerWidth();
    var showRightColumnWidth = $('#show-right-column').is(":hidden") ? 0 : $('#show-right-column').outerWidth();
    console.log('calc(100% - ' + sidebars_width + 'px - ' + showLeftColumnWidth + 'px - ' + showRightColumnWidth + 'px)');
    workspace.css('width', 'calc(100% - ' + sidebars_width + 'px - ' + showLeftColumnWidth + 'px - ' + showRightColumnWidth + 'px)');
    CalculateGrid();
}

function ShowMenu() {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#delivery-urls').attr('menu-url'),
            data: {'delivery_mode': true},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    //modal_delivery_order_container.hide();
                    modal_menu_container.html(data['html']);
                    modal_menu_container.css("display", "block");
                    modal_menu_is_opened = true;
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
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#delivery-urls').attr('create-order-url'),
            dataType: 'json',
            data: pk_data,
            success: function (data) {
                if (data['success']) {
                    modal_delivery_order_container.html(data['html']);
                    modal_delivery_order_container.css("display", "block");
                    modal_delivery_order_is_opened = true;
                    jQuery.datetimepicker.setLocale('ru');
                    // $('#id_obtain_timepoint').datetimepicker({
                    //     format: "d.m.Y H:i",
                    //     mask: true,
                    //     minDate: 0,
                    //     lang: "ru"
                    // });
                    $('#id_obtain_timepoint').prop('disabled',true);
                    $('#id_delivered_timepoint').datetimepicker({
                        format: "d.m.Y H:i",
                        mask: true,
                        minDate: 0,
                        step: 5,
                        lang: "ru"
                    });
                    $('#id_preparation_duration').datetimepicker({
                        datepicker: false,
                        mask: true,
                        format: "H:i",
                        step: 5,
                        lang: "ru"
                    });
                    $('#id_delivery_duration').datetimepicker({
                        datepicker: false,
                        mask: true,
                        format: "H:i",
                        step: 5,
                        lang: "ru"
                    });
                    $('#btn_show_menu').on('click', function (event) {
                        event.preventDefault();
                    });
                    OverrideDeliveryOrderSubmition();
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
            url: $('#delivery-urls').attr('create-order-url'),
            data: form_data,
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    location.reload();
                }
                else {
                    modal_delivery_order_container.html(data['html']);
                    OverrideDeliveryOrderSubmition();
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
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#delivery-urls').attr('incoming-call-url'),
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    modal_delivery_order_container.html(data['html']);
                    modal_delivery_order_container.css("display", "block");
                    modal_delivery_order_is_opened = true;
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


function SendIncomingCall(CustomerPK = null) {
    var pk = $('#delivery-order-form').attr('object-pk');
    var customer_pk = $('#incoming-call-form').attr('customer-pk');
    var form_data = {
        'name': $('#id_name').val(),
        'phone_number': $('#id_phone_number').val(),
        'email': $('#id_email').val(),
        'note': $('#id_note').val(),
        'pk': customer_pk
    };
    if (CustomerPK != null)
        form_data['pk'] = CustomerPK;
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#delivery-urls').attr('incoming-call-url'),
            data: form_data,
            dataType: 'json',
            success: function (data) {
                modal_delivery_order_container.html(data['html']);
                modal_delivery_order_container.css("display", "block");
                modal_delivery_order_is_opened = true;
                $('#current-order-data').attr('customer-pk', $('#incoming-call-form').attr('customer-pk'));
                $('#btn_create_delivery_order').on('click', function (event) {
                    event.preventDefault();
                });
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


function CreateDelivery() {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#delivery-urls').attr('delivery-url'),
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    modal_delivery_order_container.html(data['html']);
                    modal_delivery_order_container.css("display", "block");
                    modal_delivery_order_is_opened = true;
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


function SendDelivery() {
    var pk = $('#delivery-form').attr('object-pk');
    var form_data = {
        'car_driver': $('#id_car_driver').val()
    };
    if (pk)
        form_data['delivery_pk'] = pk;
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#delivery-urls').attr('delivery-url'),
            data: form_data,
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    location.reload();
                }
                else {
                    modal_delivery_order_container.html(data['html']);
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


function UpdateWorkspace() {
    var workspace = $('#delivery-workspace');
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#delivery-urls').attr('workspace-update'),
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
                setTimeout(UpdateWorkspace, workspace_update_timeout);
            }
        }
    ).fail(function () {
        alert('Необработанное исключение!');
    });
}


function CheckCalls() {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'GET',
            url: $('#delivery-urls').attr('check-calls-url'),
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    if (!(modal_delivery_order_is_opened || modal_menu_is_opened))
                        SendIncomingCall(data['caller_pk']);
                    else
                        console.log('There is a call but some modal window seams to be opened.');
                }
                else {
                    console.log('Waiting for calls...');
                }
            },
            complete: function () {
                setTimeout(CheckCalls, call_check_timeout);
            }
        }
    ).fail(function () {
        alert('Необработанное исключение!');
    });
}


function SelectCook(CookPK, DeliveryOrderPK) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#delivery-urls').attr('select-cook-url'),
            data: {"cook_pk": CookPK, "delivery_order_pk": DeliveryOrderPK},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    alert(data['message']);
                }
                else {
                    alert(data['message']);
                }
            }
        }
    ).fail(function () {
        console.log('Failed ' + aux);
    });
}


function StartShawarmaCooking(OrderPK) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#delivery-urls').attr('start-shawarma-cooking-url'),
            data: {"order_pk": OrderPK},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    alert(data['message']);
                }
                else {
                    alert(data['message']);
                }
            }
        }
    ).fail(function () {
        console.log('Failed ' + aux);
    });
}


function SetAddressFieldValue(AddressString) {
    $('#id_address').val(AddressString);
}


function StartShashlykCooking(OrderPK) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#delivery-urls').attr('start-shashlyk-cooking-url'),
            data: {"order_pk": OrderPK},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    alert(data['message']);
                }
                else {
                    alert(data['message']);
                }
            }
        }
    ).fail(function () {
        console.log('Failed ' + aux);
    });
}


function FinishShashlykCooking(OrderPK) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#delivery-urls').attr('finish-shashlyk-cooking-url'),
            data: {"order_pk": DeliveryOrderPK},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    alert(data['message']);
                }
                else {
                    alert(data['message']);
                }
            }
        }
    ).fail(function () {
        console.log('Failed ' + aux);
    });
}


function FinishDeliveryOrder(DeliveryOrderPK) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#delivery-urls').attr('finish-delivery-order-url'),
            data: {"delivery_order_pk": DeliveryOrderPK},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    alert(data['message']);
                }
                else {
                    alert(data['message']);
                }
            }
        }
    ).fail(function () {
        console.log('Failed ' + aux);
    });
}

function CancelDeliveryOrder(DeliveryOrderPK) {
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    });
    $.ajax({
            type: 'POST',
            url: $('#delivery-urls').attr('cancel-delivery-order-url'),
            data: {"delivery_order_pk": DeliveryOrderPK},
            dataType: 'json',
            success: function (data) {
                if (data['success']) {
                    alert(data['message']);
                }
                else {
                    alert(data['message']);
                }
            }
        }
    ).fail(function () {
        console.log('Failed ' + aux);
    });
}