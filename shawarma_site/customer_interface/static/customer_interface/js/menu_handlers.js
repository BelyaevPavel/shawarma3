/**
 * Created by paul on 12.04.20.
 */
$(document).ready(function () {
    $('.block-title').click(function (event) {
        $(this).toggleClass('active').next().slideToggle(300);
    });
});