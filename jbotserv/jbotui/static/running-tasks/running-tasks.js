$(document).ready(function() {

    refresh_running_tasks_table()

    var timer = window.setInterval(refresh_running_tasks_table, 1000);

    function refresh_running_tasks_table(){
        $.get( "get_running_tasks.html", function(data) {
            data = JSON.parse(data, null, 2)
            console.log(JSON.stringify(data))
            // Remove all rows in the table
            $("#running-tasks-table tbody tr").remove()
            for (entry in data) {
                $("#running-tasks-table tbody").append("<tr><td>" + JSON.stringify(data[entry]) + "</td></tr>")
            }
        });
    }
});