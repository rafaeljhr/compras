"""Lista de Compras (alimentação) — quadro partilhado de casa.

App web (Flask) em português. Dois níveis de navegação (Categoria → Subcategoria),
ambos editáveis pelo utilizador (adicionar/editar/eliminar) e guardados no servidor.
Cada produto é um item permanente com uma "quantidade a comprar" (0 = fora da lista);
o nome é editável inline. A lista "A comprar" agrega tudo o que tem quantidade.

Estado em volume /data. Corre no porto 8003.
"""

import base64
import json
import os
import tempfile
import unicodedata
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request, Response

app = Flask(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).with_name("data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
ITEMS_FILE = DATA_DIR / "items.json"
STRUCT_FILE = DATA_DIR / "structure.json"

DEFAULT_CATS = [
    {"key": "fl", "label": "Frutas & Legumes", "icone": "🥦", "subs": [
        {"key": "frutas", "label": "Frutas"}, {"key": "legumes", "label": "Legumes"},
        {"key": "frescos", "label": "Ervas & Temperos"}]},
    {"key": "cpo", "label": "Carne, Peixe & Ovos", "icone": "🥩", "subs": [
        {"key": "carne", "label": "Carne"}, {"key": "peixe", "label": "Peixe"},
        {"key": "mariscos", "label": "Mariscos"}, {"key": "ovos", "label": "Ovos"}]},
    {"key": "lat", "label": "Laticínios & Frios", "icone": "🧀", "subs": [
        {"key": "leite", "label": "Leite & Iogurtes"}, {"key": "queijos", "label": "Queijos"},
        {"key": "manteiga", "label": "Manteiga & Natas"}, {"key": "charcutaria", "label": "Charcutaria"}]},
    {"key": "enl", "label": "Enlatados & Conservas", "icone": "🥫", "subs": [
        {"key": "vegetais", "label": "Vegetais"}, {"key": "frutas", "label": "Frutas"},
        {"key": "peixe", "label": "Peixe"}, {"key": "carne", "label": "Carne"},
        {"key": "leguminosas", "label": "Leguminosas"}]},
    {"key": "mer", "label": "Mercearia", "icone": "🧂", "subs": [
        {"key": "massarroz", "label": "Massa & Arroz"}, {"key": "molhos", "label": "Molhos & Temperos"},
        {"key": "oleos", "label": "Óleos & Vinagres"}, {"key": "pa", "label": "Pequeno-almoço"},
        {"key": "snacks", "label": "Snacks & Doces"}]},
    {"key": "pad", "label": "Padaria", "icone": "🥖", "subs": [
        {"key": "pao", "label": "Pão"}, {"key": "bolachas", "label": "Bolachas & Cereais"},
        {"key": "pastelaria", "label": "Pastelaria"}]},
    {"key": "cong", "label": "Congelados", "icone": "🧊", "subs": [
        {"key": "legumes", "label": "Legumes"}, {"key": "peixe", "label": "Peixe"},
        {"key": "refeicoes", "label": "Refeições"}, {"key": "gelados", "label": "Gelados"}]},
    {"key": "beb", "label": "Bebidas", "icone": "🧃", "subs": [
        {"key": "aguas", "label": "Águas"}, {"key": "sumos", "label": "Sumos & Refrigerantes"},
        {"key": "cafe", "label": "Café & Chá"}, {"key": "alcool", "label": "Álcool"}]},
]

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


def _key():
    return uuid.uuid4().hex[:6]


def _write(path, data):
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        name = tmp.name
    os.replace(name, path)


def read_structure():
    try:
        d = json.loads(STRUCT_FILE.read_text())
        if isinstance(d, list) and d:
            return d
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    cats = json.loads(json.dumps(DEFAULT_CATS))  # deep copy
    _write(STRUCT_FILE, cats)
    return cats


def write_structure(cats):
    _write(STRUCT_FILE, cats)


def read_items():
    try:
        d = json.loads(ITEMS_FILE.read_text())
        if isinstance(d, list):
            return d
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    items = [{"id": _key() + _key(), "nome": n, "cat": c, "sub": s, "qtd": 0} for c, s, n in SEED]
    _write(ITEMS_FILE, items)
    return items


def write_items(items):
    _write(ITEMS_FILE, items)


def _valid(cats, cat, sub):
    c = next((x for x in cats if x["key"] == cat), None)
    return bool(c and any(s["key"] == sub for s in c["subs"]))


def payload():
    return {"cats": read_structure(), "items": read_items()}


@app.route("/api/data")
def api_data():
    return jsonify(payload())


# --- itens -------------------------------------------------------------------
@app.route("/api/items/add", methods=["POST"])
def items_add():
    d = request.get_json(silent=True) or {}
    nome = (d.get("nome") or "").strip()
    cat, sub = (d.get("cat") or "").strip(), (d.get("sub") or "").strip()
    if not nome or not _valid(read_structure(), cat, sub):
        return jsonify({"ok": False}), 400
    items = read_items()
    items.append({"id": _key() + _key(), "nome": nome, "cat": cat, "sub": sub, "qtd": 1})
    write_items(items)
    return jsonify(payload())


@app.route("/api/items/qty", methods=["POST"])
def items_qty():
    d = request.get_json(silent=True) or {}
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
    return jsonify(payload())


@app.route("/api/items/edit", methods=["POST"])
def items_edit():
    d = request.get_json(silent=True) or {}
    item_id = (d.get("id") or "").strip()
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"ok": False}), 400
    items = read_items()
    for it in items:
        if it.get("id") == item_id:
            it["nome"] = nome
            break
    write_items(items)
    return jsonify(payload())


