"""Lista de Compras (alimentação) — quadro partilhado de casa.

App web (Flask) em português. Dois níveis de separadores: Categoria → Subcategoria
(tab dentro de tab). Cada produto é um item permanente do catálogo com uma
"quantidade a comprar" (0 = não está na lista). Em vez de reescrever sempre,
ajusta-se a quantidade; depois das compras carrega-se em "Limpar lista".

Separadores arrastáveis (ordem por dispositivo). Estado guardado no servidor
(volume /data). Corre no porto 8003.
"""

import json
import os
import tempfile
import unicodedata
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).with_name("data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
ITEMS_FILE = DATA_DIR / "items.json"

CATS = [
    {"key": "fl", "label": "Frutas & Legumes", "icone": "🥦", "subs": [
        {"key": "frutas", "label": "Frutas"},
        {"key": "legumes", "label": "Legumes"},
        {"key": "frescos", "label": "Ervas & Temperos"}]},
    {"key": "cpo", "label": "Carne, Peixe & Ovos", "icone": "🥩", "subs": [
        {"key": "carne", "label": "Carne"},
        {"key": "peixe", "label": "Peixe"},
        {"key": "mariscos", "label": "Mariscos"},
        {"key": "ovos", "label": "Ovos"}]},
    {"key": "lat", "label": "Laticínios & Frios", "icone": "🧀", "subs": [
        {"key": "leite", "label": "Leite & Iogurtes"},
        {"key": "queijos", "label": "Queijos"},
        {"key": "manteiga", "label": "Manteiga & Natas"},
        {"key": "charcutaria", "label": "Charcutaria"}]},
    {"key": "enl", "label": "Enlatados & Conservas", "icone": "🥫", "subs": [
        {"key": "vegetais", "label": "Vegetais"},
        {"key": "frutas", "label": "Frutas"},
        {"key": "peixe", "label": "Peixe"},
        {"key": "carne", "label": "Carne"},
        {"key": "leguminosas", "label": "Leguminosas"}]},
    {"key": "mer", "label": "Mercearia", "icone": "🧂", "subs": [
        {"key": "massarroz", "label": "Massa & Arroz"},
        {"key": "molhos", "label": "Molhos & Temperos"},
        {"key": "oleos", "label": "Óleos & Vinagres"},
        {"key": "pa", "label": "Pequeno-almoço"},
        {"key": "snacks", "label": "Snacks & Doces"}]},
    {"key": "pad", "label": "Padaria", "icone": "🥖", "subs": [
        {"key": "pao", "label": "Pão"},
        {"key": "bolachas", "label": "Bolachas & Cereais"},
        {"key": "pastelaria", "label": "Pastelaria"}]},
    {"key": "cong", "label": "Congelados", "icone": "🧊", "subs": [
        {"key": "legumes", "label": "Legumes"},
        {"key": "peixe", "label": "Peixe"},
        {"key": "refeicoes", "label": "Refeições"},
        {"key": "gelados", "label": "Gelados"}]},
    {"key": "beb", "label": "Bebidas", "icone": "🧃", "subs": [
        {"key": "aguas", "label": "Águas"},
        {"key": "sumos", "label": "Sumos & Refrigerantes"},
        {"key": "cafe", "label": "Café & Chá"},
        {"key": "alcool", "label": "Álcool"}]},
]
VALID = {(c["key"], s["key"]) for c in CATS for s in c["subs"]}

# Catálogo inicial (cat, sub, nome) — fica permanente; ajusta-se só a quantidade.
SEED = [
    ("fl", "frutas", "Maçã"), ("fl", "frutas", "Banana"), ("fl", "frutas", "Laranja"),
    ("fl", "frutas", "Pera"), ("fl", "frutas", "Morangos"), ("fl", "frutas", "Uvas"),
    ("fl", "frutas", "Limão"), ("fl", "frutas", "Abacate"), ("fl", "frutas", "Melão"),
    ("fl", "legumes", "Batatas"), ("fl", "legumes", "Cenoura"), ("fl", "legumes", "Courgette"),
    ("fl", "legumes", "Cebolas"), ("fl", "legumes", "Alho"), ("fl", "legumes", "Alface"),
    ("fl", "legumes", "Tomate"), ("fl", "legumes", "Pepino"), ("fl", "legumes", "Brócolos"),
    ("fl", "legumes", "Espinafres"), ("fl", "legumes", "Pimentos"), ("fl", "legumes", "Cogumelos"),
    ("fl", "frescos", "Salsa"), ("fl", "frescos", "Coentros"), ("fl", "frescos", "Manjericão"),
    ("fl", "frescos", "Gengibre"),
    ("cpo", "carne", "Peito de frango"), ("cpo", "carne", "Coxas de frango"),
    ("cpo", "carne", "Carne picada"), ("cpo", "carne", "Bife de vaca"),
    ("cpo", "carne", "Costeletas de porco"), ("cpo", "carne", "Coelho"), ("cpo", "carne", "Peru"),
    ("cpo", "peixe", "Salmão"), ("cpo", "peixe", "Bacalhau"), ("cpo", "peixe", "Dourada"),
    ("cpo", "peixe", "Pescada"), ("cpo", "peixe", "Sardinha"),
    ("cpo", "mariscos", "Camarão"), ("cpo", "mariscos", "Amêijoas"),
    ("cpo", "mariscos", "Mexilhão"), ("cpo", "mariscos", "Lulas"), ("cpo", "mariscos", "Polvo"),
    ("cpo", "ovos", "Ovos (dúzia)"),
    ("lat", "leite", "Leite"), ("lat", "leite", "Iogurtes de beber da Mariana"),
    ("lat", "leite", "Iogurtes de comer"), ("lat", "leite", "Iogurtes gregos"),
    ("lat", "queijos", "Queijo fatiado"), ("lat", "queijos", "Queijo flamengo"),
    ("lat", "queijos", "Mozzarella"), ("lat", "queijos", "Queijo ralado"),
    ("lat", "manteiga", "Manteiga"), ("lat", "manteiga", "Natas"), ("lat", "manteiga", "Margarina"),
    ("lat", "charcutaria", "Fiambre"), ("lat", "charcutaria", "Chouriço"),
    ("lat", "charcutaria", "Presunto"), ("lat", "charcutaria", "Bacon"),
    ("enl", "vegetais", "Milho"), ("enl", "vegetais", "Ervilhas"),
    ("enl", "vegetais", "Tomate pelado"), ("enl", "vegetais", "Feijão verde"),
    ("enl", "frutas", "Ananás em calda"), ("enl", "frutas", "Pêssego em calda"),
    ("enl", "peixe", "Atum"), ("enl", "peixe", "Sardinhas"), ("enl", "peixe", "Cavala"),
    ("enl", "carne", "Paté"), ("enl", "carne", "Salsichas"),
    ("enl", "leguminosas", "Grão-de-bico"), ("enl", "leguminosas", "Feijão encarnado"),
    ("enl", "leguminosas", "Feijão branco"), ("enl", "leguminosas", "Lentilhas"),
    ("mer", "massarroz", "Esparguete"), ("mer", "massarroz", "Massa cotovelos"),
    ("mer", "massarroz", "Arroz"), ("mer", "massarroz", "Noodles"),
    ("mer", "molhos", "Sal"), ("mer", "molhos", "Pimenta"), ("mer", "molhos", "Ketchup"),
    ("mer", "molhos", "Maionese"), ("mer", "molhos", "Mostarda"), ("mer", "molhos", "Molho de soja"),
    ("mer", "molhos", "Vinagre de arroz"), ("mer", "molhos", "Caldos"), ("mer", "molhos", "Orégãos"),
    ("mer", "oleos", "Azeite"), ("mer", "oleos", "Óleo"), ("mer", "oleos", "Vinagre"),
    ("mer", "pa", "Cereais"), ("mer", "pa", "Flocos de aveia"), ("mer", "pa", "Compota"),
    ("mer", "pa", "Mel"), ("mer", "pa", "Manteiga de amendoim"),
    ("mer", "snacks", "Batatas fritas"), ("mer", "snacks", "Bolachas"),
    ("mer", "snacks", "Chocolate"), ("mer", "snacks", "Frutos secos"),
    ("pad", "pao", "Pão de forma"), ("pad", "pao", "Pão fresco"), ("pad", "pao", "Tostas"),
    ("pad", "pao", "Croutons"), ("pad", "pao", "Wraps"),
    ("pad", "bolachas", "Bolachas Maria"), ("pad", "bolachas", "Bolachas água e sal"),
    ("pad", "pastelaria", "Croissants"), ("pad", "pastelaria", "Bolos"),
    ("cong", "legumes", "Ervilhas congeladas"), ("cong", "legumes", "Brócolos congelados"),
    ("cong", "legumes", "Legumes salteados"),
    ("cong", "peixe", "Filetes"), ("cong", "peixe", "Douradinhos"), ("cong", "peixe", "Camarão congelado"),
    ("cong", "refeicoes", "Pizza"), ("cong", "refeicoes", "Lasanha"), ("cong", "refeicoes", "Batata frita congelada"),
    ("cong", "gelados", "Gelado"), ("cong", "gelados", "Gelados individuais"),
    ("beb", "aguas", "Água"), ("beb", "aguas", "Água com gás"),
    ("beb", "sumos", "Sumo de laranja"), ("beb", "sumos", "Refrigerantes"), ("beb", "sumos", "Néctar"),
    ("beb", "cafe", "Café"), ("beb", "cafe", "Cápsulas"), ("beb", "cafe", "Chá"),
    ("beb", "alcool", "Cerveja"), ("beb", "alcool", "Vinho"),
]


def _fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower())
                   if unicodedata.category(c) != "Mn")


