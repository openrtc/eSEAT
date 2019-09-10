/*
 * RT System Editor on the Web

*/

//// for FileSupport  ///////////////////
var fileApiSupported = 0;

function checkFileApi(){
  if (window.File && window.FileReader && window.FileList && window.Blob) {
    fileApiSupported = 1;
  } else {
    alert('The File APIs are not fully supported in this browser.');
  }
}

/*
 *
 */
/// create File  Viewss
//
var selectedItem = null;

function selectItem(ele){
  if(selectedItem){
     selectedItem.style.background='#ffffff';
     selectedItem.style.color='#000000';
  }
  selectedItem = ele;
  selectedItem.style.background='#0000aa';
  selectedItem.style.color='#ffffff';
}

function fileItemFunc(ele){
  var nodes = ele.childNodes;
  var n = nodes.length;

  for(var i=0; i<n ;i++){
    var node = nodes[i];
    if(typeof node != 'undefined'){
      if(node.nodeName == 'UL'){
        toggleDisplay(node);
        return false;
      }
    }
  }
  return false;
}
function mkFileItem(p, obj){
  var res,itm;

  if(isString(obj)){
    res = document.createElement("li");
    res.className="rtsprofile";
    res.onclick = function(e){ e.stopPropagation(); };
    itm = res.appendChild(document.createElement("A"));
    itm.className="rts_item";
    itm.href="#";
    itm.innerHTML=obj;
    itm.setAttribute('path', p);
    itm.onclick = function(e){
                   selectItem(this);
                   e.stopPropagation();
                };
    res.setAttribute('id', p+'/'+obj);

  }else{
    res = document.createElement("li");
    res.className="folder";
    var itm_val = document.createElement("span");
    itm_val.innerHTML = obj.folder;
    if( obj.components.length > 0 ){
      itm_val.className = "haschild";
    }
    res.appendChild( itm_val);
    res.onclick = function(e){
                     fileItemFunc(this);
                     e.stopPropagation();
                  };

    itm = res.appendChild( document.createElement("ul") );
    itm.style.display = 'none';

    p = p + "/"+ obj.folder;

    for(var i=0;i< obj.components.length; i++){
      itm.appendChild(mkFileItem(p, obj.components[i] ));
    }
  }
  return res;
}

function mkFileView(txt){
  var content = JSON.parse(txt);
  var res, itm, itm_val;
  var p;

  res = document.createElement("ul");
  res.className = "folder";
  res.setAttribute("root", content.folder);
  p="/"+content.folder;
 
  itm = res.appendChild( document.createElement("li"));
  itm.className = "folder";

  itm_val = document.createElement("span");
  itm_val.innerHTML = content.folder;

  if( content.components.length > 0 ){
    itm_val.className = "haschild";
  }
  itm.appendChild( itm_val);
 
  itm.onclick = function(e){
                   fileItemFunc(this);
                   e.stopPropagation();
                };

  itm = itm.appendChild( document.createElement("ul") );
  itm.style.display = 'none';

  for(var i=0; i< content.components.length; i++ ){
    itm.appendChild(mkFileItem(p, content.components[i] ));
  }

  return res;
}

function showProfileList(txt){
  var tree=mkFileView(txt);
  var view = document.getElementById('listview');
  view.appendChild(tree);

}

function ListRemoteRtcProfile(){
  var data=new Array();
  data['cmd'] = "rtcProfileList";
  postRequest(rtsh_com, data, showProfileList, null);
}

function getRemoteRtcProfile(fname){
  var data=new Array();
  data['cmd'] = "getRtcProfile";
  data['name'] = fname;
  postRequest(rtsh_com, data, loadedRtcProfile, null);
}

function OpenRemoteRtcProfile(){
  if(selectedItem){
    var path = selectedItem.getAttribute('path');
    var file = selectedItem.innerHTML;
    var fname = path+"/"+file

    getRemoteRtcProfile(fname);
    console.log(fname); 
  }

}

