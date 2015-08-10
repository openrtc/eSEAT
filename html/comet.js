/*
 *
 */

function long_polling(){
  $.ajax({
    type: "POST",
    url: "comet_request",
    data: "id="+$("input[name='id']").val(),
    dataType: "json",
    success: function(event){
       processEvents(event);
       if (event.terminate){
          alert("Tarminate Long_polling..");
       }else{
          long_polling();
     }
    },
    error: function(XMLHttpRequest, textStatus, errorThrown){
       $("#response").html("Error in long_polling:"+errorThrown);
    }
  });
}

function long_polling_id(id){
  $.ajax({
    type: "POST",
    url: "comet_request",
    data: "force=True&id="+id,
    dataType: "json",
    success: function(event){
       processEvents(event);
       if (event.terminate){
          alert("Tarminate Long_polling..");
       }else{
          long_polling_id(id);
     }
    },
    error: function(XMLHttpRequest, textStatus, errorThrown){
       $("#response").html("Error in long_polling:"+errorThrown);
    }
  });
}


function processEvents(event){
  $("#response").html(event.message + " on  " + event.date);
}

function sendEvent(){
  $.ajax({
    type: "POST",
    url: "comet_event",
    data: "id="+$("input[name='eid']").val()+"&location=Somewhere",
    dataType: "json",
    success: function(data){
      $("#response2").html(data.result+" on "+data.date);
    }
  });
}


function sendEventToRtc(){
  $.ajax({
    type: "POST",
    url: "rtc_onData",
    data: $("input[name='msg']").val(),
    dataType: "json",
    success: function(data){
      $("#response2").html(data.result+" on "+data.date);
    }
  });
}

function sendValueToRtc(val){
  $.ajax({
    type: "POST",
    url: "rtc_onData",
    data: val,
    dataType: "json",
    success: function(data){
      $("#response2").html(data.result+" on "+data.date);
    }
  });
}