@app.route("/api/items/delete", methods=["POST"])
def items_delete():
    d = request.get_json(silent=True) or {}
    item_id = (d.get("id") or "").strip()
    write_items([it for it in read_items() if it.get("id") != item_id])
    return jsonify(payload())


@app.route("/api/items/clear", methods=["POST"])
def items_clear():
    items = read_items()
    for it in items:
        it["qtd"] = 0
    write_items(items)
    return jsonify(payload())


# --- categorias / subcategorias ----------------------------------------------
@app.route("/api/cat/add", methods=["POST"])
def cat_add():
    d = request.get_json(silent=True) or {}
    label = (d.get("label") or "").strip()
    if not label:
        return jsonify({"ok": False}), 400
    cats = read_structure()
    cats.append({"key": _key(), "label": label, "icone": (d.get("icone") or "🛍️").strip() or "🛍️", "subs": []})
    write_structure(cats)
    return jsonify(payload())


@app.route("/api/cat/edit", methods=["POST"])
def cat_edit():
    d = request.get_json(silent=True) or {}
    key, label = (d.get("key") or "").strip(), (d.get("label") or "").strip()
    cats = read_structure()
    for c in cats:
        if c["key"] == key:
            if label:
                c["label"] = label
            if d.get("icone") is not None and d.get("icone").strip():
                c["icone"] = d["icone"].strip()
            break
    write_structure(cats)
    return jsonify(payload())


@app.route("/api/cat/delete", methods=["POST"])
def cat_delete():
    d = request.get_json(silent=True) or {}
    key = (d.get("key") or "").strip()
    write_structure([c for c in read_structure() if c["key"] != key])
    write_items([it for it in read_items() if it.get("cat") != key])
    return jsonify(payload())


@app.route("/api/cat/reorder", methods=["POST"])
def cat_reorder():
    d = request.get_json(silent=True) or {}
    order = d.get("order") or []
    cats = read_structure()
    cats.sort(key=lambda c: order.index(c["key"]) if c["key"] in order else 999)
    write_structure(cats)
    return jsonify(payload())


@app.route("/api/sub/add", methods=["POST"])
def sub_add():
    d = request.get_json(silent=True) or {}
    cat, label = (d.get("cat") or "").strip(), (d.get("label") or "").strip()
    if not label:
        return jsonify({"ok": False}), 400
    cats = read_structure()
    for c in cats:
        if c["key"] == cat:
            c["subs"].append({"key": _key(), "label": label})
            break
    write_structure(cats)
    return jsonify(payload())


