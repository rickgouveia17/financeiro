from flask import Flask, render_template, request, jsonify, send_file, session, redirect
import json
import os
import io
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

app = Flask(__name__)
app.secret_key = 'farol-secret-2026'

# ── Usuários ───────────────────────────────────────
USERS = {
    "financeiro1": {"senha": "fin1@2026", "nome": "Financeiro 1"},
    "financeiro2": {"senha": "fin2@2026", "nome": "Financeiro 2"},
}

def data_file(user):
    return f'data_{user}.json'

def load_data(user):
    f = data_file(user)
    if not os.path.exists(f):
        notas = []
        save_data(user, notas)
        return notas
    with open(f, 'r', encoding='utf-8') as fp:
        return json.load(fp)

def save_data(user, notas):
    with open(data_file(user), 'w', encoding='utf-8') as fp:
        json.dump(notas, fp, ensure_ascii=False, indent=2)

def next_id(notas):
    return max((n['id'] for n in notas), default=0) + 1

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ── Auth ───────────────────────────────────────────
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    body = request.get_json()
    user = body.get('usuario', '').strip()
    senha = body.get('senha', '').strip()
    if user in USERS and USERS[user]['senha'] == senha:
        session['user'] = user
        session['nome'] = USERS[user]['nome']
        return jsonify({"ok": True, "nome": USERS[user]['nome']})
    return jsonify({"erro": "Usuário ou senha incorretos"}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ── App ────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    return render_template('index.html', nome=session.get('nome'))

# ── API ────────────────────────────────────────────
@app.route('/api/notas', methods=['GET'])
@login_required
def get_notas():
    return jsonify(load_data(session['user']))

@app.route('/api/notas', methods=['POST'])
@login_required
def create_nota():
    notas = load_data(session['user'])
    body = request.get_json()
    nova = {
        "id": next_id(notas),
        "numero": body.get('numero', ''),
        "fornecedor": body.get('fornecedor', ''),
        "valor": float(body.get('valor', 0)),
        "status": body.get('status', 'processando'),
        "observacao": body.get('observacao', ''),
        "dias": int(body.get('dias', 0)),
    }
    notas.append(nova)
    save_data(session['user'], notas)
    return jsonify(nova), 201

@app.route('/api/notas/<int:nid>/status', methods=['PATCH'])
@login_required
def update_status(nid):
    notas = load_data(session['user'])
    body = request.get_json()
    for n in notas:
        if n['id'] == nid:
            n['status'] = body.get('status', n['status'])
            save_data(session['user'], notas)
            return jsonify(n)
    return jsonify({"erro": "não encontrado"}), 404

@app.route('/api/notas/<int:nid>', methods=['DELETE'])
@login_required
def delete_nota(nid):
    notas = load_data(session['user'])
    notas = [n for n in notas if n['id'] != nid]
    save_data(session['user'], notas)
    return jsonify({"ok": True})

@app.route('/api/exportar', methods=['GET'])
@login_required
def exportar_excel():
    notas = load_data(session['user'])
    wb = Workbook()
    ws = wb.active
    ws.title = "Notas Fiscais"

    fill_verde    = PatternFill("solid", fgColor="C6EFCE")
    fill_laranja  = PatternFill("solid", fgColor="FFEB9C")
    fill_vermelho = PatternFill("solid", fgColor="FFC7CE")
    fill_header   = PatternFill("solid", fgColor="1B2232")
    font_header   = Font(bold=True, color="FFFFFF", size=11)
    font_normal   = Font(size=10)
    border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )

    headers    = ["NF", "Fornecedor", "Valor (R$)", "Status", "Observação", "Dias"]
    col_widths = [10, 28, 16, 16, 28, 8]

    for i, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=i, value=h)
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
        ws.column_dimensions[cell.column_letter].width = w
    ws.row_dimensions[1].height = 22

    status_label = {
        'processando': 'Em Processamento',
        'medicao': 'Em Medição',
        'pendencia': 'Com Pendência',
        'concluida': 'Concluída'
    }

    for row_idx, n in enumerate(notas, 2):
        valores = [f"#{n['numero']}", n['fornecedor'], n['valor'],
                   status_label.get(n['status'], n['status']),
                   n.get('observacao', ''), n.get('dias', 0)]
        fill = fill_verde if n['status'] == 'concluida' else \
               fill_vermelho if n['status'] == 'pendencia' else fill_laranja
        for col_idx, val in enumerate(valores, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.fill = fill
            cell.font = font_normal
            cell.border = border
            cell.alignment = Alignment(vertical='center')

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'notas_{session["user"]}.xlsx')

@app.route('/api/importar', methods=['POST'])
@login_required
def importar_excel():
    if 'arquivo' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    arquivo = request.files['arquivo']
    if not arquivo.filename.endswith(('.xlsx', '.xls')):
        return jsonify({"erro": "Formato inválido. Use .xlsx ou .xls"}), 400
    try:
        wb = load_workbook(io.BytesIO(arquivo.read()), data_only=True)
        ws = wb.active
        notas = load_data(session['user'])
        idx = {n['numero']: n for n in notas}
        status_map = {
            'em processamento': 'processando', 'processando': 'processando',
            'em medição': 'medicao', 'medição': 'medicao', 'medicao': 'medicao',
            'com pendência': 'pendencia', 'pendência': 'pendencia', 'pendencia': 'pendencia',
            'concluída': 'concluida', 'concluida': 'concluida', 'lançado': 'concluida',
        }
        importadas = atualizadas = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row): continue
            try:
                numero     = str(row[0]).strip().replace('#','') if row[0] else None
                fornecedor = str(row[1]).strip() if row[1] else ''
                valor      = float(str(row[2]).replace('R$','').replace('.','').replace(',','.').strip()) if row[2] else 0
                status_raw = str(row[3]).strip().lower() if row[3] else 'processando'
                observacao = str(row[4]).strip() if row[4] else ''
                dias       = int(row[5]) if row[5] else 0
            except Exception: continue
            if not numero or numero == 'None': continue
            status = status_map.get(status_raw, 'processando')
            if numero in idx:
                n = idx[numero]
                n.update(fornecedor=fornecedor, valor=valor, status=status, observacao=observacao, dias=dias)
                atualizadas += 1
            else:
                nova = {"id": next_id(notas), "numero": numero, "fornecedor": fornecedor,
                        "valor": valor, "status": status, "observacao": observacao, "dias": dias}
                notas.append(nova)
                idx[numero] = nova
                importadas += 1
        save_data(session['user'], notas)
        return jsonify({"ok": True, "importadas": importadas, "atualizadas": atualizadas, "total": len(notas)})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
