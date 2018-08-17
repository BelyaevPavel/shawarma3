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

$(window).resize(function () {
    CalculateGrid();
    console.log("Handler for .resize() called.");
});

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