@app.route("/api/sub/edit", methods=["POST"])
def sub_edit():
    d = request.get_json(silent=True) or {}
    cat, key, label = (d.get("cat") or "").strip(), (d.get("key") or "").strip(), (d.get("label") or "").strip()
    cats = read_structure()
    for c in cats:
        if c["key"] == cat:
            for s in c["subs"]:
                if s["key"] == key and label:
                    s["label"] = label
            break
    write_structure(cats)
    return jsonify(payload())


@app.route("/api/sub/delete", methods=["POST"])
def sub_delete():
    d = request.get_json(silent=True) or {}
    cat, key = (d.get("cat") or "").strip(), (d.get("key") or "").strip()
    cats = read_structure()
    for c in cats:
        if c["key"] == cat:
            c["subs"] = [s for s in c["subs"] if s["key"] != key]
            break
    write_structure(cats)
    write_items([it for it in read_items() if not (it.get("cat") == cat and it.get("sub") == key)])
    return jsonify(payload())


@app.route("/api/sub/reorder", methods=["POST"])
def sub_reorder():
    d = request.get_json(silent=True) or {}
    cat, order = (d.get("cat") or "").strip(), (d.get("order") or [])
    cats = read_structure()
    for c in cats:
        if c["key"] == cat:
            c["subs"].sort(key=lambda s: order.index(s["key"]) if s["key"] in order else 999)
            break
    write_structure(cats)
    return jsonify(payload())


APPLE_ICON_PNG = base64.b64decode("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")


@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    return Response(APPLE_ICON_PNG, mimetype="image/png")


@app.route("/healthz")
def healthz():
    return {"ok": True}


