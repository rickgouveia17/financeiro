const API = '/api/notas';
let draggedId = null;
let todasNotas = [];

function showPage(name, el) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`page-${name}`).classList.add('active');
  if (el) el.classList.add('active');
  const titles = { dashboard: 'Dashboard', varal: 'Notas Penduradas', relatorios: 'Relatórios' };
  document.getElementById('page-title').textContent = titles[name] || '';
  if (name === 'relatorios') renderTabela();
  return false;
}

async function carregarNotas() {
  const res = await fetch(API);
  todasNotas = await res.json();
  ['processando','medicao','pendencia','concluida'].forEach(s => {
    document.getElementById(`cards-${s}`).innerHTML = '';
  });
  todasNotas.forEach(renderCard);
  atualizarDashboard(todasNotas);
}

function fmt(v) {
  return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
}

function labelStatus(s) {
  return { processando: 'Processando', medicao: 'Em Medição', pendencia: 'Pendência', concluida: 'Concluída' }[s] || s;
}

function renderCard(nota) {
  const container = document.getElementById(`cards-${nota.status}`);
  if (!container) return;

  const diasTxt = nota.dias < 1 ? '<1 dia' : `${nota.dias} dia${nota.dias > 1 ? 's' : ''}`;
  const diasHtml = nota.dias > 2
    ? `<span class="dias-alerta">${diasTxt} ⚠</span>`
    : `<span>${diasTxt}</span>`;

  const div = document.createElement('div');
  div.className = 'card' + (nota.status === 'pendencia' ? ' alerta-pendencia' : '');
  div.draggable = true;
  div.dataset.id = nota.id;
  div.innerHTML = `
    <div class="card-title">NF #${nota.numero} · ${nota.fornecedor}</div>
    <div class="card-valor">R$ ${fmt(nota.valor)}</div>
    <div class="card-footer">
      <span>${nota.observacao || ''}</span>
      ${diasHtml}
    </div>
  `;
  div.addEventListener('dragstart', () => { draggedId = nota.id; div.classList.add('dragging'); });
  div.addEventListener('dragend',   () => { div.classList.remove('dragging'); draggedId = null; });
  container.appendChild(div);
}

function atualizarDashboard(notas) {
  const pend = notas.filter(n => n.status === 'pendencia').length;

  document.getElementById('d-total').textContent     = notas.length;
  document.getElementById('d-medicao').textContent   = notas.filter(n => n.status === 'processando' || n.status === 'medicao').length;
  document.getElementById('d-pendencia').textContent = pend;
  document.getElementById('d-concluida').textContent = notas.filter(n => n.status === 'concluida').length;

  const badge = document.getElementById('badge-pendencia');
  badge.textContent = pend;
  badge.style.display = pend > 0 ? 'inline' : 'none';

  const alertas = notas.filter(n => n.status === 'pendencia' || n.dias > 2);
  document.getElementById('tabela-alertas').innerHTML = alertas.length === 0
    ? '<tr><td colspan="5" style="text-align:center;color:#aaa;padding:16px">Nenhuma pendência 🎉</td></tr>'
    : alertas.map(n => `<tr>
        <td>#${n.numero}</td>
        <td>${n.fornecedor}</td>
        <td>R$ ${fmt(n.valor)}</td>
        <td><span class="badge ${n.status}">${labelStatus(n.status)}</span></td>
        <td class="${n.dias > 2 ? 'dias-alerta' : ''}">${n.dias < 1 ? '<1' : n.dias}d</td>
      </tr>`).join('');

  const concluidas = notas.filter(n => n.status === 'concluida').slice(0, 5);
  document.getElementById('tabela-concluidas').innerHTML = concluidas.length === 0
    ? '<tr><td colspan="4" style="text-align:center;color:#aaa;padding:16px">Nenhuma concluída</td></tr>'
    : concluidas.map(n => `<tr>
        <td>#${n.numero}</td>
        <td>${n.fornecedor}</td>
        <td>R$ ${fmt(n.valor)}</td>
        <td>${n.observacao || '-'}</td>
      </tr>`).join('');
}

function renderTabela() {
  document.getElementById('tabela-relatorio').innerHTML = todasNotas.length === 0
    ? '<tr><td colspan="7" style="text-align:center;color:#aaa;padding:16px">Nenhuma nota</td></tr>'
    : todasNotas.map(n => `<tr>
        <td>#${n.numero}</td>
        <td>${n.fornecedor}</td>
        <td>R$ ${fmt(n.valor)}</td>
        <td><span class="badge ${n.status}">${labelStatus(n.status)}</span></td>
        <td>${n.observacao || '-'}</td>
        <td class="${n.dias > 2 ? 'dias-alerta' : ''}">${n.dias < 1 ? '<1' : n.dias}d</td>
        <td><button class="btn-del" onclick="deletarNota(${n.id})">Excluir</button></td>
      </tr>`).join('');
}

// Drag & drop
document.querySelectorAll('.cards').forEach(col => {
  col.addEventListener('dragover', e => e.preventDefault());
  col.addEventListener('drop', async () => {
    const status = col.id.replace('cards-', '');
    if (draggedId) await moverNota(draggedId, status);
  });
});

document.querySelectorAll('.drop-zone').forEach(zone => {
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('over'));
  zone.addEventListener('drop', async () => {
    zone.classList.remove('over');
    if (draggedId) await moverNota(draggedId, zone.dataset.target);
  });
});

async function moverNota(id, status) {
  await fetch(`${API}/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  });
  carregarNotas();
}

async function deletarNota(id) {
  if (!confirm('Excluir esta nota?')) return;
  await fetch(`${API}/${id}`, { method: 'DELETE' });
  await carregarNotas();
  renderTabela();
}

function abrirModal() {
  document.getElementById('modal').classList.remove('hidden');
}
function fecharModal() {
  document.getElementById('modal').classList.add('hidden');
  ['m-numero','m-fornecedor','m-valor','m-obs'].forEach(id => document.getElementById(id).value = '');
}
async function salvarNota() {
  const numero     = document.getElementById('m-numero').value.trim();
  const fornecedor = document.getElementById('m-fornecedor').value.trim();
  const valor      = parseFloat(document.getElementById('m-valor').value);
  const observacao = document.getElementById('m-obs').value.trim();
  const status     = document.getElementById('m-status').value;

  if (!numero || !fornecedor || isNaN(valor)) { alert('Preencha número, fornecedor e valor.'); return; }

  await fetch(API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ numero, fornecedor, valor, observacao, status, dias: 0 })
  });
  fecharModal();
  carregarNotas();
}

function exportarExcel() {
  window.location.href = '/api/exportar';
}

function uploadPlanilha(input) {
  const file = input.files[0];
  if (!file) return;
  // por enquanto só avisa — integração real quando você trouxer o PDF
  alert(`Planilha "${file.name}" selecionada.\nA integração será configurada em breve.`);
  input.value = '';
}

document.getElementById('modal').addEventListener('click', function(e) {
  if (e.target === this) fecharModal();
});

carregarNotas();