///// restore RT System...
function restoreComponent(path,  x, y){
  console.log("Restore component:  "+ path+": ("+x+","+y+")");
  window.opener.requestRestoreComponent(path, Number(x), Number(y));
}

function restoreConnector(source, sport,  target, tport, opts, count){
  if(!count){ count = 0; }
  if (source.charAt(0) != "/"){ source = "/"+source; }
  if (target.charAt(0) != "/"){ target = "/"+target; }
  var sp = sport.split('.');
  var tp = tport.split('.');

  //console.log("Count:"+count);
  var sobj = window.opener.findRtc(source);
  var tobj = window.opener.findRtc(target);

  if((!sobj || !tobj) && count < 10 ){
    (function(){
       var sc = source;
       var sp = sport;
       var tc = target;
       var tp = tport;
       var ops = opts;
       var c = count+1;
       setTimeout(function(){ restoreConnector( sc, sp,  tc, tp, ops, c); }, 500);
    })();
  }else{
    console.log("Restore connector:  "+ source+":"+sp[1]+"<-->"+ target+":"+tp[1]);
    window.opener.createConnector(source+":"+sp[1], target+":"+tp[1], 0);
  }
}

////// parse RTS Profile
function getExtProperty(node, name){
  for(var i in node.childNodes){
    var cn = node.childNodes[i];
    if(cn.tagName ==  "rtsExt:Properties"){
      var extname = cn.getAttribute("rtsExt:name");
      if(extname == name){
        return cn.getAttribute("rtsExt:value");
      }
    }
  }
  return null;
}

function getAttribute(node, name){
  if(node.hasAttribute(name)){
    return node.getAttribute(name);
  }
  return null;
}

function parseComponent(node){
  var comp = new RtsComponentProfile(null);

  /// Attributes
  for(var i=0; i<node.attributes.length; i++){
    var name = node.attributes[i].name;
    var value = node.attributes[i].value;

    if(name == "rts:id"){
      comp.id = value;
    }else if(name == "rts:instanceName"){
      comp.instanceName = value;
    }else if(name == "rts:pathUri"){
      comp.path = value;
    }else if(name == "rts:isRequired"){
      comp.required = value;
    }else if(name == "rts:compositeType"){
      comp.compType = value;
    }else if(name == "rts:activeConfigurationSet"){
      comp.configSet = value;
    }
  }

  if(!comp.instanceName  || !comp.id  || !comp.path  || !comp.compType ){
     alert("Invalid RTS Profile");
     return null;
  }

  ////
  comp.obj = new RtObject(comp.instanceName, "/"+comp.path);

  /// ChildNode
  var x=0, y=0;
  for(var i in node.childNodes){
    var cn = node.childNodes[i];
    if(cn.tagName){
      if(cn.tagName == "rts:DataPorts"){
      }else if (cn.tagName == "rts:ServicePorts" ){
      }else if (cn.tagName == "rts:ConfigurationSets" ){
      }else if (cn.tagName == "rts:ExecutionContexts" ){
      }else if (cn.tagName == "rtsExt:Location" ){
        if(cn.hasAttribute("rtsExt:x")){
          x = cn.getAttribute("rtsExt:x");
        }
        if(cn.hasAttribute("rtsExt:y")){
          y = cn.getAttribute("rtsExt:y");
        }
      }else if (cn.tagName == "rtsExt:Properties" ){
      }else{
        console.log("Unknown tagName : "+cn.tagName);
      }
    }
  } 

  //// 
  comp.x = x;
  comp.y = y;
  comp.restoreCmd = restoreComponent;

  ///// restore component
  restoreComponent(comp.path,  x, y);

  return comp;
}

