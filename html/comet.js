/*
 *  Comet functions for eSEAT
 *  Copyright(c)  2015 Isao Hara, All Rights Reserved.
 */

/*
 *  Register Comet handler
 */
function requestComet(id, force){
  var force_flag  = force || 1;
  $.ajax({
    type: "POST",
    url: "comet_request",
    data: "force="+force_flag+"&id="+id,
    dataType: "json",
    success: function(event){
       if(typeof processEvents == "function"){
         processEvents(event);
       }else{
         processEvents_default(event);
       }
       if (event.terminate){
          alert("Tarminate Long_polling..");
       }else{
          requestComet(id, force_flag);
     }
    },
    error: function(XMLHttpRequest, textStatus, errorThrown){
       $("#response").html("Error in long_polling:"+errorThrown);
    }
  });
}

/*
 *  default callback function
 */
function processEvents_default(event){
  $("#response").html(event.message + " on " + event.date);
}

function showReply(data){
    $("#response").html(data.result+" on "+data.date);
}


/*
 * send data to eSEAT
 */
function sendValueToRtc(val, func){
  var mfunc  = func || showReply;

  $.ajax({
    type: "POST",
    url: "rtc_onData",
    data: val,
    dataType: "json",
    success: mfunc
  });
}

/*
 * send event to registered  comet_request
 */
function sendComet(id, data, func){
  $.ajax({
    type: "POST",
    url: "comet_event",
    data: "id="+id+"&data="+data,
    dataType: "json",
    success: func
  });
}

