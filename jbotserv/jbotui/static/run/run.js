$(document).ready(function() {

    $('#runform').submit(function(event){
        formData = $('#runform').serializeArray()
        submitData = {}
        for (var _elem in formData) {
            submitData[formData[_elem]["name"]] = formData[_elem]["value"]
        }
        //console.log(JSON.stringify(submitData))
        var runworkflow = $.post("executeworkflow", submitData, function(response, status) {
        })
            .done(function(postresponse, status) {
                alert(postresponse)
            })
            .fail(function(postresponse, status) {
                alert( "Could not reach server." );
            })
            .always(function(postresponse, status) {
                
            })

        event.preventDefault();
    });

});