function parseDataPortConnector(node){
  /// Attributes
  for(var i=0; i<node.attributes.length; i++){
    var name = node.attributes[i].name;
    var value = node.attributes[i].value;

    if(name == "rts:name"){
    }else if(name == "rts:connectorId"){
    }else if(name == "rts:dataType"){
    }else if(name == "rts:dataflowType"){
    }else if(name == "rts:interfaceType"){
    }else if(name == "rts:subscriptionType"){
    }
  }

  /// ChildNode
  var source, target;
  var opts=[];

  for(var i in node.childNodes){
    var cn = node.childNodes[i];
    if(cn.tagName){
      if(cn.tagName == "rts:sourceDataPort"){
        source_id = cn.getAttribute("rts:componentId");
        source_port = cn.getAttribute("rts:portName");
        source = getExtProperty(cn, "COMPONENT_PATH_ID");

      }else if (cn.tagName == "rts:targetDataPort" ){
        target_id = cn.getAttribute("rts:componentId");
        target_port = cn.getAttribute("rts:portName");
        target = getExtProperty(cn, "COMPONENT_PATH_ID");

      }else if (cn.tagName == "rtsExt:Properties" ){
      }else{
        console.log("Unknown tagName : "+cn.tagName);
      }
    }
  } 

  ///// restore connector
  restoreConnector(source, source_port,  target, target_port,  null);
}

function parseServicePortConnector(node){
  /// Attributes
  for(var i=0; i<node.attributes.length; i++){
    var name = node.attributes[i].name;
    var value = node.attributes[i].value;

    if(name == "rts:name"){
    }else if(name == "rts:connectorId"){
    }
  }
  /// ChildNode
  var source, target;
  var opts=[];

  for(var i in node.childNodes){
    var cn = node.childNodes[i];
    if(cn.tagName){
      if(cn.tagName == "rts:sourceServicePort"){
        source_id = cn.getAttribute("rts:componentId");
        source_port = cn.getAttribute("rts:portName");
        source = getExtProperty(cn, "COMPONENT_PATH_ID");
      }else if (cn.tagName == "rts:targetServicePort" ){
        target_id = cn.getAttribute("rts:componentId");
        target_port = cn.getAttribute("rts:portName");
        target = getExtProperty(cn, "COMPONENT_PATH_ID");
      }else if (cn.tagName == "rtsExt:Properties" ){
      }else{
        console.log("Unknown tagName : "+cn.tagName);
      }
    }
  } 

  ///// restore connector
  restoreConnector(source, source_port,  target, target_port,  null);
}

///// load RTS Profile from local storage
//
function loadedRtcProfile(txt)
{
  var span = document.createElement('span');
  span.innerHTML = "<hr><input type=\"button\" onClick=\"restoreRtcProfile();\" value=\"Restore...\"/>";
  span.innerHTML += "<br><textarea cols=\"100\" rows=\"20\" id=\"rtsprofile\">"+ txt +"</textarea>";

  document.getElementById('list').insertBefore(span, null);

//  restoreRtcProfile();
}

//////
function restoreRtcProfile()
{
  var txt = document.getElementById('rtsprofile').value;

  var parser = new DOMParser();
  var xmldoc = parser.parseFromString(txt, "text/xml");
  var val = "";

  var nodes = xmldoc.getElementsByTagName("rts:RtsProfile");
  var rtsprofile = new RtsProfile('', '', '');

  var topNode = nodes[0];
  rtsprofile.version = topNode.getAttribute('rts:version');
  if(rtsprofile.version != "0.2") {
    alert("Invalid RtsProfile");
    return;
  }

  rtsprofile.id = topNode.getAttribute('rts:id');
  rtsprofile.creattionDate = topNode.getAttribute('rts:version');
  rtsprofile.creationDate = new Date(topNode.getAttribute('rts:creationDate'));
  rtsprofile.updateDate = new Date(topNode.getAttribute('rts:updateDate'));

  for(var i in topNode.childNodes){
    var node = topNode.childNodes[i];
    var tag = node.tagName;

    if(tag){
      if(tag == "rts:Components"){
        parseComponent(node);

      }else if(tag == "rts:DataPortConnectors"){
        parseDataPortConnector(node);

      }else if(tag == "rts:ServicePortConnectors"){
        parseServicePortConnector(node);

      }else{
        console.log("Unknown tag: "+ tag);
      }
    }
  }
}