def read_items():
    try:
        data = json.loads(ITEMS_FILE.read_text())
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    items = [{"id": uuid.uuid4().hex[:10], "nome": n, "cat": c, "sub": s, "qtd": 0}
             for c, s, n in SEED]
    write_items(items)
    return items


def write_items(items):
    with tempfile.NamedTemporaryFile("w", dir=ITEMS_FILE.parent, delete=False) as tmp:
        json.dump(items, tmp, ensure_ascii=False, indent=2)
        tmp_name = tmp.name
    os.replace(tmp_name, ITEMS_FILE)


@app.route("/api/items")
def api_items():
    return jsonify(read_items())


@app.route("/api/items/add", methods=["POST"])
def api_add():
    d = request.get_json(silent=True) or request.form
    nome = (d.get("nome") or "").strip()
    cat, sub = (d.get("cat") or "").strip(), (d.get("sub") or "").strip()
    if not nome or (cat, sub) not in VALID:
        return jsonify({"ok": False, "erro": "dados inválidos"}), 400
    items = read_items()
    items.append({"id": uuid.uuid4().hex[:10], "nome": nome, "cat": cat, "sub": sub, "qtd": 1})
    write_items(items)
    return jsonify(items)


@app.route("/api/items/qty", methods=["POST"])
def api_qty():
    d = request.get_json(silent=True) or request.form
    item_id = (d.get("id") or "").strip()
    try:
        delta = int(d.get("delta", 0))
    except (TypeError, ValueError):
        delta = 0
    items = read_items()
    for it in items:
        if it.get("id") == item_id:
            it["qtd"] = max(0, int(it.get("qtd", 0)) + delta)
            break
    write_items(items)
    return jsonify(items)


