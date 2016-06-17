/*
 *  Comet functions for eSEAT
 *  Copyright(c)  2015 Isao Hara, All Rights Reserved.
 */
(function( global, factory) {
  if ( typeof module === "object" && typeof module.exports === "object" ){
    module.exports = global.document ?
	factory( global, true) :
	function (w) {
	  if ( !w.document ){
		throw new Error("rtc requires a window with a document");
	  }
	  return factory( w );
	};
  } else {
	factory( global );
  }
}(typeof window !== "undefined" ? window : this, function( window, noGlobal){

var
  version = "0.1",

  Rtc = function( selector, context ){
    //return new RTC.fn.init( selector, context );
  };

Rtc.prototype ={
  rtc: version,
  constructor: Rtc,
  selector: "",
  showReply: false,

  getMySeatKey: function(){
     return "My_eSEAT_Key";
  },

  showKey: function(){
     alert(this.getMySeatKey());
  },


  /*
  *  Register Comet handler
 */
  requestComet: function(id, force){
    var force_flag  = force || 1;
    $.ajax({
      type: "POST",
      url: "comet_request",
      data: "force="+force_flag+"&id="+id,
      dataType: "json",
      headers: {'eSEAT-Key' : this.getMySeatKey()},
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
  },
  /*
   *  default callback function
   */

  processEvents_default: function(event){
    $("#response").html(event.message + " on " + event.date);
  },

  showReply: function(data){
    $("#response").html(data.result+" on "+data.date);
  },


  /*
   * send data to eSEAT
   */

  sendValueToRtc: function(val, func){
    var mfunc  = func || this.showReply;

    $.ajax({
      type: "POST",
      url: "rtc_onData",
      data: val,
      dataType: "json",
      headers: {'eSEAT-Key' : this.getMySeatKey()},
      success: mfunc
    });
  },

  /*
   *
   */

  sendMessageToRtc: function(msg, func){
    var mfunc  = func || this.showReply;

    $.ajax({
      type: "POST",
      url: "rtc_processResult",
      data: msg,
      dataType: "json",
      headers: {'eSEAT-Key' : this.getMySeatKey()},
      success: mfunc
    });
  },


  /*
   *
   */

  sendScriptToRtc: function(scr, func){
    var mfunc  = func || this.showReply;

    $.ajax({
      type: "POST",
      url: "evalCommand",
      data: scr,
      dataType: "json",
      headers: {'eSEAT-Key' : this.getMySeatKey()},
      success: mfunc
    });
  },

  /*
   * send event to registered  comet_request
   */
  sendComet: function(id, data, func){
    $.ajax({
      type: "POST",
      url: "comet_event",
      data: "id="+id+"&data="+data,
      dataType: "json",
      success: func
    });
  },

};

var strundefined = typeof undefined;

if ( typeof noGlobal === strundefined ){
  window.Rtc = Rtc;
}

  return Rtc;
}));
