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
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
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
# ENVIADOS — salvo no Supabase também
# ══════════════════════════════
def ja_enviado(chave):
    try:
        r = req.get(
            f"{SUPA_URL}/rest/v1/enviados?chave=eq.{chave}&select=chave",
            headers=SUPA_HEADERS, timeout=10
        )
        return len(r.json()) > 0
    except:
        return False

def marcar_enviado(chave):
    try:
        req.post(
            f"{SUPA_URL}/rest/v1/enviados",
            headers=SUPA_HEADERS,
            json={"chave": chave},
            timeout=10
        )
    except Exception as e:
        print(f"❌ Erro ao marcar enviado: {e}")

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

    # Se não cadastrou horário, redistribui automaticamente
    if not produto["horarios"]:
        todos = get_produtos()
        redistribuir_horarios(todos)
        return jsonify({"ok": True, "produto": produto, "auto_horario": True})

    return jsonify({"ok": True, "produto": produto})

@app.route("/api/produtos/<int:pid>", methods=["DELETE"])
def excluir_produto(pid):
    if request.args.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    delete_produto(pid)
    return jsonify({"ok": True})


@app.route("/api/produtos/<int:pid>/horarios", methods=["PATCH"])
def editar_horarios(pid):
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    try:
        req.patch(
            f"{SUPA_URL}/rest/v1/produtos?id=eq.{pid}",
            headers=SUPA_HEADERS,
            json={"horarios": data.get("horarios", [])},
            timeout=10
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500

# ══════════════════════════════
# BOT — disparo via rota (sem thread duplicada)
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

frase_idx = 0


def enviar_video_telegram(video, frase):
    nome   = video.get("nome", "")
    preco  = video.get("preco", "")
    link   = video.get("link", "")
    video_url = video.get("video", "")

    legenda = (
        f"🛒 *{nome}*\n\n"
        f"💲 *Preço: R$ {preco}*\n\n"
        f"{frase}\n\n"
        f"👇 *Compre aqui:*\n{link}"
    )

    try:
        # Tenta enviar como vídeo
        r = req.post(
            f"https://api.telegram.org/bot{TOKEN}/sendVideo",
            json={"chat_id": GRUPO_ID, "video": video_url,
                  "caption": legenda, "parse_mode": "Markdown"},
            timeout=30
        )
        if r.json().get("ok"):
            print(f"✅ Vídeo enviado: {nome}")
            return
        # Fallback: envia como texto com link
        req.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": GRUPO_ID, "text": legenda + f"\n\n🎬 {video_url}", "parse_mode": "Markdown"},
            timeout=15
        )
        print(f"✅ Vídeo (texto): {nome}")
    except Exception as e:
        print(f"❌ Erro ao enviar vídeo: {e}")

def bot_loop():
    global frase_idx
    while True:
        try:
            agora    = datetime.now(BRASILIA)
            hora_str = agora.strftime("%H:%M")
            hoje     = agora.strftime("%Y-%m-%d")
            produtos = get_produtos()

            for produto in produtos:
                pid      = str(produto.get("id", ""))
                horarios = produto.get("horarios", [])
                if isinstance(horarios, str):
                    horarios = json.loads(horarios)
                for h in horarios:
                    chave = f"{pid}_{hoje}_{h}"
                    if h == hora_str and not ja_enviado(chave):
                        frase = FRASES[frase_idx % len(FRASES)]
                        frase_idx += 1
                        enviar_telegram(produto, frase)
                        marcar_enviado(chave)
                        time.sleep(2)

            # Envia vídeos agendados
            videos = get_videos()
            for video in videos:
                vid_id   = str(video.get("id", ""))
                horarios = video.get("horarios", [])
                if isinstance(horarios, str):
                    horarios = json.loads(horarios)
                for h in horarios:
                    chave = f"vid_{vid_id}_{hoje}_{h}"
                    if h == hora_str and not ja_enviado(chave):
                        frase = FRASES[frase_idx % len(FRASES)]
                        frase_idx += 1
                        enviar_video_telegram(video, frase)
                        marcar_enviado(chave)
                        time.sleep(2)
        except Exception as e:
            print(f"❌ Erro no bot: {e}")

        time.sleep(60)

def ping_loop():
    while True:
        try:
            req.get(APP_URL + "/ping", timeout=10)
            print("🏓 Ping!")
        except:
            pass
        time.sleep(600)



@app.route("/api/videos", methods=["GET"])
def listar_videos():
    return jsonify(get_videos())