//////
//
function handleFileSelect(evt) {
  var files = evt.target.files; // FileList object

  for (var i = 0, f; f = files[i]; i++) {
    if (!f.type.match('text/*')) {
      continue;
    }
    var reader = new FileReader();
    reader.onload = (function(theFile) {
      return function(e) {  loadedRtcProfile(e.target.result); };
    })(f);
    reader.readAsText(f,'utf8');
  }
}

//////////

function changeDownloadFilename(){
  var nele = document.getElementById('rtsname');
  var aele = document.getElementById('anchor');
  aele.download=nele.value;
}

function handleDownload(id){
  var ele = document.getElementById(id);
  var nele = document.getElementById('rtsname');
  var text = ele.value;
  var obj = document.getElementById("anchor");
  obj.download=nele.value;
  obj.href = 'data:application/octet-stream,'+encodeURIComponent(text);
  obj.innerHTML = "Please click and download...";
}

////
function openRtsProfileWindow(){
  rtsp_window = window.open("rtsprofile.html", "RtsProfile", "width=600,height=600,scrollbars=1,menubar=1");
  rtsp_window.focus();
}

function rtsPath(path){
  if (path.charAt(0) == '/'){
    return path.substr(1);

  }
  return path;
}

////////// RtsProfile
//
//RtcComponentProfile
var RtsComponentProfile=function(comp)
{
  this.obj = comp;
  this.configSet=null;

  if(comp){
    this.compType="None";
    this.instanceName=comp.obj["InstanceName"];
    this.id=comp.getId();
    this.path=comp.getFullName();
    this.required="true";
  }else{
    this.compType="";
    this.instanceName="";
    this.id="";
    this.path="";
    this.required="false";
  }
  this.x = 0;
  this.y = 0;
  this.restoreCmd = null;
}

RtsComponentProfile.prototype.port_toXML=function(port)
{
   var res ="";
   var type = port.Type;

   if(type == 'DataInPort' || type == 'DataOutPort'){
      res += "  <rts:DataPorts xsi:type=\"rtsExt:dataport_ext\" ";
      res += " rts:name=\""+port["Name"]+"\">\n";

      var keys = ["port.port_type", "dataport.data_type", "dataport.subscription_type", "dataport.dataflow_type", "dataport.interface_type"];
      for(var i=0;i<keys.length;i++){
        var propname = keys[i];
        res += "    <rtsExt:Properties rtsExt:name=\""+propname+"\" rtsExt:value=\""+port["Properties"][propname]+"\"/>\n";
      }

      res += "  </rts:DataPorts>\n";

   }else if(type == 'CorbaPort'){
      res += "  <rts:ServicePorts xsi:type=\"rtsExt:serviceport_ext\" ";
      res += " rts:name=\""+port.name+"\">\n";

      var keys = ["port.port_type"];
      for(var i=0;i<keys.length;i++){
        var propname = keys[i];
        res += "    <rtsExt:Properties rtsExt:name=\""+propname+"\" rtsExt:value=\""+port["Properties"][propname]+"\"/>\n";
      }

      res += "  </rts:ServicePorts>\n";
   }
   return res;
}

RtsComponentProfile.prototype.match_port=function(obj){
  for(i in this.obj.ports){
    var p = this.obj.ports[i];
    if(p == obj){
      return true;
    } 
  }
  return false;
}

RtsComponentProfile.prototype.get_port=function(obj){
  var res = null;

  return res;
}

RtsComponentProfile.prototype.to_target_portXML=function(tagname, port)
{
  var res ="";
  res += "  <rts:"+tagname+" xsi:type=\"rtsExt:target_port_ext\"";
  res += " rts:instanceName=\""+this.instanceName+"\" ";
  res += " rts:componentId=\""+this.obj.getId()+"\" ";
  res += " rts:portName=\""+this.instanceName+"."+port.Name+"\" ";
  res += ">\n"
  res += "    <rtsExt:Properties rtsExt:name=\"COMPONENT_PATH_ID\"";
  res += " rtsExt:value=\""+rtsPath(this.path)+"\" />\n";
  
  res += "  </rts:"+tagname+">\n";
  return res;
}