@app.route("/api/items/delete", methods=["POST"])
def api_delete():
    d = request.get_json(silent=True) or request.form
    item_id = (d.get("id") or "").strip()
    write_items([it for it in read_items() if it.get("id") != item_id])
    return jsonify(read_items())


@app.route("/api/items/clear", methods=["POST"])
def api_clear():
    items = read_items()
    for it in items:
        it["qtd"] = 0
    write_items(items)
    return jsonify(items)


@app.route("/healthz")
def healthz():
    return {"ok": True}


PAGE = r"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Compras</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23e8743b'/%3E%3Cpath d='M8 9h3l2 11h9l2-8H12' fill='none' stroke='%23fff' stroke-width='2.2' stroke-linejoin='round' stroke-linecap='round'/%3E%3Ccircle cx='14' cy='25' r='1.6' fill='%23fff'/%3E%3Ccircle cx='22' cy='25' r='1.6' fill='%23fff'/%3E%3C/svg%3E">
  <style>
    :root {
      --bg:#eef1f6; --card:#fff; --text:#16202e; --muted:#67748a; --border:#e2e7ef;
      --shadow:0 1px 3px rgba(20,30,50,.08),0 1px 2px rgba(20,30,50,.04);
      --accent:#e8743b; --accent-bg:#e8743b18; --green:#1f9d57;
    }
    @media (prefers-color-scheme: dark) {
      :root { --bg:#0e131b; --card:#19212c; --text:#e8eef6; --muted:#90a0b6; --border:#28323f;
        --shadow:0 1px 2px rgba(0,0,0,.4); --accent:#ff8c52; --accent-bg:#ff8c5222; --green:#34c884; }
    }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--text); line-height:1.5;
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
    .wrap { max-width:820px; margin:0 auto; padding:1rem 1rem 3rem; }
    h1 { margin:.1rem 0 .6rem; font-size:1.4rem; }
    .tabs { display:flex; gap:.4rem; flex-wrap:wrap; margin-bottom:.5rem; }
    .tabs.sub { margin-bottom:.9rem; }
    .tab { font-weight:700; padding:.45rem .75rem; border-radius:999px; cursor:grab;
      border:1px solid var(--border); background:var(--card); color:var(--muted); display:flex;
      gap:.3rem; align-items:center; touch-action:none; user-select:none; -webkit-user-select:none; }
    .tabs.cat .tab { font-size:.9rem; }
    .tabs.sub .tab { font-size:.82rem; padding:.35rem .65rem; }
    .tab.on { background:var(--accent); color:#fff; border-color:var(--accent); }
    .tab.lista.on { background:var(--green); border-color:var(--green); }
    .tab.dragging { opacity:.55; cursor:grabbing; }
    .grip { opacity:.4; margin-right:.1rem; font-size:.95em; letter-spacing:-2px; }
    .tab.on .grip { opacity:.75; }
    .badge { font-size:.72rem; font-weight:800; min-width:18px; text-align:center; padding:0 .3rem;
      border-radius:999px; background:var(--accent); color:#fff; }
    .tab.on .badge { background:#fff; color:var(--accent); }
    .search { width:100%; padding:.6rem .85rem; font-size:1rem; border-radius:12px;
      border:1px solid var(--border); background:var(--card); color:var(--text); box-shadow:var(--shadow);
      margin-bottom:.8rem; }
    .addbar { display:flex; gap:.5rem; margin-bottom:1rem; }
    .addbar input { flex:1; padding:.6rem .8rem; font-size:1rem; border-radius:10px;
      border:1px solid var(--border); background:var(--card); color:var(--text); }
    .btn { padding:.6rem .9rem; border-radius:10px; border:1px solid var(--accent); background:var(--accent);
      color:#fff; font-weight:700; cursor:pointer; font-size:.92rem; white-space:nowrap; }
    .btn.ghost { background:transparent; color:var(--accent); margin-bottom:.7rem; }
    .item { display:flex; align-items:center; gap:.7rem; background:var(--card); border:1px solid var(--border);
      border-radius:12px; box-shadow:var(--shadow); padding:.55rem .8rem; margin-bottom:.45rem; }
    .item.on { border-color:var(--accent); background:var(--accent-bg); }
    .item .info { flex:1; min-width:0; }
    .item .nome { font-weight:700; }
    .item .meta { font-size:.76rem; color:var(--muted); }
    .stepper { display:flex; align-items:center; gap:.3rem; }
    .sb { width:30px; height:30px; border-radius:8px; border:1px solid var(--border); background:var(--card);
      color:var(--text); font-size:1.15rem; line-height:1; cursor:pointer; font-weight:700; }
    .sb:hover { border-color:var(--accent); color:var(--accent); }
    .num { min-width:24px; text-align:center; font-weight:800; }
    .num.pos { color:var(--accent); }
    .act.done { border:1px solid var(--green); color:#fff; background:var(--green); border-radius:9px;
      padding:.45rem .65rem; cursor:pointer; font-weight:800; }
    .x { border:none; background:none; color:var(--muted); cursor:pointer; font-size:1.1rem; padding:.2rem .3rem; }
    .x:hover { color:#d24b3a; }
    .grouptitle { font-size:.82rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em;
      margin:1rem 0 .5rem; font-weight:700; }
    .empty { color:var(--muted); padding:1.2rem; text-align:center; }
    .hide { display:none; }
    footer { margin-top:2rem; text-align:center; color:var(--muted); font-size:.8rem; }
  </style>
</head>
<body>
<div class="wrap">
  <h1>🛒 Lista de Compras</h1>

  <div class="tabs cat" id="cattabs">
    {% for c in cats %}
    <div class="tab{% if loop.first %} on{% endif %}" data-cat="{{ c.key }}">{{ c.icone }} {{ c.label }}
      <span class="badge hide" id="bc-{{ c.key }}"></span></div>
    {% endfor %}
    <div class="tab lista" data-cat="lista">🛒 Lista <span class="badge hide" id="b-lista"></span></div>
  </div>

  <div id="subwrap">
    {% for c in cats %}
    <div class="tabs sub subrow{% if not loop.first %} hide{% endif %}" id="sub-{{ c.key }}">
      {% for s in c.subs %}
      <div class="tab{% if loop.first %} on{% endif %}" data-sub="{{ s.key }}">{{ s.label }}
        <span class="badge hide" id="bs-{{ c.key }}-{{ s.key }}"></span></div>
      {% endfor %}
    </div>
    {% endfor %}
  </div>

  <input id="q" class="search" type="search" autocomplete="off" placeholder="🔎 Pesquisar produto…">

  <div class="addbar" id="addbar">
    <input id="novo" placeholder="Adicionar produto a esta secção…" autocomplete="off">
    <button class="btn" id="add">＋ Adicionar</button>
  </div>

  <div id="list"></div>

  <footer>Ajusta a quantidade a comprar com −/＋. Tudo o que tem quantidade vai para a tab <b>Lista</b>.<br>
    Depois das compras, usa <b>Limpar lista</b>. Arrasta as tabs (⠿) para reordenar. Sincroniza sozinho.</footer>
</div>

<script>
  const $ = id => document.getElementById(id);
  const fold = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const CATS = {{ cats_json|safe }};
  const CATLABEL = Object.fromEntries(CATS.map(c => [c.key, c.icone + ' ' + c.label]));
  const SUBLABEL = {};
  CATS.forEach(c => c.subs.forEach(s => SUBLABEL[c.key + '|' + s.key] = s.label));
  let items = [], aCat = CATS[0].key, aSub = CATS[0].subs[0].key;

  async function api(path, body) {
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}) });
    items = await r.json(); render();
  }
  const load = () => fetch('/api/items').then(r => r.json()).then(d => { items = d; render(); });

  function showCat(c) {
    aCat = c;
    document.querySelectorAll('#cattabs [data-cat]').forEach(t => t.classList.toggle('on', t.dataset.cat === c));
    document.querySelectorAll('.subrow').forEach(r => r.classList.toggle('hide', r.id !== 'sub-' + c || c === 'lista'));
    $('subwrap').classList.toggle('hide', c === 'lista');
    $('addbar').classList.toggle('hide', c === 'lista');
    if (c !== 'lista') {
      const subs = document.querySelectorAll('#sub-' + c + ' [data-sub]');
      if (subs.length) aSub = subs[0].dataset.sub;
    }
    render();
  }
  function showSub(s) { aSub = s; render(); }

  function badge(id, n) { const b = $(id); if (b) { b.textContent = n; b.classList.toggle('hide', !n); } }

  function row(it) {
    const on = it.qtd > 0;
    return `<div class="item ${on ? 'on' : ''}">
      <div class="info"><div class="nome">${it.nome}</div></div>
      <div class="stepper"><button class="sb" data-q="${it.id}|-1">−</button>
        <span class="num ${on ? 'pos' : ''}">${it.qtd}</span>
        <button class="sb" data-q="${it.id}|1">+</button></div>
      <button class="x" data-del="${it.id}" title="remover">✕</button></div>`;
  }
  function rowLista(it) {
    return `<div class="item on">
      <div class="info"><div class="nome">${it.nome}</div><div class="meta">${SUBLABEL[it.cat + '|' + it.sub] || ''}</div></div>
      <div class="stepper"><button class="sb" data-q="${it.id}|-1">−</button>
        <span class="num pos">${it.qtd}</span>
        <button class="sb" data-q="${it.id}|1">+</button></div>
      <button class="act done" data-buy="${it.id}|${it.qtd}" title="comprado">✓</button></div>`;
  }
  function render() {
    const buy = items.filter(i => i.qtd > 0);
    badge('b-lista', buy.length);
    CATS.forEach(c => {
      badge('bc-' + c.key, buy.filter(i => i.cat === c.key).length);
      c.subs.forEach(s => badge('bs-' + c.key + '-' + s.key, buy.filter(i => i.cat === c.key && i.sub === s.key).length));
    });
    if (aCat !== 'lista')
      document.querySelectorAll('#sub-' + aCat + ' [data-sub]').forEach(t => t.classList.toggle('on', t.dataset.sub === aSub));

    const term = fold($('q').value.trim());
    const box = $('list');
    if (aCat === 'lista') {
      if (!buy.length) { box.innerHTML = '<div class="empty">🛒 Lista vazia. Marca o que precisas nas categorias.</div>'; return; }
      box.innerHTML = '<button class="btn ghost" id="clearbtn">🧹 Limpar lista (após compras)</button>' +
        CATS.map(c => {
          const sub = buy.filter(i => i.cat === c.key && (!term || fold(i.nome).includes(term)));
          return sub.length ? `<div class="grouptitle">${CATLABEL[c.key]}</div>` + sub.map(rowLista).join('') : '';
        }).join('');
      const cb = $('clearbtn');
      if (cb) cb.onclick = () => { if (confirm('Limpar toda a lista de compras?')) api('/api/items/clear'); };
    } else {
      let list = items.filter(i => i.cat === aCat && i.sub === aSub && (!term || fold(i.nome).includes(term)));
      list.sort((a, b) => ((b.qtd > 0) - (a.qtd > 0)) || a.nome.localeCompare(b.nome, 'pt'));
      box.innerHTML = list.length ? list.map(row).join('') : '<div class="empty">Sem itens aqui. Adiciona acima 👆</div>';
    }
    box.querySelectorAll('[data-q]').forEach(b => b.onclick = () => {
      const [id, delta] = b.dataset.q.split('|'); api('/api/items/qty', { id, delta: Number(delta) });
    });
    box.querySelectorAll('[data-buy]').forEach(b => b.onclick = () => {
      const [id, q] = b.dataset.buy.split('|'); api('/api/items/qty', { id, delta: -Number(q) });
    });
    box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => api('/api/items/delete', { id: b.dataset.del }));
  }

  document.querySelectorAll('#cattabs [data-cat]').forEach(t => t.addEventListener('click', () => showCat(t.dataset.cat)));
  document.querySelectorAll('.subrow [data-sub]').forEach(t => t.addEventListener('click', () => showSub(t.dataset.sub)));
  $('q').addEventListener('input', render);
  function addNovo() {
    const nome = $('novo').value.trim(); if (!nome || aCat === 'lista') return;
    $('novo').value = ''; api('/api/items/add', { nome, cat: aCat, sub: aSub });
  }
  $('add').addEventListener('click', addNovo);
  $('novo').addEventListener('keydown', e => { if (e.key === 'Enter') addNovo(); });

  // Arrastar para reordenar as tabs (guardado por dispositivo)
  function makeSortable(container, key, attr) {
    if (!container) return;
    try {
      const saved = JSON.parse(localStorage.getItem(key) || '[]');
      saved.forEach(k => { const el = container.querySelector('[' + attr + '="' + k + '"]'); if (el) container.appendChild(el); });
    } catch (e) {}
    const save = () => localStorage.setItem(key,
      JSON.stringify([...container.querySelectorAll('[' + attr + ']')].map(e => e.getAttribute(attr))));
    container.querySelectorAll('[' + attr + ']').forEach(el => {
      el.insertAdjacentHTML('afterbegin', '<span class="grip" aria-hidden="true">⠿</span>');
      el.addEventListener('pointerdown', e => {
        if (e.button) return;
        const sx = e.clientX, sy = e.clientY; let moved = false;
        const move = ev => {
          if (!moved && Math.hypot(ev.clientX - sx, ev.clientY - sy) < 8) return;
          if (!moved) { moved = true; el.classList.add('dragging'); try { el.setPointerCapture(ev.pointerId); } catch (_) {} }
          ev.preventDefault();
          let best = null, bd = Infinity;
          container.querySelectorAll('[' + attr + ']:not(.dragging)').forEach(o => {
            const r = o.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
            const d = Math.hypot(ev.clientX - cx, ev.clientY - cy);
            if (d < bd) { bd = d; best = { o, cx }; }
          });
          if (best) container.insertBefore(el, ev.clientX < best.cx ? best.o : best.o.nextSibling);
        };
        const up = () => {
          document.removeEventListener('pointermove', move);
          document.removeEventListener('pointerup', up);
          if (moved) {
            el.classList.remove('dragging'); save();
            const swallow = c => { c.stopPropagation(); c.preventDefault(); };
            el.addEventListener('click', swallow, { capture: true, once: true });
            setTimeout(() => el.removeEventListener('click', swallow, true), 50);
          }
        };
        document.addEventListener('pointermove', move);
        document.addEventListener('pointerup', up);
      });
    });
  }
  makeSortable($('cattabs'), 'compras_cat', 'data-cat');
  CATS.forEach(c => makeSortable($('sub-' + c.key), 'compras_sub_' + c.key, 'data-sub'));

  load();
  setInterval(load, 15000);
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(PAGE, cats=CATS, cats_json=json.dumps(CATS, ensure_ascii=False))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003)