@app.route("/api/videos", methods=["POST"])
def adicionar_video():
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    video = {
        "id": int(datetime.now(BRASILIA).timestamp() * 1000),
        "nome": data.get("nome", ""),
        "preco": data.get("preco", ""),
        "link": data.get("link", ""),
        "video": data.get("video", ""),
        "horarios": data.get("horarios", [])
    }
    add_video(video)
    return jsonify({"ok": True, "video": video})

@app.route("/api/videos/<int:vid>", methods=["DELETE"])
def excluir_video(vid):
    if request.args.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    delete_video(vid)
    return jsonify({"ok": True})

@app.route("/api/videos/<int:vid>/horarios", methods=["PATCH"])
def editar_horarios_video(vid):
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    try:
        req.patch(
            f"{SUPA_URL}/rest/v1/videos?id=eq.{vid}",
            headers=SUPA_HEADERS,
            json={"horarios": data.get("horarios", [])},
            timeout=10
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500

# ══════════════════════════════
# BOT — BOAS VINDAS
# ══════════════════════════════
BOAS_VINDAS = [
    "Oi, {nome}! 👋 Que bom ter você aqui no *ACHADINHOS DA CASA*! 🛍️\n\nPrepara o bolso porque vêm muitas ofertas incríveis por aí! 🔥",
    "Seja bem-vindo(a), {nome}! 🎉\n\nVocê chegou no lugar certo! Aqui a gente garimpeia os melhores produtos da Shopee todo dia pra você. 💰",
    "Olá, {nome}! 😊\n\nBem-vindo(a) ao *ACHADINHOS DA CASA*! Fique de olho nas ofertas, porque os preços aqui são de cair o queixo! 😱🛒",
    "{nome}, que ótimo ter você aqui! 🙌\n\nNo *ACHADINHOS DA CASA* a gente só divulga o que realmente vale a pena. Aproveita! ✅",
    "Boa vinda, {nome}! 🏠✨\n\nVocê acabou de entrar no grupo de ofertas mais quente do Telegram! Prepara pra economizar muito! 💸🔥",
    "Ei, {nome}! 👀\n\nSeja muito bem-vindo(a)! Aqui você vai encontrar aquele produto que estava procurando por um preço que não acredita! 🎯",
    "Olá, {nome}! 🌟\n\nQue bom que você chegou! No *ACHADINHOS DA CASA* tem oferta boa todo dia. Não esquece de ativar as notificações! 🔔",
    "Bem-vindo(a) ao grupo, {nome}! 🛍️❤️\n\nAqui é família! Compartilha com seus amigos também, todo mundo merece economizar! 😄",
]

bv_frase_idx = 0

def enviar_boas_vindas(nome):
    global bv_frase_idx
    frase = BOAS_VINDAS[bv_frase_idx % len(BOAS_VINDAS)].format(nome=nome)
    bv_frase_idx += 1
    try:
        req.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": GRUPO_ID, "text": frase, "parse_mode": "Markdown"},
            timeout=15
        )
        print(f"Boas-vindas enviadas para {nome}")
    except Exception as e:
        print(f"Erro nas boas-vindas: {e}")

def verificar_novos_membros():
    ultimo_id = 0
    while True:
        try:
            r = req.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": ultimo_id + 1, "timeout": 10, "allowed_updates": ["chat_member"]},
                timeout=15
            )
            updates = r.json().get("result", [])
            for update in updates:
                ultimo_id = update["update_id"]
                membro = update.get("chat_member", {})
                novo = membro.get("new_chat_member", {})
                if novo.get("status") == "member":
                    user = novo.get("user", {})
                    nome = user.get("first_name", "amigo(a)")
                    enviar_boas_vindas(nome)
        except Exception as e:
            print(f"Erro ao verificar membros: {e}")
        time.sleep(5)

# Usa variável de ambiente para garantir que só 1 processo inicia o bot
if os.environ.get("BOT_WORKER") == "true":
    threading.Thread(target=bot_loop, daemon=True).start()
    threading.Thread(target=ping_loop, daemon=True).start()
    threading.Thread(target=verificar_novos_membros, daemon=True).start()
    print("🤖 Bot iniciado!")

if __name__ == "__main__":
    os.environ["BOT_WORKER"] = "true"
    threading.Thread(target=bot_loop, daemon=True).start()
    threading.Thread(target=ping_loop, daemon=True).start()
    threading.Thread(target=verificar_novos_membros, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
@app.route("/site")
def site():
    return send_file("index.html")