RtsComponentProfile.prototype.toXML=function()
{
  var configSet="";
  var comp = this.obj;
  if(comp.obj.ActiveConfig){
    this.configSet = comp.obj.ActiveConfig;
    configSet=" rts:activeConfigurationSet=\""+comp.obj.ActiveConfig+"\"" ;
  }
  var result = "\n<rts:Components xsi:type=\"rtsExt:component_ext\" rts:isRequired=\"true\" ";
  result += "rts:compositeType=\""+this.compType;
  result += "\" rts:instanceName=\""+this.instanceName;
  result += "\" rts:pathUri=\""+rtsPath(this.path);
  result += "\" rts:id=\""+this.id+"\""
  result += configSet+">\n";

  //// Ports
  for(var i=0; i<comp.obj.Ports.length; i++){
    var port = comp.obj.Ports[i];
    result += this.port_toXML(port); 
  }

  //// ConfigurationSets
  var ext_props = comp.obj["ExtraProperties"];
  if(comp.obj.ConfigSet){
    for(var j=0; j<comp.obj.ConfigSet.length; j++){
      var confname = comp.obj.ConfigSet[j];
      var params = getConfigParams(ext_props, confname);
      result += "  <rts:ConfigurationSets rts:id=\""+confname+"\">\n";
      for(var i=0; i<comp.obj.ConfigParams.length; i++){
        var param = comp.obj.ConfigParams[i];
        var paramname = "conf."+confname+"."+param;
        result += "    <rts:ConfigurationData rts:name=\""+param+"\" rts:data=\""+params[paramname]+"\"/>\n";
      }
      result += "  </rts:ConfigurationSets>\n";
    }

    var other_configsets = ['__widget__', '__constraints__'];

    for(var j=0; j<other_configsets.length; j++){
      var confname = other_configsets[j];
      var params = getConfigParams(ext_props, confname);
      result += "  <rts:ConfigurationSets rts:id=\""+confname+"\">\n";
      for(var i=0; i<comp.obj.ConfigParams.length; i++){
        var param = comp.obj.ConfigParams[i];
        var paramname = "conf."+confname+"."+param;
        result += "    <rts:ConfigurationData rts:name=\""+param+"\" rts:data=\""+params[paramname]+"\"/>\n";
      }
      result += "  </rts:ConfigurationSets>\n";
    }
  }

  //// ExecutionContext
  var ecs = comp.obj.ExecutionContext;
  for(var i in ecs){
    var ec = ecs[i];
    result += "  <rts:ExecutionContexts rts:id=\""+ec.Handle+"\" xsi:type=\"rtsExt:execution_context_ext\" ";
    result += " rts:kind=\""+ec.Kind+"\" ";
    result += " rts:rate=\""+ec.Rate+"\" ";
    result += "/>\n";

  }
  
  //// Participants
  
  //// Location
  var x=0, y=0;
  pos = comp.getCurrentPos();
  x=pos[0];
  y=pos[1];
  result += "  <rtsExt:Location rtsExt:x=\""+x+"\" rtsExt:y=\""+y+"\" rtsExt:height=\"-1\" rtsExt:width=\"-1\" rtsExt:direction=\""+comp.dir+"\"/>\n";
  
  //// ExtraProperties
  var keys = [];
  for (var x in ext_props){ keys.push(x);}
  keys.sort();
  for(var i in keys){
    var name = keys[i];
    var val = ext_props[name];
    result += "  <rtsExt:Properties rtsExt:name=\""+name+"\" rtsExt:value=\""+val+"\"/>\n";
  }
  
  result +="</rts:Components>\n";
  return result;

}

