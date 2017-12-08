$(document).ready(function() {

    $('.delete-device').on( "click", function() {
        var address = $(this).closest('tr').find(".device-address").html()
        var csrftoken = getCookie('csrftoken');
        var postdata = {
                address,
                'csrfmiddlewaretoken': csrftoken
            };
        var postworkflow = $.post( "delete_device", postdata, function(postresponse, status) {
            
        })
            .done(function(postresponse, status) {

            })
            .fail(function(postresponse, status) {
                alert("Could not delete device.")
            })
            .always(function(postresponse, status) {
                location.reload();
            });
    });

    function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
});