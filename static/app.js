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
const headings={mesa:['Cada soporte, en su lugar.','Consulta tus ventas y prepara el siguiente paso.','Mesa de trabajo'],ventas:['Las ventas, a la vista.','Busca y revisa el detalle comercial antes de asociar.','Ventas'],catalogo:['El catálogo de La Esquina.','Una fuente de productos y precios para construir tus ventas.','Catálogo'],practica:['Observa. Consulta. Decide.','Doce soportes para practicar distintos recorridos.','Soportes de práctica']};
function page(name) {
 if(!headings[name])name='mesa';
 document.querySelectorAll('.page').forEach(n=>n.hidden=n.id!=='page-'+name);
 document.querySelectorAll('.nav').forEach(n=>{n.classList.toggle('selected',n.dataset.page===name);if(n.dataset.page===name)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});
 const [title,subtitle,crumb]=headings[name];$('page-title').textContent=title;$('page-subtitle').textContent=subtitle;$('breadcrumb').textContent=crumb;
 location.hash=name;clearError();
 if(name==='ventas')task(loadSales);if(name==='catalogo')task(loadProducts);if(name==='practica')task(loadSamples);
}
document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>page(b.dataset.page)));
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>page(b.dataset.go)));
window.addEventListener('hashchange',()=>{const name=location.hash.slice(1);if(headings[name]&&!$('page-'+name).hidden)return;page(name);});
async function summary(){const d=await api('/api/resumen');['productos','ventas','archivos'].forEach(k=>$('stat-'+k).textContent=new Intl.NumberFormat('es-CO').format(d[k]));}
function message(role,text){const n=el('div',undefined,'message'+(role==='usuario'?' user':''));n.append(el('span',role==='usuario'?'TÚ':'CHAT DE PRÁCTICA','author'),document.createTextNode(text));$('messages').append(n);$('messages').scrollTop=$('messages').scrollHeight;}
async function chatHistory(){const rows=await api('/api/chat');$('messages').replaceChildren();if(!rows.length)message('asistente','Hola. Esta es tu mesa de trabajo. Carga un soporte para conservar su evidencia o escribe «ventas» para consultar SQLite. El reconocimiento y las operaciones comerciales se construyen en clase.');rows.forEach(r=>message(r.rol,r.texto));}
let sending=false;
async function sendChat(text){if(sending||!text.trim())return;sending=true;try{await busy($('send-chat'),async()=>{await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:text})});$('chat-input').value='';await chatHistory();});}finally{sending=false;}}
$('chat-form').addEventListener('submit',e=>{e.preventDefault();task(()=>sendChat($('chat-input').value));});
$('chat-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('chat-form').requestSubmit();}});
document.querySelectorAll('[data-command]').forEach(b=>b.addEventListener('click',()=>task(()=>sendChat(b.dataset.command))));
function preview(file){$('preview-empty').hidden=true;$('preview').hidden=false;$('preview-image').src='/archivos/'+file.id;$('original-link').href='/archivos/'+file.id;$('file-detail').replaceChildren(el('strong',file.nombre_original),el('div',file.id),el('div','Pendiente de reconocimiento · '+dateTime(file.cargado_en)));}
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
async function saleDetail(id){const v=await api('/api/ventas/'+id),content=el('div'),meta=el('div',undefined,'detail-meta');for(const [label,value]of [['Fecha comercial',v.fecha_comercial],['Cliente',v.cliente||'Sin cliente'],['Factura externa',v.factura_externa||'No informada'],['Origen','Venta ficticia de práctica']]){const n=el('div');n.append(el('span',label),document.createTextNode(value));meta.append(n);}content.append(meta);const wrap=el('div',undefined,'table-wrap');wrap.append(table(['Producto','Cantidad','Precio COP','Subtotal COP'],v.lineas.map(l=>[l.producto_codigo+' · '+l.nombre,l.cantidad,money(l.precio_unitario),money(l.subtotal)])));content.append(wrap,el('p','Total '+money(v.total)+' COP','total'),el('p','Sin pagos asociados. La revisión de una imagen no verifica el abono bancario.','info'));openDialog('Venta '+id,content);}
let productsPage=1;
async function loadProducts(){const data=await api('/api/productos?'+new URLSearchParams({q:$('products-q').value,pagina:productsPage}));$('products-count').textContent=data.total+' productos encontrados';$('products-page').textContent='Página '+productsPage+' de '+Math.max(1,Math.ceil(data.total/30));$('previous-products').disabled=productsPage<=1;$('next-products').disabled=productsPage*30>=data.total;$('products-table').replaceChildren(table(['Código','Producto','Categoría','Unidad','Precio COP'],data.resultados.map(p=>[p.codigo,p.nombre,p.categoria,p.unidad,el('span',money(p.precio_venta),'number')])));}
$('products-form').addEventListener('submit',e=>{e.preventDefault();productsPage=1;task(()=>busy(e.submitter,loadProducts));});
$('previous-products').addEventListener('click',()=>{if(productsPage>1){productsPage--;task(loadProducts);}});
$('next-products').addEventListener('click',()=>{productsPage++;task(loadProducts);});
let samplesLoaded=false;
async function loadSamples(){if(samplesLoaded)return;const rows=await api('/api/casos');$('sample-list').replaceChildren();for(const r of rows){const card=el('article',undefined,'sample-card'),img=el('img');img.src=r.url;img.alt=r.nombre+' anonimizado';img.loading='lazy';const controls=el('div',undefined,'sample-buttons'),see=el('button','Ampliar','secondary'),use=el('button','Cargar a mi práctica','primary');see.addEventListener('click',()=>enlarge(r.url,r.nombre));use.addEventListener('click',()=>task(()=>busy(use,async()=>{const response=await fetch(r.url);if(!response.ok)throw new Error('No se pudo leer el soporte de práctica.');await upload(new File([await response.blob()],r.nombre,{type:'image/png'}));page('mesa');$('preview').scrollIntoView({block:'center'});})));controls.append(see,use);card.append(img,el('h3',r.nombre),controls);$('sample-list').append(card);}samplesLoaded=true;}
task(async()=>{await Promise.all([summary(),chatHistory(),loadFiles()]);const files=await api('/api/archivos');if(files.length)preview(files[0]);page(location.hash.slice(1)||'mesa');});
