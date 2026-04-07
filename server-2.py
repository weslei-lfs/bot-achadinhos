from flask import Flask, request, jsonify, send_file
import json
import os
import requests as req
from datetime import datetime
import threading
import time
from zoneinfo import ZoneInfo

BRASILIA = ZoneInfo("America/Sao_Paulo")

app = Flask(__name__)

PRODUTOS_FILE = "produtos.json"
ENVIADOS_FILE = "enviados.json"
TOKEN    = os.environ.get("TOKEN", "8660560171:AAHW5OcfhgnpGDaoXeadaSnf2NGLadIFh64")
GRUPO_ID = os.environ.get("GRUPO_ID", "-5116230681")
SENHA    = os.environ.get("SENHA", "achadinhos2024")

FRASES = [
    "🔥 IMPERDÍVEL! Corre que é por tempo limitado!",
    "😱 Que preço incrível! Não perde essa oportunidade!",
    "⚡ OFERTA RELÂMPAGO! Garante o seu agora!",
    "🛍️ Achado do dia! Vale muito a pena conferir!",
    "💰 Economia garantida! Aproveita antes que acabe!",
    "🎯 Produto top com preço imbatível!",
    "✅ Recomendo demais! Qualidade e preço no mesmo lugar!",
    "🚨 ATENÇÃO! Promoção por tempo limitado!",
]

def get_produtos():
    if os.path.exists(PRODUTOS_FILE):
        with open(PRODUTOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_produtos(p):
    with open(PRODUTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)

def get_enviados():
    if os.path.exists(ENVIADOS_FILE):
        with open(ENVIADOS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_enviados(d):
    with open(ENVIADOS_FILE, "w") as f:
        json.dump(d, f)

@app.route("/")
def index():
    return send_file("painel.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if data.get("senha") == SENHA:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "erro": "Senha incorreta"}), 401

@app.route("/api/produtos", methods=["GET"])
def listar_produtos():
    return jsonify(get_produtos())

@app.route("/api/produtos", methods=["POST"])
def adicionar_produto():
    data = request.json
    if not data.get("senha") == SENHA:
        return jsonify({"ok": False}), 401
    produtos = get_produtos()
    produto = {
        "id": int(datetime.now(BRASILIA).timestamp() * 1000),
        "nome": data.get("nome", ""),
        "preco": data.get("preco", ""),
        "link": data.get("link", ""),
        "imagem": data.get("imagem", ""),
        "horarios": data.get("horarios", [])
    }
    produtos.append(produto)
    save_produtos(produtos)
    return jsonify({"ok": True, "produto": produto})

@app.route("/api/produtos/<int:pid>", methods=["DELETE"])
def excluir_produto(pid):
    senha = request.args.get("senha", "")
    if senha != SENHA:
        return jsonify({"ok": False}), 401
    produtos = [p for p in get_produtos() if p.get("id") != pid]
    save_produtos(produtos)
    return jsonify({"ok": True})

def enviar_telegram(produto, frase):
    nome   = produto.get("nome", "")
    preco  = produto.get("preco", "")
    link   = produto.get("link", "")
    imagem = produto.get("imagem", "")

    legenda = (
        f"🛒 *{nome}*\n\n"
        f"💲 *Preço: R$ {preco}*\n\n"
        f"{frase}\n\n"
        f"👇 *Compre aqui:*\n{link}"
    )

    try:
        if imagem:
            r = req.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                json={"chat_id": GRUPO_ID, "photo": imagem,
                      "caption": legenda, "parse_mode": "Markdown"},
                timeout=15
            )
            if r.json().get("ok"):
                print(f"✅ Enviado com imagem: {nome}")
                return

        req.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": GRUPO_ID, "text": legenda, "parse_mode": "Markdown"},
            timeout=15
        )
        print(f"✅ Enviado (texto): {nome}")
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")

def bot_loop():
    frase_idx = 0
    while True:
        try:
            agora    = datetime.now(BRASILIA)
            hora_str = agora.strftime("%H:%M")
            hoje     = agora.strftime("%Y-%m-%d")
            produtos = get_produtos()
            enviados = get_enviados()

            for produto in produtos:
                pid      = str(produto.get("id", ""))
                horarios = produto.get("horarios", [])
                for h in horarios:
                    chave = f"{pid}_{hoje}_{h}"
                    if h == hora_str and chave not in enviados:
                        frase = FRASES[frase_idx % len(FRASES)]
                        frase_idx += 1
                        enviar_telegram(produto, frase)
                        enviados[chave] = True
                        save_enviados(enviados)
                        time.sleep(2)
        except Exception as e:
            print(f"❌ Erro no bot: {e}")

        time.sleep(60)

# Inicia o bot SEMPRE, independente de como o app é iniciado (gunicorn ou python)
t = threading.Thread(target=bot_loop, daemon=True)
t.start()
print("🤖 Bot iniciado em background!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
