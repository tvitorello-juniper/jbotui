$(document).ready(function() {

    refresh_results_table()

    var timer = window.setInterval(refresh_results_table, 1000);

    function refresh_results_table(){
        $.get( "get_results.html", function(data) {
            data = JSON.parse(data, null, 2)
            console.log(JSON.stringify(data))
            // Remove all rows in the table
            $("#results-table tbody tr").remove()
            for (entry in data) {
                $("#results-table tbody").append("<tr><td>" + JSON.stringify(data[entry]) + "</td></tr>")
            }
        });
    }
});