/// RtsConnectionProfile
var RtsConnectorProfile=function(conn)
{
  this.start_obj=null;
  this.end_obj=null;

  if(conn.obj){
    this.obj = conn.obj;
    this.connectionType=conn.obj["ConnectionType"];
    this.connectorId=conn.obj["ID"];
    this.name=conn.obj["Name"];
    this.start_obj=conn.start_obj;
    this.end_obj=conn.end_obj;

  }else{
    this.obj = null;
    this.connectionType="";
    this.connectorId="";
    this.name="";
    if(conn.start_obj){ this.start_obj=conn.start_obj; }
    if(conn.end_obj){ this.end_obj=conn.end_obj; }
  }
}

RtsConnectorProfile.prototype.propsXML=function(){
  var result="";
  for (var k in this.obj){
    if(k != 'DestPorts' && k != 'ConnectionType' && k != 'ID' && k != 'Name'){
      result += "  <rtsExt:Properties rtsExt:name=\""+k+"\" rtsExt:value=\""+this.obj[k]+"\" />\n";
    }
  }
  return result;
}

RtsConnectorProfile.prototype.toXML=function(comps){
  var result="";
  var source_obj=null;
  var target_obj=null;
  var sport, eport;

  for(var i in comps){
    if(comps[i].match_port(this.start_obj)){
      source_obj = comps[i];
      sport = this.start_obj.obj
    }
    if(comps[i].match_port(this.end_obj)){
      target_obj = comps[i];
      eport = this.end_obj.obj
    }
  }

  if(!source_obj || !target_obj || !sport || !eport){ return result; }

  if(this.connectionType == 'DataPort'){
    result += "<rts:DataPortConnectors xsi:type=\"rtsExt:dataport_connector_ext\" ";
    result += " rts:name=\""+this.name+"\" rts:connectorId=\""+this.connectorId+"\" ";
    result += " rts:dataType=\""+this.obj['dataport.data_type']+"\"";
    result += " rts:interfaceType=\""+this.obj['dataport.interface_type']+"\"";
    result += " rts:dataflowType=\""+this.obj['dataport.dataflow_type']+"\"";
    result += " rts:subscriptionType=\""+this.obj['dataport.subscription_type']+"\"";
    result += ">\n";
    ///source
    result += source_obj.to_target_portXML("sourceDataPort",sport);
    ///target
    result += target_obj.to_target_portXML('targetDataPort', eport);
    /// Props

    result += this.propsXML();
    result += "</rts:DataPortConnectors>\n"; 
    
  }else if(this.connectionType == 'ServicePort'){
    result += "<rts:ServicePortConnectors xsi:type=\"rtsExt:serviceport_connector_ext\" ";
    result += " rts:name=\""+this.name+"\" rts:connectorId=\""+this.connectorId+"\" ";
    result += ">\n"; 
    ///source
    result += source_obj.to_target_portXML('sourceServicePort', sport)
    ///target
    result += target_obj.to_target_portXML('targetServicePort', eport)
    /// Props
    result += this.propsXML();
    result += "</rts:ServicePortConnectors>\n"; 
  }

  return result;
}

//// RtsProfile
var RtsProfile=function(vendor, sysname, version){
  this.header = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" ;

  this.id = "RTSystem:"+vendor+"."+sysname+":"+ version;
  this.version = version;
  this.creationDate=new Date();
  this.updateDate=new Date();
  this.Abstract = "Created by RTSE on the Web";

  this.Components=[];
  this.Groups = [];
  this.Connectors=[];
  this.StartUp=null;
  this.Shutdown=null;
  this.Activation=null;
  this.Deactivation=null;
  this.Resetting=null;
  this.Initializating=null;
  this.Finalizing=null;
  this.commnet=null;
  this.VersionLog=[];
  this.Properties=[];
  ////
  this.restoreCommands=[];
}

RtsProfile.prototype.formatDate=function(d){
  yy = d.getYear();
  mm = d.getMonth() + 1;
  dd = d.getDate();
  hh = d.getHours();
  jj = d.getMinutes();
  ss = d.getSeconds();
  if (yy < 2000) { yy += 1900; }
  if (mm < 10) { mm = "0" + mm; }
  if (dd < 10) { dd = "0" + dd; }
  if (hh < 10) { hh = "0" + hh; }
  if (jj < 10) { jj = "0" + jj; }
  if (ss < 10) { ss = "0" + ss; }

  return  yy+"-"+mm+"-"+dd+"T"+hh+":"+jj+":"+ss;
}

