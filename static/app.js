'use strict';
const $ = id => document.getElementById(id);
let token = new URLSearchParams(location.hash.slice(1)).get('token') || sessionStorage.getItem('nodavira-token');
if (token) sessionStorage.setItem('nodavira-token', token);
history.replaceState(null, '', '/');
let catalog = [], defaults = [], selected = new Set(), latest = null, filter = 'all', busy = false, loaded = false;
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (value, digits=1) => value == null ? '—' : Number(value).toLocaleString('pt-BR', {maximumFractionDigits:digits, minimumFractionDigits:digits});
const protocolLabel = p => ({udp:'UDP',doh:'DoH',dot:'DoT'}[p] || p);
function showError(message) { $('error').textContent = message; $('error').classList.remove('hidden'); }
async function api(path, body) {
  const result = await fetch('/api/' + path, {method:body === undefined ? 'GET' : 'POST', headers:{'X-Nodavira-Token':token || '', 'Content-Type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await result.json();
  if (!result.ok) throw Error(data.error || 'Não foi possível concluir a operação.');
  return data;
}
function view(name) {
  document.querySelectorAll('.view').forEach(el => el.classList.toggle('hidden', el.id !== 'view-' + name));
  document.querySelectorAll('.nav').forEach(el => el.classList.toggle('active', el.dataset.view === name));
  window.scrollTo(0,0);
}
document.querySelectorAll('[data-view]').forEach(el => el.addEventListener('click', () => view(el.dataset.view)));
function getDomains() { return [...new Set($('domains').value.split(/[\s,;]+/).map(x=>x.trim()).filter(Boolean))]; }
function updateSummary() {
  const domains = getDomains();
  $('selected-count').textContent = selected.size + ' selecionados';
  $('domain-count').textContent = domains.length;
  $('config-summary').textContent = `${selected.size} servidores · ${domains.length} domínios · ${$('rounds').value} passagens`;
}
function renderResolvers() {
  const groups = [...new Set(catalog.map(r=>r.name))];
  $('resolver-list').innerHTML = groups.map(name => {
    const items = catalog.filter(r=>r.name === name);
    return `<div class="resolver-group"><h3>${escapeHTML(name)}</h3><p>${escapeHTML(items[0].policy)}</p>${items.map(r=>`<label class="resolver-option"><input type="checkbox" data-resolver="${escapeHTML(r.id)}" ${selected.has(r.id)?'checked':''} ${busy?'disabled':''}><b>${protocolLabel(r.protocol)}</b><span class="family">${r.family}</span><span class="address" title="${escapeHTML(r.address)}">${escapeHTML(r.address)}</span></label>`).join('')}</div>`;
  }).join('');
  $('resolver-list').querySelectorAll('input').forEach(input=>input.addEventListener('change',()=>{
    input.checked ? selected.add(input.dataset.resolver) : selected.delete(input.dataset.resolver);
    $('profile').value='custom'; updateSummary();
  }));
  updateSummary();
}
function selectDefault() { selected = new Set(catalog.filter(r=>r.family==='IPv4' && r.protocol!=='dot').map(r=>r.id)); renderResolvers(); }
$('select-default').onclick=()=>{selectDefault();$('profile').value='custom';};
$('select-ipv6').onclick=()=>{catalog.filter(r=>r.family==='IPv6'&&r.protocol!=='dot').forEach(r=>selected.add(r.id));renderResolvers();$('profile').value='custom';};
$('clear-servers').onclick=()=>{selected.clear();renderResolvers();$('profile').value='custom';};
['domains','rounds','concurrency','timeout','qtype-a','qtype-aaaa'].forEach(id=>$(id).addEventListener('input',()=>{$('profile').value='custom';updateSummary();}));
$('restore-domains').onclick=()=>{$('domains').value=defaults.join('\n');$('profile').value='custom';updateSummary();};
$('profile').onchange=()=>{if($('profile').value==='custom')return;const quick=$('profile').value==='quick';$('domains').value=(quick?defaults.slice(0,12):defaults).join('\n');$('rounds').value=quick?2:3;$('concurrency').value=4;$('timeout').value=1500;$('qtype-a').checked=$('qtype-aaaa').checked=true;selectDefault();};
$('custom-form').onsubmit=event=>{
  event.preventDefault();const protocol=$('custom-protocol').value, endpoint=$('custom-host').value.trim(), address=$('custom-ip').value.trim();
  if(protocol!=='udp'&&!endpoint){$('custom-message').textContent='Informe a URL HTTPS ou o hostname TLS.';return;}
  const item={id:'custom-'+Date.now(),name:$('custom-name').value.trim(),address,protocol,hostname:protocol==='dot'?endpoint:'',url:protocol==='doh'?endpoint:'',family:address.includes(':')?'IPv6':'IPv4',policy:'Personalizado',port:{udp:53,doh:443,dot:853}[protocol]};
  catalog.push(item);selected.add(item.id);renderResolvers();$('profile').value='custom';$('custom-message').textContent='Servidor adicionado. O endereço será validado ao iniciar.';$('custom-form').reset();
};
$('import-domains').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  try{
    if(file.size>30*1024*1024)throw Error('Use um arquivo de até 30 MB.');
    const content=await file.text();let names=[];
    if(/\.(har|json)$/i.test(file.name)){
      const data=JSON.parse(content);if(!Array.isArray(data.log?.entries))throw Error('O arquivo não contém requisições HAR.');
      for(const entry of data.log.entries){try{const url=new URL(entry.request.url);if(['http:','https:'].includes(url.protocol)&&url.hostname.includes('.')&&!/^\d+(\.\d+){3}$/.test(url.hostname))names.push(url.hostname);}catch{}}
    }else names=content.split(/[\s,;]+/).filter(Boolean);
    names=[...new Set(names.map(x=>x.toLowerCase()))];if(!names.length)throw Error('Nenhum domínio encontrado.');
    $('domains').value=names.slice(0,300).join('\n');$('profile').value='custom';updateSummary();
    $('import-message').textContent=`${Math.min(names.length,300)} domínios importados${names.length>300?' (limitado aos primeiros 300)':''}.`;
  }catch(error){$('import-message').textContent=error.message;}finally{event.target.value='';}
};
function config(){return{resolvers:catalog.filter(r=>selected.has(r.id)),domains:getDomains(),rounds:Number($('rounds').value),concurrency:Number($('concurrency').value),timeout_ms:Number($('timeout').value),qtypes:[$('qtype-a').checked?'A':null,$('qtype-aaaa').checked?'AAAA':null].filter(Boolean)};}
function setBusy(value){
  busy=value;$('start').disabled=value||!loaded;$('stop').classList.toggle('hidden',!value);$('profile').disabled=value;
  document.querySelectorAll('#view-settings input,#view-settings textarea,#view-settings select,#view-settings button').forEach(el=>el.disabled=value);
}
$('start').onclick=async()=>{
  $('error').classList.add('hidden');setBusy(true);
  try{await api('start',config());latest=await api('status');render();}catch(error){showError(error.message);setBusy(false);}
};
$('stop').onclick=async()=>{try{await api('stop',{});$('stop').disabled=true;$('progress-message').textContent='Concluindo as consultas em andamento…';}catch(error){showError(error.message);}};
$('shutdown').onclick=async()=>{try{await api('shutdown',{});clearInterval(pollTimer);$('start').disabled=true;showError('Aplicativo encerrado. Você pode fechar esta janela.');}catch(error){showError(error.message);}};
function render(){
  if(!latest)return;const running=latest.state==='running';setBusy(running);if(!running)$('stop').disabled=false;
  const rows=latest.rows||[];const candidates=rows.filter(r=>r.score_ms!=null&&r.success>0);
  const leader=latest.state==='complete'?candidates[0]:null;
  $('best-name').textContent=leader?leader.name:'—';
  $('best-detail').textContent=leader?`${protocolLabel(leader.protocol)} · ${leader.family} · índice ${number(leader.score_ms)} ms`:latest.state==='cancelled'?'Teste interrompido; resultado parcial':'Disponível após o teste completo';
  $('best-median').innerHTML=`${number(leader?.median_ms)}<em> ms</em>`;$('best-p95').innerHTML=`${number(leader?.p95_ms)}<em> ms</em>`;
  $('sample-count').textContent=number(latest.completed||0,0);$('server-count').textContent=rows.length;
  $('elapsed').textContent=latest.elapsed_seconds?`${number(latest.elapsed_seconds,0)} s de medição · ${latest.state==='cancelled'?'parcial':latest.state==='complete'?'concluído':'em andamento'}`:'Primeira passagem + repetições';
  $('progress-panel').classList.toggle('hidden',latest.state==='idle');$('progress-message').textContent=latest.message;
  $('progress-count').textContent=latest.total?`${latest.completed} / ${latest.total}`:'Sondagem inicial';
  $('progress').value=latest.total?100*latest.completed/latest.total:0;
  $('result-subtitle').textContent=running?'Resultados provisórios. Aguarde todas as passagens antes de comparar.':latest.state==='cancelled'?'Resultado parcial: amostras desiguais; não há recomendação de vencedor.':'Resultados da sua rede, no momento do teste.';
  $('export-json').disabled=latest.state==='idle';$('export-csv').disabled=!latest.completed;
  $('empty').classList.toggle('hidden',rows.length>0);
  let visible=rows.filter(r=>filter==='all'||r.protocol===filter);const max=Math.max(1,...rows.map(r=>r.score_ms||0));
  $('rows').innerHTML=visible.map(r=>{
    const best=r===leader;const unavailable=!r.available&&Object.keys(r.diagnostic_errors||{}).length>0;
    return `<tr data-row="${r.id}" class="${best?'leader':''}" tabindex="0" aria-label="Ver detalhes de ${escapeHTML(r.name)} ${protocolLabel(r.protocol)} ${r.family}"><td><div class="server-name"><div class="provider-icon">${escapeHTML(r.name[0])}</div><div><strong>${escapeHTML(r.name)}</strong>${best?'<span class="badge">MENOR ÍNDICE</span>':''}<small>${escapeHTML(r.address)}<span class="protocol">${protocolLabel(r.protocol)} · ${r.family}</span></small></div></div></td><td><div class="bar-cell"><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100,(r.score_ms||0)/max*100)}%"></div></div><b>${unavailable?'Indisponível':number(r.score_ms)}</b></div></td><td>${number(r.median_ms)} <span class="muted">ms</span></td><td>${number(r.p95_ms)} <span class="muted">ms</span></td><td class="${r.failure_pct>0?'bad':'good'}">${r.failure_pct==null?'—':number(r.failure_pct,1)+'%'}</td><td>${r.count||0}</td></tr>`;
  }).join('');
  $('rows').querySelectorAll('tr').forEach(el=>{el.onclick=()=>showDetail(el.dataset.row);el.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();showDetail(el.dataset.row);}};});
  if(rows.length&&!visible.length)$('rows').innerHTML='<tr><td colspan="6">Nenhum servidor deste protocolo foi incluído neste teste.</td></tr>';
  const unavailable=rows.filter(r=>!r.available&&Object.keys(r.diagnostic_errors||{}).length).length;
  $('report-note').textContent=[unavailable?`${unavailable} servidor(es) indisponível(is) na sondagem inicial; não participaram do ranking.`:'',latest.saved_to?`Relatório salvo: ${latest.saved_to}`:'',latest.save_error||'',latest.state==='complete'&&leader&&leader.count<100?'Amostra exploratória. Repita em horários diferentes antes de escolher um DNS.':''].filter(Boolean).join(' ');
  if(latest.state==='error')showError(latest.message);
}
function showDetail(id){
  const r=latest.rows.find(row=>row.id===id);if(!r)return;$('detail-title').textContent=r.name+' · '+protocolLabel(r.protocol);
  const stat=(label,value)=>`<div class="detail-stat"><span>${label}</span><strong>${number(value)} ms</strong></div>`;
  $('detail-content').innerHTML=`<p class="detail-info"><b>${escapeHTML(r.address)} · ${r.family}</b><br>${escapeHTML(r.policy)}</p><div class="detail-grid">${stat('Primeira passagem · média com penalidades',r.first.cost_ms)}${stat('Repetições · média com penalidades',r.repeat.cost_ms)}${stat('Sondagem inicial · mediana, fora do ranking',r.setup_ms)}${stat('P95 do tempo por lote paralelo',r.batch_p95_ms)}</div><p class="detail-info"><b>${r.success} de ${r.count} respostas válidas</b> · ${r.nodata} NODATA · ${r.tcp_fallbacks} fallback(s) TCP<br>Mínimo: ${number(r.min_ms)} ms · Máximo: ${number(r.max_ms)} ms<br>Desvio padrão: ${number(r.stddev_ms)} ms${r.http_versions?.length?'<br>HTTPS negociado: '+escapeHTML(r.http_versions.join(', ')):''}</p><p class="detail-info"><b>Falhas medidas:</b> ${escapeHTML(Object.entries(r.errors||{}).map(([k,v])=>`${k}: ${v}`).join(' · ')||'Nenhuma')}<br><b>Falhas na sondagem:</b> ${escapeHTML(Object.entries(r.diagnostic_errors||{}).map(([k,v])=>`${k}: ${v}`).join(' · ')||'Nenhuma')}</p><p class="small-note">NODATA é uma resposta válida sem o registro solicitado. Políticas de bloqueio e nomes desativados podem produzir falhas de resolução. Consulte o JSON para auditar cada resposta. O P95 do lote não é tempo de carregamento de página.</p>`;
  $('details').showModal();
}
$('close-details').onclick=()=>$('details').close();
$('show-notices').onclick=async()=>{
  $('notices').showModal();
  if($('notices-content').dataset.loaded)return;
  try{
    const response=await fetch('/notices.txt');
    if(!response.ok)throw Error('Não foi possível abrir os avisos.');
    $('notices-content').textContent=await response.text();
    $('notices-content').dataset.loaded='true';
  }catch(error){$('notices-content').textContent=error.message;}
};
$('close-notices').onclick=()=>$('notices').close();
$('details').onclick=event=>{if(event.target===$('details')){const rect=$('details').getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)$('details').close();}};
$('result-filter').querySelectorAll('button').forEach(button=>button.onclick=()=>{filter=button.dataset.filter;$('result-filter').querySelectorAll('button').forEach(b=>b.classList.toggle('selected',b===button));render();});
for(const format of ['json','csv'])$('export-'+format).onclick=async()=>{
  try{const response=await fetch('/api/export.'+format,{headers:{'X-Nodavira-Token':token}});if(!response.ok)throw Error('Falha ao exportar.');const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download='nodavira-resultados.'+format;link.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}catch(error){showError(error.message);}
};
async function poll(){try{latest=await api('status');render();}catch(error){showError('Sem conexão com o aplicativo. Abra Nodavira novamente para iniciar uma nova sessão.');clearInterval(pollTimer);setBusy(false);$('start').disabled=true;}}
let pollTimer;
(async()=>{try{const data=await api('config');catalog=data.resolvers;defaults=data.domains;$('domains').value=defaults.join('\n');selectDefault();loaded=true;await poll();pollTimer=setInterval(poll,1000);}catch(error){showError(error.message);$('start').disabled=true;}})();
