'use strict';
const $=id=>document.getElementById(id),token=document.querySelector('meta[name="practica-token"]').content;
const money=n=>new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n);
const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
async function api(url,options={}){const response=await fetch(url,{...options,headers:{'X-Practica-Token':token,...options.headers}});const data=await response.json();if(!response.ok)throw new Error(data.error||'No pude completar la solicitud. Inténtalo de nuevo.');return data;}
const post=(url,data)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
const icons={Abarrotes:['M7 6h10l2 15H5L7 6z','M9 6V3h6v3M9 11h6m-7 4h8'],Ferretería:['m5 21 9-9','M14 12a6 6 0 007-7l-4 4-3-3 4-4a6 6 0 00-7 7L2 18a2 2 0 003 3'],Papelería:['M6 2h12v20H6z','M9 6h6m-6 4h6m-6 4h6M3 5h4m-4 5h4m-4 5h4m-4 5h4'],Panadería:['M5 12a5 5 0 010-9h14a5 5 0 010 9v9H5v-9z','M9 7v3m6-3v3'],Miscelánea:['M3 8h18v5H3zM5 13v8h14v-8','M12 8v13M12 8C4 9 5 1 9 3l3 5zm0 0c8 1 7-7 3-5l-3 5z']};
function icon(category){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');for(const d of icons[category]||icons.Miscelánea){const p=document.createElementNS(svg.namespaceURI,'path');p.setAttribute('d',d);svg.append(p);}return svg;}
let category='',products=[],shown=0,catalogPage=1,total=0,catalogLoading=false,catalogGeneration=0;
function productCard(p){const card=node('article',undefined,'product-card'),visual=node('div',undefined,'product-visual');visual.append(icon(p.categoria),node('span',p.categoria,'category-tag'));const bottom=node('div',undefined,'product-bottom'),ask=node('button','↗');ask.type='button';ask.setAttribute('aria-label','Consultar sobre '+p.nombre);ask.addEventListener('click',()=>{openBot();$('bot-text').value='Quiero saber sobre '+p.nombre+' ('+p.codigo+').';$('bot-text').focus();});bottom.append(node('strong',money(p.precio_venta)),ask);card.append(visual,node('h3',p.nombre),node('p',p.codigo+' · '+(p.unidad||'Unidad'),'product-code'),bottom);return card;}
async function catalog(reset=false){
 if(catalogLoading&&!reset)return;const generation=reset?++catalogGeneration:catalogGeneration;
 if(reset){catalogPage=1;products=[];shown=0;$('product-grid').replaceChildren();}
 catalogLoading=true;$('catalog-status').textContent='Buscando tus productos…';
 try{
  if(shown>=products.length){const data=await api('/api/productos?'+new URLSearchParams({q:$('catalog-query').value,categoria:category,pagina:catalogPage}));if(generation!==catalogGeneration)return;products.push(...data.resultados);total=data.total;catalogPage++;}
  const end=Math.min(shown+8,products.length);for(let i=shown;i<end;i++)$('product-grid').append(productCard(products[i]));shown=end;
  $('catalog-status').textContent=total?new Intl.NumberFormat('es-CO').format(total)+' productos para encontrar tu próximo imprescindible.':'No encontramos productos con esa búsqueda. Prueba otro nombre o categoría.';
  $('more-products').hidden=shown>=total;
 }catch(e){if(generation===catalogGeneration)$('catalog-status').textContent=e.message;}finally{if(generation===catalogGeneration)catalogLoading=false;}
}
document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.category;document.querySelectorAll('[data-category]').forEach(c=>{const active=c===b;c.classList.toggle('active',active);c.setAttribute('aria-pressed',String(active));});catalog(true);}));
$('catalog-search').addEventListener('submit',e=>{e.preventDefault();catalog(true);});$('more-products').addEventListener('click',()=>catalog());
function openBot(){const p=$('bot-panel');p.hidden=false;$('bot-launcher').setAttribute('aria-expanded','true');$('bot-text').focus();}
function closeBot(){$('bot-panel').hidden=true;$('bot-launcher').setAttribute('aria-expanded','false');$('bot-launcher').focus();}
$('bot-launcher').addEventListener('click',()=>{$('bot-panel').hidden?openBot():closeBot();});$('bot-close').addEventListener('click',closeBot);document.querySelectorAll('[data-open-bot]').forEach(b=>b.addEventListener('click',openBot));
$('bot-panel').addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();closeBot();}});
let session=null,working=false,flowVersion=0,cancelling=false;
let solicitudId=localStorage.getItem('esquina-asistente-solicitud');
const firstPrompt='Revisa este soporte, busca la venta y ayúdame a resolverlo. No apruebes ni ejecutes operaciones.';
function message(role,text){const msg=node('div',undefined,'bot-message'+(role==='usuario'?' user':''));msg.append(node('span',role==='usuario'?'TÚ':'LA ESQUINA','message-name'),document.createTextNode(text));$('bot-messages').append(msg);$('bot-messages').scrollTop=$('bot-messages').scrollHeight;}
function greeting(){$('bot-messages').replaceChildren();message('asistente','Hola, soy tu asistente de La Esquina.\nAdjunta un comprobante y te ayudo a resolverlo. Si necesito algún dato, te lo preguntaré por aquí.');}
function busy(value,text='Estoy revisando tu comprobante…'){working=value;$('cancel-operation').hidden=!(session||solicitudId);$('bot-progress').hidden=!value;$('bot-progress').lastChild.textContent=text;$('bot-text').disabled=value;$('bot-file').disabled=value;$('bot-send').disabled=value;$('use-example').disabled=value;const confirm=$('confirm-result');if(confirm)confirm.disabled=value;}
function error(e){$('bot-error').textContent=e.message||'No pude completar tu solicitud.';$('bot-error').hidden=false;}
async function task(fn,text){if(working||cancelling)return;const version=flowVersion;$('bot-error').hidden=true;busy(true,text);try{await fn(version);}catch(e){if(version===flowVersion)error(e);}finally{if(version===flowVersion)busy(false);}}
function original(id){$('original-image').src='/archivos/'+id;$('original-dialog').showModal();}
$('close-original').addEventListener('click',()=>$('original-dialog').close());
function renderSession(s){session=s;$('cancel-operation').hidden=false;localStorage.setItem('esquina-asistente',s.id);$('new-conversation').hidden=false;$('bot-messages').replaceChildren();
 const a=node('div',undefined,'attachment-card'),img=node('img');img.src='/archivos/'+s.extraccion.archivo_id;img.alt='Tu comprobante adjunto';const info=node('div');info.append(node('strong','Comprobante recibido'));const see=node('button','Ver original');see.type='button';see.addEventListener('click',()=>original(s.extraccion.archivo_id));info.append(node('br'),see);a.append(img,info);$('bot-messages').append(a);
 for(const m of s.mensajes)if(m.texto!==firstPrompt)message(m.rol,m.texto);
 if(!s.mensajes.length)message('asistente','Ya recibí la imagen. Voy a buscar la información que corresponde.');renderResult(s.propuesta,s.extraccion,s.productos||{});
}
function datum(parent,label,value){const n=node('div');n.append(node('span',label),document.createTextNode(String(value??'No informado')));parent.append(n);}
function renderResult(p,ext,products){const panel=$('bot-result');panel.replaceChildren();panel.hidden=!p;if(!p)return;
 if(p.estado==='ejecutada'){panel.append(node('h3','Listo, quedó guardado.'),node('p','Tu comprobante y su relación comercial están disponibles. La recepción bancaria sigue sin verificar.'));const result=p.resultado||{};if(result.venta_id)panel.append(node('p','Venta '+result.venta_id));return;}
 const composite=p.tipo==='resolver_soporte',d=composite?p.contenido.operacion:p.contenido,r=composite?p.contenido.registro.revision:ext.original,tipo=composite?p.contenido.tipo_operacion:p.tipo;
 panel.append(node('h3',tipo==='crear_venta'?'Tu nueva venta, lista para confirmar.':tipo==='adjuntar_soporte'?'Un soporte más para la misma operación.':'Encontramos cómo asociarlo.'));
 const meta=node('div',undefined,'result-meta');datum(meta,'Comprobante',r.payment_brand_or_medium||'Medio no visible');datum(meta,'Fecha del soporte',r.document_date);datum(meta,'Moneda',d.moneda_confirmada||'COP');datum(meta,'Tipo',d.naturaleza==='financiacion'?'Financiación':'Cobro reportado');if(d.venta_id)datum(meta,'Venta seleccionada',d.venta_id);if(d.fecha_comercial)datum(meta,'Fecha de la venta',d.fecha_comercial);if(d.cliente)datum(meta,'Cliente',d.cliente);panel.append(meta);
 if(d.lineas)for(const l of d.lineas){const row=node('div',undefined,'result-line');row.append(node('span',l.cantidad+' × '+(products[l.producto_codigo]||l.producto_codigo)),node('span',money(l.cantidad*l.precio_unitario)));panel.append(row);}
 if(d.total!=null){const total=node('div',undefined,'result-total');total.append(node('span','Total venta'),node('span',money(d.total)));panel.append(total);}
 const applied=node('div',undefined,'result-total');applied.append(node('span','Importe aplicado'),node('span',money(d.importe_aplicado??r.total_amount)));panel.append(applied);
 const details=node('details'),reading=node('div',undefined,'result-reading');details.append(node('summary','Ver datos del comprobante'));for(const [label,value]of [['Total observado',r.total_amount==null?'No visible':money(r.total_amount)],['Fecha',r.document_date],['Hora',r.document_time?`${r.document_time} (${r.time_precision==='minute'?'precisión de minuto':'precisión de segundo'})`:null],['Moneda visible',r.currency_observed],['Estado visible',r.operation_status_observed],['Comercio',r.merchant_or_store],['Notas',r.notes],['Efectivo mencionado (separado)',r.stated_cash_amount],['Importe inferido (separado)',r.inferred_amount]])reading.append(node('div',label+': '+(value??'No visible / no informado')));for(const [key,value]of Object.entries(r.references))reading.append(node('div',key+': '+(value??'No visible')));if(r.warnings.length)reading.append(node('p',r.warnings.join(' ')));details.append(reading);panel.append(details);
 const see=node('button','Comparar con el original','button outline');see.type='button';see.addEventListener('click',()=>original(ext.archivo_id));panel.append(see,node('p','Revisa el original y este resumen. Al confirmar guardarás los datos y la operación indicada. Si algo no corresponde, dímelo en el chat.'));
 if(p.estado==='borrador'){panel.append(node('p','Faltan datos para dejarlo listo. Completa la información en el chat.'));return;}
 const confirm=node('button','Confirmar y guardar','button dark');confirm.id='confirm-result';confirm.type='button';confirm.disabled=working;confirm.addEventListener('click',()=>task(async version=>{const sid=session.id;
   try{await post('/api/propuestas/'+p.id+'/aprobar',{version:p.version,confirmacion:'REVISADO'});if(version!==flowVersion)return;await post('/api/propuestas/ejecutar',{id:p.id,version:p.version});const s=await api('/api/asistente/'+sid);if(version===flowVersion)renderSession(s);}
   catch(e){if(version===flowVersion){const s=await api('/api/asistente/'+sid);if(version===flowVersion)renderSession(s);}throw e;}
 },'Estoy guardando tu resultado…'));panel.append(confirm);
}
async function send(text,version=flowVersion){if(!text.trim())return;if(!session){message('usuario',text);const response=await post('/api/agente',{texto:text.slice(0,1000)});if(version===flowVersion)message('asistente',response.respuesta);return;}const sid=session.id;const s=await post('/api/asistente/'+sid+'/mensaje',{texto:text});if(version===flowVersion)renderSession(s);}
$('bot-form').addEventListener('submit',e=>{e.preventDefault();const text=$('bot-text').value;task(async version=>{$('bot-text').value='';await send(text,version);},'Estoy preparando tu respuesta…');});
$('bot-text').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('bot-form').requestSubmit();}});
async function attach(file,version=flowVersion){
 if(!file)return;if(file.size>8*1024*1024)throw new Error('La imagen supera 8 MB. Adjunta una imagen más pequeña.');if(!['image/png','image/jpeg'].includes(file.type))throw new Error('Adjunta una imagen PNG o JPG.');
 solicitudId=crypto.randomUUID();localStorage.setItem('esquina-asistente-solicitud',solicitudId);$('cancel-operation').hidden=false;const requestId=solicitudId;
 const form=new FormData();form.append('archivo',file,file.name);const uploaded=await api('/api/archivos',{method:'POST',body:form});if(version!==flowVersion)return;
 const s=await post('/api/asistente/iniciar/'+uploaded.archivo.id,{solicitud_id:requestId});if(version!==flowVersion)return;renderSession(s);if(!s.mensajes.length&&!s.ocupado)await send(firstPrompt,version);
}
$('bot-file').addEventListener('change',()=>{const f=$('bot-file').files[0];openBot();task(async version=>{await attach(f,version);if(version===flowVersion)$('bot-file').value='';});});
$('show-examples').addEventListener('click',async()=>{$('example-options').hidden=!$('example-options').hidden;if(!$('example-select').options.length){try{const rows=await api('/api/casos');for(const r of rows){const opt=node('option',r.nombre);opt.value=r.url;$('example-select').append(opt);}}catch(e){error(e);}}});
$('use-example').addEventListener('click',()=>task(async version=>{const select=$('example-select'),url=select.value;if(!url)return;const response=await fetch(url);if(!response.ok)throw new Error('No pude abrir ese ejemplo.');$('example-options').hidden=true;if(version!==flowVersion)return;await attach(new File([await response.blob()],select.options[select.selectedIndex].text,{type:'image/png'}),version);}));
function resetConversation(){session=null;solicitudId=null;localStorage.removeItem('esquina-asistente');localStorage.removeItem('esquina-asistente-solicitud');$('bot-result').replaceChildren();$('bot-result').hidden=true;$('bot-error').hidden=true;$('new-conversation').hidden=true;$('cancel-operation').hidden=true;$('example-options').hidden=true;$('bot-text').value='';$('bot-file').value='';greeting();}
async function cancelOperation(){
 if(cancelling)return;const request={sesion_id:session?.id||null,solicitud_id:solicitudId||null};flowVersion++;cancelling=true;$('cancel-operation').disabled=true;busy(true,'Cancelando la operación…');
 try{const result=request.sesion_id||request.solicitud_id?await post('/api/asistente/cancelar',request):null;resetConversation();message('asistente',result?.resultado_guardado?'Cerré esta conversación. Los registros que ya guardaste se conservan. Puedes adjuntar otro comprobante.':'Operación cancelada. Ya no usaré ese soporte ni su propuesta en esta conversación. Puedes adjuntar otro comprobante.');}
 catch(e){error(e);}finally{cancelling=false;$('cancel-operation').disabled=false;busy(false);$('bot-text').focus();}
}
$('cancel-operation').addEventListener('click',cancelOperation);
$('new-conversation').addEventListener('click',()=>{if(working||cancelling)return;cancelOperation();});
greeting();catalog(true);$('cancel-operation').hidden=!solicitudId;
const saved=localStorage.getItem('esquina-asistente');if(saved){const version=flowVersion;api('/api/asistente/'+encodeURIComponent(saved)).then(s=>{if(version===flowVersion)renderSession(s);}).catch(()=>{if(version===flowVersion)resetConversation();});}