RtsProfile.prototype.mkRootNode=function(){
  var nodestr = "<rts:RtsProfile rts:id=\""+this.id;
  nodestr += "\" rts:version=\"0.2";
  nodestr += "\" rts:updateDate=\""+this.formatDate(this.creationDate);
  nodestr += "\" rts:creationDate=\""+this.formatDate(this.updateDate);
  nodestr += "\" rts:abstract=\""+this.Abstract;
  nodestr += "\" xmlns:rtsExt=\"http://www.openrtp.org/namespaces/rts_ext\" xmlns:rts=\"http://www.openrtp.org/namespaces/rts\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">";

  return this.header +"\n" + nodestr+"\n";
}

RtsProfile.prototype.pushComponent=function(comp){
  this.Components.push(new RtsComponentProfile(comp));
}

RtsProfile.prototype.pushConnection=function(conn){
  this.Connectors.push(new RtsConnectorProfile(conn));
}

RtsProfile.prototype.toXML=function(){
  var result = this.mkRootNode();

  /// Components
  for(var i=0;i<this.Components.length;i++){
    var comp = this.Components[i];
    result += comp.toXML();
  }

  // Groups:: doesn't support...
  // 
  // DataPortConnectors
  // ServicePortConnetors
  for(var i=0;i<this.Connectors.length;i++){
    var conn = this.Connectors[i];
    result += conn.toXML(this.Components);
  }

  result +="</rts:RtsProfile>\n";
  return result;
}

/////
// Create RTS Profile 
function createRtsProfile(){
  profile = new  RtsProfile("AIST", "RTSEoW", "0.1");
  
  var rtcs = getDisplayedRtcs();
  for(var i=0;i<rtcs.length;i++){
    var comp = rtcs[i];
    profile.pushComponent(comp);
  }

  var conns = getConnectorList();
  for(var i=0;i<conns.length; i++){
    var conn = conns[i];
    profile.pushConnection(conn);
  }
  var txt = profile.toXML();
  var ele = document.getElementById('profile');
  var content ="";

  //content +="<input type=\"button\" onClick=\"handleWriteToFile('rtsprofile');\" value=\"Save\"">";
  content +="<input type=\"text\" onClick=\"changeDownloadFilename();\" value=\"rtse.xml\" id=\"rtsname\">";
  content +="<input type=\"button\" onClick=\"handleDownload('rtsprofile');\" value=\"SetupDownload\">";
  content +="<a id=\"anchor\" href=\"\"></a>";
  content +="<br><textarea cols=\"100\" rows=\"10\" id=\"rtsprofile\">"+txt+"</textarea>";
  ele.innerHTML=content;

  dl_fname="rtse.xml";
  dl_data=txt;
}

function createRtsProfile2(){
  profile = new  RtsProfile("AIST", "RTSEoW", "0.1");
  
  var rtcs = getDisplayedRtcs();
  for(var i=0;i<rtcs.length;i++){
    var comp = rtcs[i];
    profile.pushComponent(comp);
  }

  var conns = getConnectorList();
  for(var i=0;i<conns.length; i++){
    var conn = conns[i];
    profile.pushConnection(conn);
  }
  var txt = profile.toXML();
  var ele = document.getElementById('data_area');
  ele.value=txt;
}

RtsProfile.prototype.addCommands=function(cmds){
  for(var i in cmds){
    this.restoreCommands.push(cmds[i]);
  }
}

/////// RtsCommand
var RtsCommand=function(obj, comm, args){
  this.obj = obj;
  this.command = comm;
  this.args = args;

}

RtsCommand.prototype.action=function(){
  this.command.apply(this.obj, this.args);
  
}

/////////////////////
checkFileApi();
