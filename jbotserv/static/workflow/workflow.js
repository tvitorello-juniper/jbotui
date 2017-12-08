
$(document).ready(function() {

    //-----------------------------------------------------------------
    //-----------------------------------------------------------------
    //Miscellaneous
    //-----------------------------------------------------------------

    //Variables definitions for shorthanding through the code
    var $flowchart = $('#flowchart');
    var $container = $flowchart.parent();
    var $delbutton = $('#deleteselected');
    var $opprop = $('.operatorproperties');
    var $ephemeral = $('.ephemeral');
    var $morph = $('.morph');

    //Data Structures
    var operatorSettings = {}
    var data = {};


    //-----------------------------------------------------------------
    //-----------------------------------------------------------------
    //Workspace
    //-----------------------------------------------------------------


    //-----------------------------------------------------------------
    //Panzoom Handler
    var cx = $flowchart.width() / 2;
    var cy = $flowchart.height() / 2;
    $flowchart.panzoom();
    // Centering panzoom
    $flowchart.panzoom('pan', -cx + $container.width() / 2, -cy + $container.height() / 2);
    // Panzoom zoom handling...
    var possibleZooms = [0.5, 0.75, 1, 2, 3];
    var currentZoom = 2;
    $container.on('mousewheel.focal', function( e ) {
        e.preventDefault();
        var delta = (e.delta || e.originalEvent.wheelDelta) || e.originalEvent.detail;
        var zoomOut = delta ? delta < 0 : e.originalEvent.deltaY > 0;
        currentZoom = Math.max(0, Math.min(possibleZooms.length - 1, (currentZoom + (zoomOut * 2 - 1))));
        $flowchart.flowchart('setPositionRatio', possibleZooms[currentZoom]);
        $flowchart.panzoom('zoom', possibleZooms[currentZoom], {
            animate: false,
            focal: e
        });
    });


    //-----------------------------------------------------------------
    //Workflow Handler
    $('#flowchart').flowchart({
        data: data,
        //-----------------------------------------------------------------
        //Show and edit right menu on OPERATOR select
        onOperatorSelect: function(operatorId) {
            $delbutton.show();
            $opprop.find("form").trigger("reset")
            $ephemeral.hide();
            var operatorTitle = ($flowchart.flowchart('getOperatorTitle',operatorId)).trim();
            var compressedTitle = operatorTitle.replace(/\s+/g, '')
            var propbox = $('#properties'+compressedTitle)
            propbox.show()
            propbox.find('#opset').html($('#Menu'+compressedTitle).html());
            for (var key in operatorSettings[operatorId]){
                propbox.find('#'+key).val(operatorSettings[operatorId][key])
            }
            $morph.trigger("load");
            return true;
        },
        //Hide and reset the right Menu on OPERATOR unselect
        onOperatorUnselect: function() {
            $delbutton.hide();
            $opprop.find("form").trigger("reset")
            $ephemeral.hide();
            return true;
        },
        //Show right menu on LINK select
        onLinkSelect: function(linkId) {
            $ephemeral.hide();
            $delbutton.show();
            return true;
        },
        //Hide right menu on LINK unselect
        onLinkUnselect: function(linkId) {
            $ephemeral.hide();
            $delbutton.hide();
            return true;
        }
    });


    //-----------------------------------------------------------------
    //-----------------------------------------------------------------
    //Left Menu
    //-----------------------------------------------------------------

    //Opeartor Drag and Drop implementation
    var $draggableOperators = $('.draggableoperator');
    function getOperatorData($element) {
        var temp_title = $element.text().trim()
        //Base properties and settings required for all operators
        var data = {
            properties: {
                title: temp_title,
                inputs: {},
                outputs: {},
            }
        };
        //Construct the operator properties and settings for each type of operator
        if ( temp_title != 'Start') {
            data.properties.inputs = {input_1:{label:"Prev"}};
        }
        if ( temp_title == 'Start') {
            data.properties.outputs = {output_1:{label:"Next"}};
        } else if ( temp_title != 'End' && temp_title != 'Fail' ) {
            data.properties.outputs = {output_1:{label:"Next"}, outlput_2:{label:"onFail"}};
        }
        return data;
    }

    var operatorId = 0;
    //Operator creation on drag
    $draggableOperators.draggable({
        cursor: "move",
        opacity: 0.7,
        
        helper: 'clone', 
        appendTo: 'body',
        zIndex: 1000,
        
        helper: function(e) {
          var $this = $(this);
          var data = getOperatorData($this);
          return $flowchart.flowchart('getOperatorElement', data);
        },
        stop: function(e, ui) {
            var $this = $(this);
            var elOffset = ui.offset;
            var containerOffset = $container.offset();
            if (elOffset.left > containerOffset.left &&
                elOffset.top > containerOffset.top && 
                elOffset.left < containerOffset.left + $container.width() &&
                elOffset.top < containerOffset.top + $container.height()) {

                var flowchartOffset = $flowchart.offset();

                var relativeLeft = elOffset.left - flowchartOffset.left;
                var relativeTop = elOffset.top - flowchartOffset.top;

                var positionRatio = $flowchart.flowchart('getPositionRatio');
                relativeLeft /= positionRatio;
                relativeTop /= positionRatio;
                
                var data = getOperatorData($this);
                data.left = relativeLeft;
                data.top = relativeTop;
                
                $flowchart.flowchart('addOperator', data);
            }
        }
    });

    //-----------------------------------------------------------------
    //Accordion Menu
    $( "#accordion" ).accordion({
        icons: false
    });

    //-----------------------------------------------------------------
    //-----------------------------------------------------------------
    //Right Menu
    //-----------------------------------------------------------------

    //-----------------------------------------------------------------
    //Delete button functionality
    $('#deleteselected').click(function() {
        var del_id = $flowchart.flowchart('getSelectedOperatorId');
        if (del_id in operatorSettings) {
            delete operatorSettings[del_id]
        }
        $flowchart.flowchart('deleteSelected')
    });

    //-----------------------------------------------------------------
    //Save settings to selected block
    $('.settings_field, .settings_opt').on('change input', function() {
        var save_id = $flowchart.flowchart('getSelectedOperatorId');
        var temp_settings = {}
        $(this).closest('.block_settings').find('.settings_field').each( function(index) {
            temp_settings[$(this).attr('id')] = $(this).val()
        })
        $(this).closest('.block_settings').find('.settings_opt').each( function(index) {
            temp_settings[$(this).attr('id')] = $(this).find(":selected").val()
        })
        operatorSettings[save_id] = {}
        operatorSettings[save_id] = temp_settings
    });

    //-----------------------------------------------------------------
    //Compare Snapshots Block
    //Morph menu based on compare selection
    $('#comparetype').on( "change load", function() {
        var option = $(this).find("option:selected").val();
        switch (option) {
            case "pre":
                $('.comparesettings').hide()
                $('#presettings').show()
            break;
            case "easy":
                $('.comparesettings').hide()
                $('#easysettings').show()
            break;
            case "custom":
                $('.comparesettings').hide()
                $('#customsettings').show()
            break;
            default:
                $('.comparesettings').hide()
        }
    });
    //-----------------------------------------------------------------
    //Take Snapshots Block
    //Morph menu based on  selection
    $('#take_compare_type').on( "change load", function() {
        var option = $(this).find("option:selected").val();
        switch (option) {
            case "pre":
                $('.take_settings').hide()
                $('#take_pre_settings').show()
            break;
            case "custom":
                $('.take_settings').hide()
                $('#take_custom_settings').show()
            break;
            default:
                $('.take_settings').hide()
        }
    });



    //-----------------------------------------------------------------
    //-----------------------------------------------------------------
    //Top Menu
    //-----------------------------------------------------------------

    //Reload the page, clearing all settings and variables
    $('#newworkflow').click(function() {
        location.reload();
    });


    //Save current workflow
    $('#saveworkflow').click(function() {
        var csrftoken = getCookie('csrftoken');
        var workflowdata = JSON.stringify($flowchart.flowchart('getData'), null, 2)
        var setdata = JSON.stringify(operatorSettings, null, 2)
        var workflowname = prompt("Please enter file name:")
        if (!workflowname){
            return;
        }
        var postdata = {
                workflowname,
                workflowdata,
                setdata,
                'csrfmiddlewaretoken': csrftoken
            };
        var postworkflow = $.post( "saveworkflow", postdata, function(postresponse, status) {
            
        })
            .done(function(postresponse, status) {
                alert(postresponse)
            })
            .fail(function(postresponse, status) {
                alert( "error" );
            })
            .always(function(postresponse, status) {
                
            });
    });
    
});

