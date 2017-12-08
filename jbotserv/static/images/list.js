$(document).ready(function() {
    
   
    $('.delete-image').on( "click", function() {
        var name = $(this).closest('tr').find(".image-name").html()
        var csrftoken = getCookie('csrftoken');
        var postdata = {
                name,
                'csrfmiddlewaretoken': csrftoken
            };
        var postworkflow = $.post( "delete_image", postdata, function(postresponse, status) {
            
        })
            .done(function(postresponse, status) {

            })
            .fail(function(postresponse, status) {
                alert("Could not delete image.")
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