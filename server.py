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

TOKEN    = os.environ.get("TOKEN", "8660560171:AAHW5OcfhgnpGDaoXeadaSnf2NGLadIFh64")
GRUPO_ID = os.environ.get("GRUPO_ID", "-5116230681")
SENHA    = os.environ.get("SENHA", "achadinhos2024")
APP_URL  = os.environ.get("APP_URL", "https://bot-achadinhos-rsco.onrender.com")

SUPA_URL = os.environ.get("SUPA_URL", "https://tolockvnctthjqphfkyw.supabase.co")
SUPA_KEY = os.environ.get("SUPA_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRvbG9ja3ZuY3R0aGpxcGhma3l3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU1NDI2ODMsImV4cCI6MjA5MTExODY4M30.6U6HoiS-DyOF1Re0q8vyVWXX2zEjOEQ0A4G4srVzspo")

SUPA_HEADERS = {
    "apikey": SUPA_KEY,
    "Authorization": f"Bearer {SUPA_KEY}",
    "Content-Type": "application/json"
}

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

# ══════════════════════════════
# SUPABASE — PRODUTOS
# ══════════════════════════════
def get_produtos():
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/produtos?select=*", headers=SUPA_HEADERS, timeout=10)
        return r.json()
    except Exception as e:
        print(f"❌ Erro ao buscar produtos: {e}")
        return []

def add_produto(produto):
    try:
        req.post(f"{SUPA_URL}/rest/v1/produtos", headers=SUPA_HEADERS, json=produto, timeout=10)
    except Exception as e:
        print(f"❌ Erro ao salvar produto: {e}")

def delete_produto(pid):
    try:
        req.delete(f"{SUPA_URL}/rest/v1/produtos?id=eq.{pid}", headers=SUPA_HEADERS, timeout=10)
    except Exception as e:
        print(f"❌ Erro ao deletar produto: {e}")

# ══════════════════════════════
# ENVIADOS — arquivo local (resetável)
# ══════════════════════════════
ENVIADOS_FILE = "enviados.json"

def get_enviados():
    if os.path.exists(ENVIADOS_FILE):
        with open(ENVIADOS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_enviados(d):
    with open(ENVIADOS_FILE, "w") as f:
        json.dump(d, f)

# ══════════════════════════════
# PING — mantém servidor acordado
# ══════════════════════════════
def ping_loop():
    while True:
        try:
            req.get(APP_URL + "/ping", timeout=10)
            print("🏓 Ping enviado!")
        except Exception as e:
            print(f"⚠️ Ping falhou: {e}")
        time.sleep(600)

# ══════════════════════════════
# ROTAS API
# ══════════════════════════════
@app.route("/")
def index():
    return send_file("painel.html")

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if data.get("senha") == SENHA:
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401

@app.route("/api/produtos", methods=["GET"])
def listar_produtos():
    return jsonify(get_produtos())

@app.route("/api/produtos", methods=["POST"])
def adicionar_produto():
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    produto = {
        "id": int(datetime.now(BRASILIA).timestamp() * 1000),
        "nome": data.get("nome", ""),
        "preco": data.get("preco", ""),
        "link": data.get("link", ""),
        "imagem": data.get("imagem", ""),
        "horarios": data.get("horarios", [])
    }
    add_produto(produto)
    return jsonify({"ok": True, "produto": produto})

@app.route("/api/produtos/<int:pid>", methods=["DELETE"])
def excluir_produto(pid):
    if request.args.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    delete_produto(pid)
    return jsonify({"ok": True})

# ══════════════════════════════
# BOT — LOOP EM THREAD
# ══════════════════════════════
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
                if isinstance(horarios, str):
                    horarios = json.loads(horarios)
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

# Inicia bot e ping SEMPRE
threading.Thread(target=bot_loop, daemon=True).start()
threading.Thread(target=ping_loop, daemon=True).start()
print("🤖 Bot e ping iniciados!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
