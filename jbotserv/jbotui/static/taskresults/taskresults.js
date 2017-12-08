$(document).ready(function() {
    $('nav ul li a[href*="results"]').toggleClass("grey lighten-2");

    $('tr.clickable').on("click", function() {
        window.location = $(this).data("href");
    })

});