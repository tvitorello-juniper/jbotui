$(document).ready(function() {
    // Setup page
    $('nav ul li a[href*="execute"]').toggleClass("grey lighten-2");
    $(document).ready(function() {
        $('select').material_select();
    });
    $(document).ready(function(){
        $('ul.tabs').tabs();
    });

    //Execute command
    $('#execute-button').on( "click", function() {
        //Check if a workflow is selected
        if($('#workflow :selected').prop('disabled') == true){
            alert("Please select a workflow!")
            return
        }
        //Find selected workflow
        workflow = $('#workflow :selected').attr('value')

        login = $("#login").val()
        passwd = $("#passwd").val()

        if (login == "" || passwd == "") {
            alert("Please enter the login credentials!")
            return
        }

        //Find selected tab
        tab = $('#tabs .active').attr('href')
        
        //For devices tab
        if (tab == '#devices') {
            //Find all checked devices
            devices = []
            $('.device-checkbox:checked').each( function () {
                devices.push($(this).attr('id'))
            });

            //Check if at least a device is selected
            if (devices.length == 0){
                alert("Please check at least one device.")
                return
            }
            //Build POST request
            var csrftoken = getCookie('csrftoken');
            var postdata = {
                    'execute_on': 'devices',
                    login,
                    passwd,
                    workflow,
                    devices,
                    'csrfmiddlewaretoken': csrftoken
                };
        }
        //For groups tab
        else if (tab == '#groups') {
            //Find all checked groups
            groups = []
            $('.group-checkbox:checked').each( function () {
                groups.push($(this).attr('id'))
            });

            //Check if at least a device is selected
            if (groups.length == 0){
                alert("Please check at least one group.")
                return
            }
            //Build POST request
            var csrftoken = getCookie('csrftoken');
            var postdata = {
                    'execute_on': 'groups',
                    login,
                    passwd,
                    workflow,
                    groups,
                    'csrfmiddlewaretoken': csrftoken
                };
        }
        //Send POST request
        var postworkflow = $.post( "execute_request", postdata, function(postresponse, status) {
            
        })
            .done(function(postresponse, status) {
                window.location.replace("task_started")
            })
            .fail(function(postresponse, status) {
                alert("Could not execute workflow.")
            })
            .always(function(postresponse, status) {
                
            });
        
        
    });
});