PAGE = r"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Compras</title>
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Compras">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
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
    .wrap { max-width:840px; margin:0 auto; padding:1rem 1rem 3rem; }
    .topbar { display:flex; align-items:center; justify-content:space-between; gap:.6rem; flex-wrap:wrap; }
    h1 { margin:.1rem 0; font-size:1.4rem; }
    .cart { display:flex; align-items:center; gap:.4rem; padding:.55rem .9rem; border-radius:999px;
      border:1px solid var(--green); background:var(--green); color:#fff; font-weight:800; cursor:pointer; font-size:.95rem; }
    .cart .badge { background:#fff; color:var(--green); }
    .level { margin-top:.7rem; }
    .level-title { font-size:.74rem; color:var(--muted); text-transform:uppercase; letter-spacing:.05em;
      font-weight:800; margin:0 0 .35rem .15rem; }
    .level-title b { color:var(--accent); text-transform:none; letter-spacing:0; }
    .tabs { display:flex; gap:.4rem; flex-wrap:wrap; }
    .tab { font-weight:700; border-radius:999px; cursor:grab; border:1px solid var(--border);
      background:var(--card); color:var(--muted); display:flex; gap:.3rem; align-items:center;
      touch-action:none; user-select:none; -webkit-user-select:none; }
    .tabs.cat .tab { font-size:.9rem; padding:.45rem .7rem; }
    .tabs.sub .tab { font-size:.82rem; padding:.35rem .6rem; }
    .tab.on { background:var(--accent); color:#fff; border-color:var(--accent); }
    .tab.dragging { opacity:.55; cursor:grabbing; }
    .tab .grip { opacity:.4; margin-right:.05rem; font-size:.95em; letter-spacing:-2px; }
    .tab.on .grip { opacity:.8; }
    .tab .tmenu { border:none; background:none; color:inherit; cursor:pointer; opacity:.55; font-weight:800;
      padding:0 .1rem; margin-left:.1rem; font-size:1rem; line-height:1; }
    .tab .tmenu:hover { opacity:1; }
    .tab.addtab { color:var(--accent); border-style:dashed; font-size:1rem; padding:.4rem .7rem; cursor:pointer; }
    .badge { font-size:.7rem; font-weight:800; min-width:17px; text-align:center; padding:0 .28rem;
      border-radius:999px; background:var(--accent); color:#fff; }
    .tab.on .badge { background:#fff; color:var(--accent); }
    .search { width:100%; padding:.6rem .85rem; font-size:1rem; border-radius:12px; margin:.9rem 0 .8rem;
      border:1px solid var(--border); background:var(--card); color:var(--text); box-shadow:var(--shadow); }
    .addbar { display:flex; gap:.5rem; margin-top:.9rem; }
    .addbar input { flex:1; padding:.6rem .8rem; font-size:1rem; border-radius:10px;
      border:1px solid var(--border); background:var(--card); color:var(--text); }
    .btn { padding:.55rem .85rem; border-radius:10px; border:1px solid var(--accent); background:var(--accent);
      color:#fff; font-weight:700; cursor:pointer; font-size:.9rem; white-space:nowrap; }
    .btn.ghost { background:transparent; color:var(--accent); }
    .listhead { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; margin:.9rem 0 .2rem; }
    .listhead b { font-size:1.1rem; margin-right:auto; }
    .item { display:flex; align-items:center; gap:.7rem; background:var(--card); border:1px solid var(--border);
      border-radius:12px; box-shadow:var(--shadow); padding:.55rem .8rem; margin-bottom:.45rem; }
    .item.on { border-color:var(--accent); background:var(--accent-bg); }
    .item .info { flex:1; min-width:0; }
    .item .nome { font-weight:700; cursor:text; border-radius:6px; padding:.05rem .2rem; }
    .item .nome:hover { background:rgba(127,127,127,.12); }
    .item .meta { font-size:.76rem; color:var(--muted); }
    .editinput { width:100%; font-size:1rem; font-weight:700; padding:.25rem .4rem; border-radius:8px;
      border:1px solid var(--accent); background:var(--bg); color:var(--text); }
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
    .popmenu { position:absolute; z-index:50; background:var(--card); border:1px solid var(--border);
      border-radius:10px; box-shadow:0 6px 20px rgba(0,0,0,.25); padding:.25rem; display:flex; flex-direction:column; }
    .popmenu button { border:none; background:none; color:var(--text); text-align:left; padding:.5rem .8rem;
      border-radius:7px; cursor:pointer; font-size:.9rem; white-space:nowrap; }
    .popmenu button:hover { background:var(--accent-bg); }
    footer { margin-top:2rem; text-align:center; color:var(--muted); font-size:.8rem; }
  </style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <h1>🛒 Compras</h1>
    <button id="cartbtn" class="cart">🛒 A comprar <span class="badge" id="cartn">0</span></button>
  </div>

  <div id="browser">
    <div class="level">
      <div class="level-title">Categorias</div>
      <div class="tabs cat" id="cattabs"></div>
    </div>
    <div class="level">
      <div class="level-title">Subcategorias de <b id="curcat"></b></div>
      <div class="tabs sub" id="subtabs"></div>
    </div>
    <div class="addbar" id="addbar">
      <input id="novo" placeholder="Adicionar produto a esta secção…" autocomplete="off">
      <button class="btn" id="add">＋ Adicionar</button>
    </div>
  </div>

  <div class="listhead hide" id="listhead">
    <b>🛒 A comprar</b>
    <button class="btn ghost" id="clearbtn">🧹 Limpar lista</button>
    <button class="btn ghost" id="backbtn">← Categorias</button>
  </div>

  <input id="q" class="search" type="search" autocomplete="off" placeholder="🔎 Pesquisar produto…">
  <div id="list"></div>

  <footer>Ajusta a quantidade com −/＋. Clica no nome de um produto para o editar (guarda ao sair).<br>
    Os ⋮ editam/eliminam tabs; o ＋ adiciona. Arrasta (⠿) para reordenar. Sincroniza sozinho.</footer>
</div>

<script>
  const $ = id => document.getElementById(id);
  const fold = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  let data = { cats: [], items: [] }, aCat = null, aSub = null, mode = 'cat', paused = false;

  const catObj = () => data.cats.find(c => c.key === aCat);
  function fixActive() {
    if (!data.cats.length) { aCat = aSub = null; return; }
    if (!data.cats.find(c => c.key === aCat)) aCat = data.cats[0].key;
    const c = catObj();
    if (c && !c.subs.find(s => s.key === aSub)) aSub = c.subs[0] ? c.subs[0].key : null;
  }
  async function api(path, body) {
    paused = true;
    try {
      const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
      data = await r.json();
    } finally { paused = false; }
    fixActive(); render();
  }
  function load() { if (paused) return; fetch('/api/data').then(r => r.json()).then(p => { data = p; fixActive(); render(); }); }

  // ---- popover menu ----
  function closeMenu() { document.querySelectorAll('.popmenu').forEach(m => m.remove()); paused = false; }
  function openMenu(btn, opts) {
    closeMenu(); paused = true;
    const m = document.createElement('div'); m.className = 'popmenu';
    opts.forEach(o => { const b = document.createElement('button'); b.textContent = o.label;
      b.onclick = e => { e.stopPropagation(); closeMenu(); o.fn(); }; m.appendChild(b); });
    document.body.appendChild(m);
    const r = btn.getBoundingClientRect();
    m.style.left = (window.scrollX + Math.min(r.left, innerWidth - m.offsetWidth - 8)) + 'px';
    m.style.top = (window.scrollY + r.bottom + 4) + 'px';
    setTimeout(() => document.addEventListener('pointerdown', closeMenu, { once: true, capture: true }), 0);
  }

  // ---- tabs ----
  function tabHTML(attr, key, label, count, withMenu) {
    const b = count ? `<span class="badge">${count}</span>` : '';
    const mn = withMenu ? `<button class="tmenu" data-menu="${key}">⋮</button>` : '';
    return `<div class="tab" ${attr}="${key}">${label}${b}${mn}</div>`;
  }
  function renderTabs() {
    const buy = data.items.filter(i => i.qtd > 0);
    const cc = $('cattabs');
    cc.innerHTML = data.cats.map(c =>
      tabHTML('data-cat', c.key, `${c.icone} ${esc(c.label)}`, buy.filter(i => i.cat === c.key).length, true)).join('')
      + '<div class="tab addtab" data-addcat>＋</div>';
    const c = catObj();
    $('curcat').textContent = c ? c.label : '—';
    const sc = $('subtabs');
    sc.innerHTML = (c ? c.subs : []).map(s =>
      tabHTML('data-sub', s.key, esc(s.label), buy.filter(i => i.cat === aCat && i.sub === s.key).length, true)).join('')
      + (c ? '<div class="tab addtab" data-addsub>＋</div>' : '');

    cc.querySelectorAll('[data-cat]').forEach(t => { t.classList.toggle('on', t.dataset.cat === aCat);
      t.addEventListener('click', () => { aCat = t.dataset.cat; fixActive(); render(); }); });
    sc.querySelectorAll('[data-sub]').forEach(t => { t.classList.toggle('on', t.dataset.sub === aSub);
      t.addEventListener('click', () => { aSub = t.dataset.sub; render(); }); });
    cc.querySelector('[data-addcat]').onclick = addCat;
    if (c) sc.querySelector('[data-addsub]').onclick = addSub;
    cc.querySelectorAll('[data-menu]').forEach(b => b.onclick = e => { e.stopPropagation(); catMenu(b, b.dataset.menu); });
    sc.querySelectorAll('[data-menu]').forEach(b => b.onclick = e => { e.stopPropagation(); subMenu(b, b.dataset.menu); });
    sortable(cc, 'data-cat', order => api('/api/cat/reorder', { order }));
    if (c) sortable(sc, 'data-sub', order => api('/api/sub/reorder', { cat: aCat, order }));
  }

  // ---- menus / add / edit ----
  function addCat() { const l = prompt('Nome da nova categoria:'); if (!l) return;
    const e = (prompt('Emoji (opcional):', '🛍️') || '').trim(); api('/api/cat/add', { label: l.trim(), icone: e }); }
  function catMenu(btn, key) { const c = data.cats.find(x => x.key === key); openMenu(btn, [
    { label: '✏️ Editar nome', fn: () => { const l = prompt('Nome da categoria:', c.label); if (l) api('/api/cat/edit', { key, label: l.trim() }); } },
    { label: '😀 Mudar emoji', fn: () => { const e = prompt('Emoji:', c.icone); if (e) api('/api/cat/edit', { key, icone: e.trim() }); } },
    { label: '🗑️ Eliminar', fn: () => { if (confirm(`Eliminar "${c.label}" e os seus produtos?`)) api('/api/cat/delete', { key }); } }]); }
  function addSub() { const l = prompt('Nome da nova subcategoria:'); if (l) api('/api/sub/add', { cat: aCat, label: l.trim() }); }
  function subMenu(btn, key) { const c = catObj(); const s = c.subs.find(x => x.key === key); openMenu(btn, [
    { label: '✏️ Editar nome', fn: () => { const l = prompt('Nome da subcategoria:', s.label); if (l) api('/api/sub/edit', { cat: aCat, key, label: l.trim() }); } },
    { label: '🗑️ Eliminar', fn: () => { if (confirm(`Eliminar "${s.label}" e os seus produtos?`)) api('/api/sub/delete', { cat: aCat, key }); } }]); }

  // ---- itens ----
  function stepHTML(it) {
    return `<div class="stepper"><button class="sb" data-q="${it.id}|-1">−</button>
      <span class="num ${it.qtd > 0 ? 'pos' : ''}">${it.qtd}</span>
      <button class="sb" data-q="${it.id}|1">+</button></div>`;
  }
  function row(it) {
    return `<div class="item ${it.qtd > 0 ? 'on' : ''}">
      <div class="info"><span class="nome" data-edit="${it.id}">${esc(it.nome)}</span></div>
      ${stepHTML(it)}<button class="x" data-del="${it.id}" title="remover">✕</button></div>`;
  }
  function rowLista(it) {
    const c = data.cats.find(x => x.key === it.cat);
    const s = c && c.subs.find(x => x.key === it.sub);
    return `<div class="item on"><div class="info"><span class="nome" data-edit="${it.id}">${esc(it.nome)}</span>
      <div class="meta">${s ? esc(s.label) : ''}</div></div>${stepHTML(it)}
      <button class="act done" data-buy="${it.id}|${it.qtd}" title="comprado">✓</button></div>`;
  }
  function startEdit(span, id) {
    const cur = span.textContent;
    const inp = document.createElement('input'); inp.className = 'editinput'; inp.value = cur;
    span.replaceWith(inp); inp.focus(); inp.select(); paused = true;
    let done = false;
    const finish = save => { if (done) return; done = true; paused = false;
      const v = inp.value.trim();
      if (save && v && v !== cur) api('/api/items/edit', { id, nome: v }); else render(); };
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); finish(true); }
      else if (e.key === 'Escape') finish(false); });
    inp.addEventListener('blur', () => finish(true));
  }

  function render() {
    if (!data.cats.length) { $('browser').classList.add('hide');
      $('list').innerHTML = '<div class="empty">Sem categorias.</div>'; return; }
    const buy = data.items.filter(i => i.qtd > 0);
    $('cartn').textContent = buy.length;
    $('browser').classList.toggle('hide', mode === 'lista');
    $('listhead').classList.toggle('hide', mode !== 'lista');

    if (mode !== 'lista') renderTabs();
    const term = fold($('q').value.trim());
    const box = $('list');
    if (mode === 'lista') {
      const f = buy.filter(i => !term || fold(i.nome).includes(term));
      if (!f.length) box.innerHTML = '<div class="empty">🛒 Lista vazia. Marca o que precisas nas categorias.</div>';
      else box.innerHTML = data.cats.map(c => {
        const sub = f.filter(i => i.cat === c.key);
        return sub.length ? `<div class="grouptitle">${c.icone} ${esc(c.label)}</div>` + sub.map(rowLista).join('') : '';
      }).join('');
    } else {
      let list = data.items.filter(i => i.cat === aCat && i.sub === aSub && (!term || fold(i.nome).includes(term)));
      list.sort((a, b) => ((b.qtd > 0) - (a.qtd > 0)) || a.nome.localeCompare(b.nome, 'pt'));
      box.innerHTML = list.length ? list.map(row).join('') : '<div class="empty">Sem itens aqui. Adiciona acima 👆</div>';
    }
    box.querySelectorAll('[data-q]').forEach(b => b.onclick = () => { const [id, dl] = b.dataset.q.split('|'); api('/api/items/qty', { id, delta: Number(dl) }); });
    box.querySelectorAll('[data-buy]').forEach(b => b.onclick = () => { const [id, q] = b.dataset.buy.split('|'); api('/api/items/qty', { id, delta: -Number(q) }); });
    box.querySelectorAll('[data-del]').forEach(b => b.onclick = () => api('/api/items/delete', { id: b.dataset.del }));
    box.querySelectorAll('.nome[data-edit]').forEach(s => s.onclick = () => startEdit(s, s.dataset.edit));
  }

  $('cartbtn').onclick = () => { mode = mode === 'lista' ? 'cat' : 'lista'; render(); };
  $('backbtn').onclick = () => { mode = 'cat'; render(); };
  $('clearbtn').onclick = () => { if (confirm('Limpar toda a lista de compras?')) api('/api/items/clear'); };
  $('q').addEventListener('input', render);
  function addNovo() { const n = $('novo').value.trim(); if (!n || !aSub) return; $('novo').value = ''; api('/api/items/add', { nome: n, cat: aCat, sub: aSub }); }
  $('add').onclick = addNovo;
  $('novo').addEventListener('keydown', e => { if (e.key === 'Enter') addNovo(); });

  // ---- arrastar tabs (ordem partilhada no servidor) ----
  function sortable(container, attr, onReorder) {
    container.querySelectorAll('[' + attr + ']').forEach(el => {
      el.insertAdjacentHTML('afterbegin', '<span class="grip" aria-hidden="true">⠿</span>');
      el.addEventListener('pointerdown', e => {
        if (e.button || (e.target.closest && e.target.closest('.tmenu'))) return;
        const sx = e.clientX, sy = e.clientY; let moved = false; const addtab = container.querySelector('.addtab');
        const move = ev => {
          if (!moved && Math.hypot(ev.clientX - sx, ev.clientY - sy) < 8) return;
          if (!moved) { moved = true; paused = true; el.classList.add('dragging'); try { el.setPointerCapture(ev.pointerId); } catch (_) {} }
          ev.preventDefault();
          let best = null, bd = Infinity;
          container.querySelectorAll('[' + attr + ']:not(.dragging)').forEach(o => {
            const r = o.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
            const d = Math.hypot(ev.clientX - cx, ev.clientY - cy); if (d < bd) { bd = d; best = { o, cx }; }
          });
          if (best) container.insertBefore(el, ev.clientX < best.cx ? best.o : best.o.nextSibling);
          if (addtab) container.appendChild(addtab);
        };
        const up = () => {
          document.removeEventListener('pointermove', move); document.removeEventListener('pointerup', up);
          if (moved) { el.classList.remove('dragging');
            const order = [...container.querySelectorAll('[' + attr + ']')].map(x => x.getAttribute(attr));
            const sw = c => { c.stopPropagation(); c.preventDefault(); };
            el.addEventListener('click', sw, { capture: true, once: true });
            setTimeout(() => el.removeEventListener('click', sw, true), 50);
            onReorder(order);
          } else { paused = false; }
        };
        document.addEventListener('pointermove', move); document.addEventListener('pointerup', up);
      });
    });
  }

  load();
  setInterval(load, 15000);
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(PAGE)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8003)
