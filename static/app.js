'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="practica-token"]').content;
const money = n => new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n);
const dateTime = s => new Date(s).toLocaleString('es-CO');
function el(tag,text,cls) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n; }
function error(e) { $('global-error').textContent=e.message||String(e);$('global-error').hidden=false; }
function clearError() { $('global-error').hidden=true; }
async function api(url,options={}) {
  const response=await fetch(url,{...options,headers:{'X-Practica-Token':token,...options.headers}});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||'No se pudo completar la solicitud.');
  return data;
}
async function task(action) {clearError();try {await action();}catch(e){error(e);}}
async function busy(button,action) {const original=button.textContent;button.disabled=true;button.textContent='Un momento…';try{await action();}finally{button.disabled=false;button.textContent=original;}}
const headings={registros:['Revisar y registrar.','Cada cambio comercial requiere una propuesta y aprobación.','Registros'],mesa:['Cada soporte, en su lugar.','Consulta tus ventas y prepara el siguiente paso.','Mesa de trabajo'],ventas:['Las ventas, a la vista.','Busca y revisa el detalle comercial antes de asociar.','Ventas'],catalogo:['El catálogo de La Esquina.','Una fuente de productos y precios para construir tus ventas.','Catálogo'],practica:['Observa. Consulta. Decide.','Doce soportes para practicar distintos recorridos.','Soportes de práctica']};
function page(name) {
 if(!headings[name])name='mesa';
 document.querySelectorAll('.page').forEach(n=>n.hidden=n.id!=='page-'+name);
 document.querySelectorAll('.nav').forEach(n=>{n.classList.toggle('selected',n.dataset.page===name);if(n.dataset.page===name)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});
 const [title,subtitle,crumb]=headings[name];$('page-title').textContent=title;$('page-subtitle').textContent=subtitle;$('breadcrumb').textContent=crumb;
 location.hash=name;clearError();
 if(name==='registros')task(loadRecords);if(name==='ventas')task(loadSales);if(name==='catalogo')task(loadProducts);if(name==='practica')task(loadSamples);
}
document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>page(b.dataset.page)));
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>page(b.dataset.go)));
window.addEventListener('hashchange',()=>{const name=location.hash.slice(1);if(headings[name]&&!$('page-'+name).hidden)return;page(name);});
async function summary(){const d=await api('/api/resumen');['productos','ventas','archivos'].forEach(k=>$('stat-'+k).textContent=new Intl.NumberFormat('es-CO').format(d[k]));}
function message(role,text,origin="determinista"){const n=el('div',undefined,'message'+(role==='usuario'?' user':''));n.append(el('span',role==='usuario'?'TÚ':(origin==='agente_ia'?'AGENTE IA':'CHAT DE COMANDOS'),'author'),document.createTextNode(text));$('messages').append(n);$('messages').scrollTop=$('messages').scrollHeight;}
async function chatHistory(){const rows=await api('/api/chat');$('messages').replaceChildren();if(!rows.length)message('asistente','Hola. Esta es tu mesa de trabajo. Carga un soporte para conservar su evidencia o escribe «ventas» para consultar SQLite. Reconoce el soporte y revisa sus datos en Registros.');rows.forEach(r=>message(r.rol,r.texto,r.origen));}
let sending=false;
async function sendChat(text){if(sending||!text.trim())return;sending=true;try{await busy($('send-chat'),async()=>{await api($('use-agent').checked?'/api/agente':'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:text})});$('chat-input').value='';await chatHistory();});}finally{sending=false;}}
$('chat-form').addEventListener('submit',e=>{e.preventDefault();task(()=>sendChat($('chat-input').value));});
$('chat-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('chat-form').requestSubmit();}});
document.querySelectorAll('[data-command]').forEach(b=>b.addEventListener('click',()=>task(()=>sendChat(b.dataset.command))));
let selectedFile=null;
function preview(file){selectedFile=file;$('extract-button').disabled=false;$('preview-empty').hidden=true;$('preview').hidden=false;$('preview-image').src='/archivos/'+file.id;$('original-link').href='/archivos/'+file.id;$('file-detail').replaceChildren(el('strong',file.nombre_original),el('div',file.id),el('div','Pendiente de reconocimiento · '+dateTime(file.cargado_en)));}
async function upload(file){
 if(file.size>8*1024*1024)throw new Error('La imagen supera 8 MB.');
 const form=new FormData();form.append('archivo',file,file.name);
 const data=await api('/api/archivos',{method:'POST',body:form});
 preview(data.archivo);$('upload-status').textContent=data.duplicado?'Este mismo archivo ya estaba cargado. Conservamos su ID.':'Imagen conservada en tu equipo. Pendiente de reconocimiento y revisión.';
 await Promise.all([loadFiles(),summary()]);
}
$('upload-form').addEventListener('submit',e=>{e.preventDefault();task(()=>busy($('upload-button'),async()=>{const f=$('upload-input').files[0];if(!f)throw new Error('Selecciona una imagen.');await upload(f);$('upload-input').value='';}));});
async function loadFiles(){const rows=await api('/api/archivos');$('file-list').replaceChildren();if(!rows.length){$('file-list').append(el('p','Aún no has cargado archivos. Elige una imagen o usa un soporte de práctica.','hint'));return;}for(const r of rows){const row=el('div',undefined,'file-row'),info=el('div');info.append(el('strong',r.nombre_original),el('small',r.id+' · Pendiente de reconocimiento'),el('small',dateTime(r.cargado_en)));const b=el('button','Ver soporte','secondary');b.addEventListener('click',()=>{preview(r);page('mesa');$('preview').scrollIntoView({block:'center'});});row.append(info,b);$('file-list').append(row);}}
$('refresh-files').addEventListener('click',()=>task(()=>busy($('refresh-files'),loadFiles)));
function openDialog(title,content){$('dialog-title').textContent=title;$('dialog-content').replaceChildren(content);$('detail-dialog').showModal();}
$('close-dialog').addEventListener('click',()=>$('detail-dialog').close());
function enlarge(src,title){const img=el('img',undefined,'zoom-image');img.src=src;img.alt=title;openDialog(title,img);}
$('enlarge').addEventListener('click',()=>enlarge($('preview-image').src,'Soporte original'));
function table(headers,rows){const t=el('table'),head=el('thead'),hr=el('tr'),body=el('tbody');headers.forEach(h=>{const n=el('th',h);n.scope='col';hr.append(n);});head.append(hr);rows.forEach(cells=>{const r=el('tr');cells.forEach(c=>{const td=el('td');if(c instanceof Node)td.append(c);else td.textContent=c;r.append(td);});body.append(r);});t.append(head,body);return t;}
async function loadSales(){const params=new URLSearchParams({q:$('sales-q').value,importe:$('sales-amount').value,fecha:$('sales-date').value});const rows=await api('/api/ventas?'+params);$('sales-count').textContent=rows.length+' ventas encontradas'+(rows.length?'':'. Prueba otros criterios: no encontrar un total exacto no demuestra que falte la venta.');$('sales-table').replaceChildren(table(['Venta','Fecha comercial','Cliente','Total COP','Detalle'],rows.map(v=>{const b=el('button','Abrir','table-action');b.setAttribute('aria-label','Abrir venta '+v.id);b.addEventListener('click',()=>task(()=>saleDetail(v.id)));return [v.id,v.fecha_comercial,v.cliente||'Sin cliente',el('span',money(v.total),'number'),b];})));}
$('sales-form').addEventListener('submit',e=>{e.preventDefault();task(()=>busy(e.submitter,loadSales));});
$('clear-sales').addEventListener('click',()=>{$('sales-form').reset();task(loadSales);});
async function saleDetail(id){const v=await api('/api/ventas/'+id),content=el('div'),meta=el('div',undefined,'detail-meta');for(const [label,value]of [['Fecha comercial',v.fecha_comercial],['Cliente',v.cliente||'Sin cliente'],['Factura externa',v.factura_externa||'No informada'],['Origen',v.origen]]){const n=el('div');n.append(el('span',label),document.createTextNode(value));meta.append(n);}content.append(meta);const wrap=el('div',undefined,'table-wrap');wrap.append(table(['Producto','Cantidad','Precio COP','Subtotal COP'],v.lineas.map(l=>[l.producto_codigo+' · '+l.nombre,l.cantidad,money(l.precio_unitario),money(l.subtotal)])));content.append(wrap,el('p','Total '+money(v.total)+' COP','total'),el('p',v.vinculos.length?v.vinculos.map(x=>x.id+' · '+money(x.importe)+' · '+x.naturaleza+' · '+x.estado_financiero).join(' | '):'Sin vínculos comerciales. La revisión de una imagen no verifica el abono bancario.','info'));openDialog('Venta '+id,content);}
let productsPage=1;
async function loadProducts(){const data=await api('/api/productos?'+new URLSearchParams({q:$('products-q').value,pagina:productsPage}));$('products-count').textContent=data.total+' productos encontrados';$('products-page').textContent='Página '+productsPage+' de '+Math.max(1,Math.ceil(data.total/30));$('previous-products').disabled=productsPage<=1;$('next-products').disabled=productsPage*30>=data.total;$('products-table').replaceChildren(table(['Código','Producto','Categoría','Unidad','Precio COP'],data.resultados.map(p=>[p.codigo,p.nombre,p.categoria,p.unidad,el('span',money(p.precio_venta),'number')])));}
$('products-form').addEventListener('submit',e=>{e.preventDefault();productsPage=1;task(()=>busy(e.submitter,loadProducts));});
$('previous-products').addEventListener('click',()=>{if(productsPage>1){productsPage--;task(loadProducts);}});
$('next-products').addEventListener('click',()=>{productsPage++;task(loadProducts);});
let samplesLoaded=false;
async function loadSamples(){if(samplesLoaded)return;const rows=await api('/api/casos');$('sample-list').replaceChildren();for(const r of rows){const card=el('article',undefined,'sample-card'),img=el('img');img.src=r.url;img.alt=r.nombre+' anonimizado';img.loading='lazy';const controls=el('div',undefined,'sample-buttons'),see=el('button','Ampliar','secondary'),use=el('button','Cargar a mi práctica','primary');see.addEventListener('click',()=>enlarge(r.url,r.nombre));use.addEventListener('click',()=>task(()=>busy(use,async()=>{const response=await fetch(r.url);if(!response.ok)throw new Error('No se pudo leer el soporte de práctica.');await upload(new File([await response.blob()],r.nombre,{type:'image/png'}));page('mesa');$('preview').scrollIntoView({block:'center'});})));controls.append(see,use);card.append(img,el('h3',r.nombre),controls);$('sample-list').append(card);}samplesLoaded=true;}
task(async()=>{await Promise.all([summary(),chatHistory(),loadFiles(),loadConfig()]);const files=await api('/api/archivos');if(files.length)preview(files[0]);page(location.hash.slice(1)||'mesa');});

function post(url,data){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
async function loadConfig(){const c=await api('/api/configuracion');$('ia-status').textContent=c.api_configurada?'IA configurada · OCR '+c.ocr_model+' · Agente '+c.chat_model:'Configura tu clave en backend/.env para usar IA. Las consultas y revisiones locales siguen disponibles.';}
$('use-agent').addEventListener('change',()=>{$('chat-mode').textContent=$('use-agent').checked?'Agente IA · gpt-5.6-luna':'Chat de comandos';});
$('extract-button').addEventListener('click',()=>task(()=>busy($('extract-button'),async()=>{
 if(!selectedFile)throw new Error('Selecciona un soporte.');
 $('extract-status').textContent='Reconociendo el soporte…';
 try{const ext=await post('/api/extraer/'+selectedFile.id,{});page('registros');await reviewExtraction(ext.id);$('extract-status').textContent='Extracción conservada. Revisa el original.';}
 catch(e){$('extract-status').textContent='No se completó el reconocimiento.';throw e;}
})));
$('refresh-records').addEventListener('click',()=>task(loadRecords));
function actionButton(text,action){const b=el('button',text,'secondary');b.type='button';b.addEventListener('click',()=>task(()=>busy(b,action)));return b;}
function field(parent,label,value='',type='text'){
 const wrap=el('div',undefined,'edit-field'),id='field-'+crypto.randomUUID(),input=el(type==='textarea'?'textarea':type==='select'?'select':'input');
 input.id=id;if(type!=='textarea'&&type!=='select')input.type=type;
 if(type==='number')input.step='1';if(type==='textarea')input.rows=4;
 input.value=value===null?'':value;const lab=el('label',label);lab.htmlFor=id;wrap.append(lab,input);parent.append(wrap);return input;
}
function check(parent,label){const lab=el('label',undefined,'review-check'),input=el('input');input.type='checkbox';lab.append(input,document.createTextNode(' '+label));parent.append(lab);return input;}
function details(parent,label,data){const d=el('details'),pre=el('pre',JSON.stringify(data,null,2));d.append(el('summary',label),pre);parent.append(d);}
function showPanel(id){const p=$(id);p.hidden=false;p.replaceChildren();return p;}
async function loadRecords(){
 const data=await api('/api/registros'),list=$('records-list');list.replaceChildren();
 for(const [title,rows,make] of [
 ['Lecturas conservadas',data.extracciones,r=>actionButton(r.comprobante_id?'Consultar '+r.comprobante_id:'Revisar '+r.id,()=>r.comprobante_id?showReceipt(r.comprobante_id):reviewExtraction(r.id))],
 ['Comprobantes revisados',data.comprobantes,r=>actionButton('Abrir '+r.id,()=>showReceipt(r.id))],
 ['Propuestas y borradores',data.propuestas,r=>actionButton(r.id+' · v'+r.version+' · '+r.tipo+' · '+r.estado,()=>showProposal(r.id))]]){
 list.append(el('h3',title));if(!rows.length)list.append(el('p','No hay registros.','hint'));rows.forEach(r=>{const row=el('div',undefined,'file-row');row.append(make(r));list.append(row);});
 }
 if(data.operaciones.length){list.append(el('h3','Operaciones existentes'));data.operaciones.forEach(o=>list.append(el('p',o.id+' · '+o.naturaleza+' · '+money(o.monto)+' · '+o.estado_financiero)));}
}
const labels={document_type:'Tipo de documento',payment_brand_or_medium:'Marca o medio de pago',currency_observed:'Moneda visible',operation_status_observed:'Estado visible de la operación',amount_basis:'Base del importe',total_amount:'Importe total observado',inferred_amount:'Importe inferido (separado)',stated_cash_amount:'Efectivo mencionado (no se suma)',document_date:'Fecha del documento',document_time:'Hora del documento',time_precision:'Precisión de la hora',merchant_or_store:'Comercio identificado',notes:'Notas económicas visibles'};
async function reviewExtraction(id){
 const ext=await api('/api/extracciones/'+id),panel=showPanel('review-panel');panel.append(el('h2','Revisar lectura '+id),el('p',ext.origen+' · '+ext.modelo+' · '+ext.creado_en,'hint'));
 const img=el('img',undefined,'review-original');img.src='/archivos/'+ext.archivo_id;img.alt='Original para revisar la extracción';panel.append(img);
 const data=structuredClone(ext.original),grid=el('div',undefined,'edit-grid'),inputs={};
 const choices={document_type:['','card_voucher','transfer','addi_credit','sistecredito_credit','expense'],amount_basis:['observed_total','financed_value','missing'],time_precision:['','minute','second']};
 for(const [k,label] of Object.entries(labels)){
  const type=choices[k]?'select':['total_amount','inferred_amount','stated_cash_amount'].includes(k)?'number':k==='notes'?'textarea':'text';
  const input=field(grid,label,data[k],type);if(choices[k]){choices[k].forEach(v=>{const opt=el('option',v||'No visible');opt.value=v;input.append(opt);});input.value=data[k]||'';}inputs[k]=input;
 }
 panel.append(grid);panel.append(el('h3','Referencias (texto; conservar ceros iniciales)'));const refs=el('div',undefined,'edit-grid'),refInputs={};for(const [k,v]of Object.entries(data.references))refInputs[k]=field(refs,k,v);panel.append(refs);
 details(panel,'Extracción original, confianza, advertencias y evidencia textual',ext.original);
 const motivo=field(panel,'Constancia de revisión y motivo de las correcciones','','textarea');
 const revisado=check(panel,'Revisé los campos contra el original visible.');
 panel.append(actionButton('Preparar registro del comprobante',async()=>{
  if(!revisado.checked)throw new Error('Revisa el original y marca la constancia.');
  for(const [k,input]of Object.entries(inputs))data[k]=input.value===''?null:['total_amount','inferred_amount','stated_cash_amount'].includes(k)?Number(input.value):input.value;
  for(const [k,input]of Object.entries(refInputs))data.references[k]=input.value===''?null:input.value;
  const p=await post('/api/comprobantes',{extraccion_id:id,revision:data,motivo:motivo.value});await loadRecords();await showProposal(p.id);
 }));panel.scrollIntoView({block:'start'});
}
async function showReceipt(id){
 const c=await api('/api/comprobantes/'+id),p=showPanel('review-panel');p.append(el('h2','Comprobante '+id));
 const img=el('img',undefined,'review-original');img.src='/archivos/'+c.extraccion.archivo_id;img.alt='Soporte original del comprobante revisado';p.append(img);
 renderRevision(p,c.revision);details(p,'Revisión guardada completa',c.revision);details(p,'Extracción original y procedencia',c.extraccion);details(p,'Correcciones humanas',c.correcciones);
 if(c.operaciones.length){c.operaciones.forEach(o=>p.append(el('p',o.id+' · '+o.naturaleza+' · '+money(o.importe)+' aplicado a '+o.venta_id+' · Sin verificación bancaria','info')));details(p,'Operación y vínculo comercial · sin verificación bancaria',c.operaciones);}
 else {p.append(actionButton('Buscar venta y preparar operación',()=>operationForm(c)));}
 p.scrollIntoView({block:'start'});
}
async function operationForm(c,existing=null){
 const panel=showPanel('operation-panel');panel.append(el('h2','Operación para '+c.id));
 const search=field(panel,'Buscar ventas por ID o cliente'),amount=field(panel,'Filtro opcional por total COP',c.revision.total_amount,'number'),results=el('div');
 const sale=field(panel,'Venta seleccionada (ID exacto)',existing?.contenido.venta_id||'');
 panel.append(actionButton('Buscar candidatos',async()=>{const rows=await api('/api/ventas?'+new URLSearchParams({q:search.value,importe:amount.value}));results.replaceChildren(el('p',rows.length+' candidatos. Selecciona con el comerciante; el monto solo es un indicio.'));rows.forEach(v=>results.append(actionButton(v.id+' · '+v.fecha_comercial+' · '+(v.cliente||'Sin cliente')+' · '+money(v.total),async()=>{sale.value=v.id;await saleDetail(v.id);})));}),results);
 const create=check(panel,'El comerciante confirma que falta registrar la venta. Crear una venta nueva.');
 const fecha=field(panel,'Fecha comercial (para venta nueva)',existing?.contenido.fecha_comercial||'','date'),cliente=field(panel,'Cliente confirmado (opcional)',existing?.contenido.cliente||''),factura=field(panel,'Factura externa confirmada (opcional)',existing?.contenido.factura_externa||'');
 panel.append(el('h3','Productos para la venta nueva'));const catalogQuery=field(panel,'Buscar producto por nombre o código'),catalogResults=el('div'),lineList=el('div');let lines=existing?.contenido.lineas?structuredClone(existing.contenido.lineas):[];
 function renderLines(){lineList.replaceChildren();for(const [index,l]of lines.entries()){const row=el('div',undefined,'line-edit');row.append(el('span',l.producto_codigo+' · '+money(l.precio_unitario)));const qty=field(row,'Cantidad',l.cantidad,'number');qty.min='1';qty.addEventListener('change',()=>{l.cantidad=Number(qty.value);renderLines();});row.append(actionButton('Quitar',async()=>{lines.splice(index,1);renderLines();}));lineList.append(row);}lineList.append(el('p','Total orientativo '+money(lines.reduce((n,l)=>n+l.cantidad*l.precio_unitario,0))+'. El servidor volverá a calcularlo.'));}
 panel.append(actionButton('Consultar catálogo',async()=>{const data=await api('/api/productos?'+new URLSearchParams({q:catalogQuery.value}));catalogResults.replaceChildren();data.resultados.forEach(p=>catalogResults.append(actionButton(p.codigo+' · '+p.nombre+' · '+money(p.precio_venta),async()=>{if(lines.some(l=>l.producto_codigo===p.codigo))throw new Error('Ya agregaste ese producto. Cambia su cantidad.');lines.push({producto_codigo:p.codigo,cantidad:1,precio_unitario:p.precio_venta});renderLines();})));}),catalogResults,lineList);renderLines();
 const aplicado=field(panel,'Importe que se aplicará a la venta COP',existing?.contenido.importe_aplicado||c.revision.total_amount,'number');
 const cop=check(panel,'Confirmo que la moneda comercial es COP.'),unique=check(panel,'Comparé referencias y operaciones existentes. Este soporte describe una operación aún no registrada.'),review=check(panel,'Confirmé con el comerciante la venta, los productos, cantidades y precios que corresponden.');
 panel.append(el('p','Si es otra foto de una operación existente, adjúntala sin crear dinero adicional.','info'));
 const opId=field(panel,'ID de operación existente (solo para adjuntar)'),same=check(panel,'Confirmo que se trata de la misma operación y revisé sus referencias.');
 function payload(draft){return {tipo:create.checked?'crear_venta':'asociar',borrador:draft,...(existing?{id:existing.id,version:existing.version}:{}),contenido:{comprobante_id:c.id,venta_id:sale.value,moneda_confirmada:cop.checked?'COP':null,confirmacion_operacion_unica:unique.checked,confirmacion_venta_faltante:create.checked,fecha_comercial:fecha.value,cliente:cliente.value||null,factura_externa:factura.value||null,lineas:lines,importe_aplicado:aplicado.value===''?null:Number(aplicado.value)}};}
 create.checked=existing?.tipo==='crear_venta';
 panel.append(actionButton('Guardar borrador incompleto',async()=>{const p=await post('/api/propuestas',payload(true));await loadRecords();await showProposal(p.id);}),actionButton('Preparar propuesta comercial',async()=>{if(!review.checked)throw new Error('Confirma los datos comerciales con la persona.');const p=await post('/api/propuestas',payload(false));await loadRecords();await showProposal(p.id);}),actionButton('Proponer adjuntar a operación existente',async()=>{const p=await post('/api/propuestas',{tipo:'adjuntar_soporte',contenido:{comprobante_id:c.id,operacion_id:opId.value,confirmacion_mismo_documento:same.checked}});await loadRecords();await showProposal(p.id);}));panel.scrollIntoView({block:'start'});
}
async function showProposal(id){
 const p=await api('/api/propuestas/'+id),panel=showPanel('proposal-panel');panel.append(el('h2','Propuesta '+p.id),el('p','Versión '+p.version+' · '+p.tipo+' · '+p.estado));
 renderProposal(panel,p);details(panel,'Datos completos de la propuesta',p.contenido);
 if(p.tipo==='registrar_comprobante'){const ext=await api('/api/extracciones/'+p.contenido.extraccion_id),img=el('img',undefined,'review-original');img.src='/archivos/'+ext.archivo_id;img.alt='Original para aprobar la revisión';panel.append(img);}
 if(['borrador','pendiente','aprobada'].includes(p.estado)&&['asociar','crear_venta'].includes(p.tipo))panel.append(actionButton('Editar propuesta (invalida la aprobación)',async()=>operationForm(await api('/api/comprobantes/'+p.contenido.comprobante_id),p)));
 if(p.estado==='pendiente'){
  const approve=check(panel,'Revisé exactamente este contenido y apruebo la versión '+p.version+'.');
  panel.append(actionButton('Aprobar esta versión',async()=>{if(!approve.checked)throw new Error('Revisa el contenido y confirma la aprobación.');await post('/api/propuestas/'+id+'/aprobar',{version:p.version,confirmacion:'REVISADO'});await loadRecords();await showProposal(id);}));
 }
 if(p.estado==='aprobada')panel.append(actionButton('Ejecutar versión aprobada',async()=>{await post('/api/propuestas/ejecutar',{id,version:p.version});await Promise.all([loadRecords(),summary()]);await showProposal(id);}));
 if(p.resultado){panel.append(el('p','Operación guardada. Resultado persistente:','status'));details(panel,'Resultado',p.resultado);if(p.resultado.comprobante_id)panel.append(actionButton('Consultar comprobante',()=>showReceipt(p.resultado.comprobante_id)));if(p.resultado.venta_id)panel.append(actionButton('Consultar venta y vínculo',()=>saleDetail(p.resultado.venta_id)));}
 panel.scrollIntoView({block:'start'});
}
function renderRevision(parent,r){const wrap=el('div',undefined,'table-wrap');wrap.append(table(['Campo revisado','Valor'],Object.entries(labels).map(([k,label])=>[label,r[k]===null?'No visible / no informado':String(r[k])])));parent.append(wrap);const refs=Object.entries(r.references).filter(([,v])=>v!==null);parent.append(el('p',refs.length?'Referencias: '+refs.map(([k,v])=>k+': '+v).join(' · '):'Sin referencias visibles.'));if(r.warnings.length)parent.append(el('p',r.warnings.join(' · '),'info'));}
function renderProposal(parent,p){
 const d=p.contenido;
 if(p.tipo==='registrar_comprobante'){parent.append(el('p','Registrar un comprobante revisado. No genera un pago ni un vínculo comercial.','info'));renderRevision(parent,d.revision);parent.append(el('p','Constancia: '+d.motivo));return;}
 if(p.tipo==='adjuntar_soporte'){parent.append(el('p','Adjuntar '+d.comprobante_id+' a '+d.operacion_id+'. No se creará una operación adicional.','info'));return;}
 const rows=[['Comprobante',d.comprobante_id],['Naturaleza',d.naturaleza||'Por completar'],['Moneda',d.moneda_confirmada||'Por confirmar'],['Importe aplicado',d.importe_aplicado==null?'Pendiente':money(d.importe_aplicado)],['Venta',d.venta_id||'Nueva venta'],['Fecha comercial',d.fecha_comercial||'Consultar venta seleccionada'],['Cliente',d.cliente||'No informado'],['Factura externa',d.factura_externa||'No informada']];parent.append(table(['Dato comercial','Valor'],rows));
 if(d.lineas?.length)parent.append(table(['Producto','Cantidad','Precio COP','Subtotal COP'],d.lineas.map(l=>[l.producto_codigo,l.cantidad,money(l.precio_unitario),money(l.cantidad*l.precio_unitario)])));
 if(d.total!=null)parent.append(el('p','Total de venta '+money(d.total),'total'));parent.append(el('p','El vínculo es comercial. La recepción de dinero sigue sin verificar.','info'));
}
