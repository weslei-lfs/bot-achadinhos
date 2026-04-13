from flask import Flask, request, jsonify, send_file
import json, os, requests as req
from datetime import datetime, timedelta
import threading, time
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
    "🎯 Produto top com preço imba tível!",
    "✅ Recomendo demais! Qualidade e preço no mesmo lugar!",
    "🚨 ATENÇÃO! Promoção por tempo limitado!",
]

def get_categorias_db():
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/categorias?select=*&order=id", headers=SUPA_HEADERS, timeout=10)
        return r.json() if r.ok else []
    except:
        return []

def detectar_categoria(nome, categorias=None):
    if categorias is None:
        categorias = get_categorias_db()
    n = nome.lower()
    for cat in categorias:
        if cat.get("nome","").lower() == "outros":
            continue
        palavras = cat.get("palavras_chave", [])
        if isinstance(palavras, str):
            palavras = json.loads(palavras)
        # Verifica palavra exata para evitar falsos positivos
        for p in palavras:
            p = p.lower().strip()
            if len(p) <= 3:
                # Palavras curtas: verifica se é palavra exata
                import re
                if re.search(r'\b' + re.escape(p) + r'\b', n):
                    return cat.get("nome", "Outros")
            else:
                if p in n:
                    return cat.get("nome", "Outros")
    return "Outros"

def get_produtos():
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/produtos?select=*&order=id.desc", headers=SUPA_HEADERS, timeout=10)
        return r.json() if r.ok else []
    except: return []

def add_produto(produto):
    try: req.post(f"{SUPA_URL}/rest/v1/produtos", headers=SUPA_HEADERS, json=produto, timeout=10)
    except: pass

def update_produto(pid, data):
    try: req.patch(f"{SUPA_URL}/rest/v1/produtos?id=eq.{pid}", headers=SUPA_HEADERS, json=data, timeout=10)
    except: pass

def delete_produto(pid):
    try: req.delete(f"{SUPA_URL}/rest/v1/produtos?id=eq.{pid}", headers=SUPA_HEADERS, timeout=10)
    except: pass

def get_videos():
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/videos?select=*&order=id.desc", headers=SUPA_HEADERS, timeout=10)
        return r.json() if r.ok else []
    except: return []

def add_video(video):
    try: req.post(f"{SUPA_URL}/rest/v1/videos", headers=SUPA_HEADERS, json=video, timeout=10)
    except: pass

def delete_video(vid):
    try: req.delete(f"{SUPA_URL}/rest/v1/videos?id=eq.{vid}", headers=SUPA_HEADERS, timeout=10)
    except: pass

def get_config_db():
    """Busca configurações da tabela configuracoes no Supabase"""
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/configuracoes?select=*", headers=SUPA_HEADERS, timeout=10)
        configs = r.json() if r.ok else []
        result = {}
        for c in configs:
            val = c.get("valor", {})
            if isinstance(val, str):
                val = json.loads(val)
            result[c["chave"]] = val
        return result
    except:
        return {}

def get_enviados():
    if os.path.exists("enviados.json"):
        with open("enviados.json") as f: return json.load(f)
    return {}

def save_enviados(d):
    with open("enviados.json","w") as f: json.dump(d, f)

def redistribuir_produtos():
    """
    Distribui produtos em ciclo contínuo dentro do período configurado.
    Ex: 58 produtos em 7 dias → ~8 por dia, uniformemente espaçados.
    Quando o ciclo termina, começa de novo automaticamente (ciclo infinito).
    """
    configs = get_config_db()
    periodo = configs.get("periodo", {})

    hora_inicio_str = periodo.get("inicio", "08:00")
    hora_fim_str    = periodo.get("fim", "22:00")
    dias            = int(periodo.get("dias", 7))

    # Converte para minutos
    hi_h, hi_m = map(int, hora_inicio_str.split(":"))
    hf_h, hf_m = map(int, hora_fim_str.split(":"))
    inicio_min = hi_h * 60 + hi_m
    fim_min    = hf_h * 60 + hf_m
    minutos_por_dia = max(1, fim_min - inicio_min)

    produtos = get_produtos()
    if not produtos:
        print("Nenhum produto para redistribuir")
        return

    total = len(produtos)
    total_slots = minutos_por_dia * dias  # total de minutos disponíveis no ciclo

    # Intervalo uniforme entre produtos
    intervalo = total_slots / total

    # Data de início = hoje
    hoje = datetime.now(BRASILIA)
    dt_base = hoje.replace(hour=hi_h, minute=hi_m, second=0, microsecond=0)

    print(f"Redistribuindo {total} produtos | {hora_inicio_str}-{hora_fim_str} | {dias} dias | Intervalo: {intervalo:.0f}min")

    for i, produto in enumerate(produtos):
        offset_min = i * intervalo  # minuto absoluto dentro do ciclo

        # Quantos dias completos
        dia_idx    = int(offset_min // minutos_por_dia)
        min_no_dia = offset_min % minutos_por_dia

        # Horário no dia
        hora_abs = inicio_min + min_no_dia
        h = int(hora_abs) // 60
        m = int(hora_abs) % 60

        # Se passou do fim do dia (segurança)
        if h * 60 + m >= fim_min:
            h = hi_h
            m = hi_m

        data = dt_base + timedelta(days=dia_idx)
        horario_str = f"{h:02d}:{m:02d}"
        data_str    = data.strftime("%d/%m")

        update_produto(produto["id"], {
            "horarios": [f"{data_str} {horario_str}"]
        })

    print(f"✅ {total} produtos redistribuídos em ciclo de {dias} dias!")

@app.route("/")
def painel():
    return send_file("painel.html")

@app.route("/loja")
def loja():
    return send_file("index.html")

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
    cat = data.get("categoria") or detectar_categoria(data.get("nome",""))
    produto = {
        "id": int(datetime.now(BRASILIA).timestamp() * 1000),
        "nome": data.get("nome",""),
        "preco": data.get("preco",""),
        "link": data.get("link",""),
        "imagem": data.get("imagem",""),
        "categoria": cat,
        "horarios": []
    }
    add_produto(produto)
    redistribuir_produtos()
    return jsonify({"ok": True, "produto": produto, "auto_distribuido": True})

@app.route("/api/produtos/<int:pid>", methods=["PATCH"])
def editar_produto(pid):
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    campos = {k:v for k,v in data.items() if k in ["nome","preco","link","imagem","categoria","horarios","data_envio"]}
    update_produto(pid, campos)
    return jsonify({"ok": True})

@app.route("/api/produtos/<int:pid>", methods=["DELETE"])
def excluir_produto(pid):
    if request.args.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    delete_produto(pid)
    return jsonify({"ok": True})

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
        "nome": data.get("nome",""),
        "preco": data.get("preco",""),
        "link": data.get("link",""),
        "video": data.get("video",""),
        "categoria": data.get("categoria") or detectar_categoria(data.get("nome","")),
        "horarios": data.get("horarios",[])
    }
    add_video(video)
    return jsonify({"ok": True})

@app.route("/api/videos/<int:vid>", methods=["DELETE"])
def excluir_video(vid):
    if request.args.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    delete_video(vid)
    return jsonify({"ok": True})

@app.route("/api/config", methods=["GET"])
def get_config_route():
    return jsonify(get_config())

@app.route("/api/config", methods=["POST"])
def save_config_route():
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    cfg = {k:v for k,v in data.items() if k != "senha"}
    save_config(cfg)
    redistribuir_produtos()
    return jsonify({"ok": True})

@app.route("/api/redistribuir", methods=["POST"])
def redistribuir_route():
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    redistribuir_produtos()
    return jsonify({"ok": True})

# ══════════════════════════════
# ROTAS — CATEGORIAS
# ══════════════════════════════
@app.route("/api/categorias", methods=["GET"])
def listar_categorias():
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/categorias?select=*&order=id", headers=SUPA_HEADERS, timeout=10)
        return jsonify(r.json() if r.ok else [])
    except:
        return jsonify([])

@app.route("/api/categorias", methods=["POST"])
def adicionar_categoria():
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    cat = {
        "id": int(datetime.now(BRASILIA).timestamp() * 1000),
        "nome": data.get("nome", ""),
        "emoji": data.get("emoji", "📦"),
        "palavras_chave": data.get("palavras_chave", [])
    }
    req.post(f"{SUPA_URL}/rest/v1/categorias", headers=SUPA_HEADERS, json=cat, timeout=10)
    return jsonify({"ok": True, "categoria": cat})

@app.route("/api/categorias/<int:cid>", methods=["DELETE"])
def excluir_categoria(cid):
    if request.args.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    req.delete(f"{SUPA_URL}/rest/v1/categorias?id=eq.{cid}", headers=SUPA_HEADERS, timeout=10)
    return jsonify({"ok": True})

# ══════════════════════════════
# ROTAS — CONFIGURAÇÕES
# ══════════════════════════════
@app.route("/api/configuracoes", methods=["GET"])
def listar_configuracoes():
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/configuracoes?select=*", headers=SUPA_HEADERS, timeout=10)
        configs = r.json() if r.ok else []
        result = {}
        for c in configs:
            val = c.get("valor", {})
            if isinstance(val, str):
                import json as _json
                val = _json.loads(val)
            result[c["chave"]] = val
        return jsonify(result)
    except:
        return jsonify({})

@app.route("/api/configuracoes", methods=["POST"])
def salvar_configuracoes():
    data = request.json
    if data.get("senha") != SENHA:
        return jsonify({"ok": False}), 401
    periodo = data.get("periodo", {})
    # Tenta update, se não existir insere
    r = req.patch(f"{SUPA_URL}/rest/v1/configuracoes?chave=eq.periodo",
        headers=SUPA_HEADERS, json={"valor": periodo}, timeout=10)
    if not r.ok or r.status_code == 404:
        req.post(f"{SUPA_URL}/rest/v1/configuracoes",
            headers=SUPA_HEADERS, json={"chave": "periodo", "valor": periodo}, timeout=10)
    redistribuir_produtos()
    return jsonify({"ok": True})

def enviar_telegram(produto, frase):
    nome = produto.get("nome","")
    preco = produto.get("preco","")
    link = produto.get("link","")
    imagem = produto.get("imagem","")
    legenda = f"🛒 *{nome}*\n\n💲 *Preco: R$ {preco}*\n\n{frase}\n\n👇 *Compre aqui:*\n{link}"
    try:
        if imagem:
            r = req.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                json={"chat_id": GRUPO_ID, "photo": imagem, "caption": legenda, "parse_mode": "Markdown"}, timeout=15)
            if r.json().get("ok"): return
        req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": GRUPO_ID, "text": legenda, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e: print(f"Erro: {e}")

def enviar_video_telegram(video, frase):
    nome = video.get("nome","")
    preco = video.get("preco","")
    link = video.get("link","")
    video_url = video.get("video","")
    legenda = f"🛒 *{nome}*\n\n💲 *Preco: R$ {preco}*\n\n{frase}\n\n👇 *Compre aqui:*\n{link}"
    try:
        r = req.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo",
            json={"chat_id": GRUPO_ID, "video": video_url, "caption": legenda, "parse_mode": "Markdown"}, timeout=30)
        if not r.json().get("ok"):
            req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": GRUPO_ID, "text": legenda, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e: print(f"Erro video: {e}")

frase_idx = 0

def bot_loop():
    global frase_idx
    while True:
        try:
            agora = datetime.now(BRASILIA)
            hora_str = agora.strftime("%H:%M")
            hoje_dmm = agora.strftime("%d/%m")  # formato dd/mm
            hoje_ymd = agora.strftime("%Y-%m-%d")
            produtos = get_produtos()
            videos = get_videos()
            enviados = get_enviados()

            for produto in produtos:
                pid = str(produto.get("id",""))
                horarios = produto.get("horarios",[])
                if isinstance(horarios, str):
                    try: horarios = json.loads(horarios)
                    except: horarios = []
                for h in horarios:
                    # Suporta formato "dd/mm HH:MM" e "HH:MM"
                    h_str = str(h).strip()
                    if " " in h_str:
                        # Formato: "15/04 14:30"
                        partes = h_str.split(" ")
                        data_h = partes[0]  # "15/04"
                        hora_h = partes[1]  # "14:30"
                        deve_enviar = (data_h == hoje_dmm and hora_h == hora_str)
                    else:
                        # Formato antigo: "14:30"
                        deve_enviar = (h_str == hora_str)

                    chave = f"{pid}_{hoje_ymd}_{h_str}"
                    if deve_enviar and chave not in enviados:
                        enviar_telegram(produto, FRASES[frase_idx % len(FRASES)])
                        frase_idx += 1
                        enviados[chave] = True
                        save_enviados(enviados)
                        time.sleep(2)

            for video in videos:
                vid_id = str(video.get("id",""))
                horarios = video.get("horarios",[])
                if isinstance(horarios, str):
                    try: horarios = json.loads(horarios)
                    except: horarios = []
                for h in horarios:
                    h_str = str(h).strip()
                    if " " in h_str:
                        partes = h_str.split(" ")
                        data_h = partes[0]
                        hora_h = partes[1]
                        deve_enviar = (data_h == hoje_dmm and hora_h == hora_str)
                    else:
                        deve_enviar = (h_str == hora_str)

                    chave = f"vid_{vid_id}_{hoje_ymd}_{h_str}"
                    if deve_enviar and chave not in enviados:
                        enviar_video_telegram(video, FRASES[frase_idx % len(FRASES)])
                        frase_idx += 1
                        enviados[chave] = True
                        save_enviados(enviados)
                        time.sleep(2)

            # Verifica se todos os produtos do ciclo já foram enviados — reinicia
            agora2 = datetime.now(BRASILIA)
            configs = get_config_db()
            periodo = configs.get("periodo", {})
            dias_ciclo = int(periodo.get("dias", 7))
            hora_fim_str = periodo.get("fim", "22:00")
            hf_h2, hf_m2 = map(int, hora_fim_str.split(":"))

            # Verifica se chegou no último dia + última hora do ciclo
            configs_check = get_config_db()
            prods_check = get_produtos()
            if prods_check:
                # Pega a última data/hora de envio
                ultimas = []
                for p in prods_check:
                    hs = p.get("horarios", [])
                    if isinstance(hs, str):
                        try: hs = json.loads(hs)
                        except: hs = []
                    for h in hs:
                        ultimas.append(str(h))
                if ultimas:
                    ultima = sorted(ultimas)[-1]
                    if " " in ultima:
                        data_ult, hora_ult = ultima.split(" ")
                        dia_ult = int(data_ult.split("/")[0])
                        mes_ult = int(data_ult.split("/")[1])
                        # Se hoje já passou da última data programada, redistribui
                        if agora2.day > dia_ult or (agora2.day == dia_ult and agora2.strftime("%H:%M") > hora_ult):
                            print("🔄 Ciclo completo! Reiniciando distribuição...")
                            redistribuir_produtos()

        except Exception as e: print(f"Bot error: {e}")
        time.sleep(60)

def ping_loop():
    while True:
        try: req.get(APP_URL + "/ping", timeout=10)
        except: pass
        time.sleep(600)

def boas_vindas_loop():
    ultimo_id = 0
    msgs = [
        "Oi, {nome}! Seja bem-vindo(a) ao ACHADINHOS DA CASA! Prepara o bolso porque vem muita oferta boa por ai!",
        "Bem-vindo(a), {nome}! Voce chegou no lugar certo! Aqui a gente garimpeia os melhores produtos da Shopee todo dia!",
        "Ola, {nome}! Fique de olho nas ofertas, porque os precos aqui sao de cair o queixo!",
        "{nome}, que otimo ter voce aqui! No ACHADINHOS DA CASA so divulgamos o que realmente vale a pena!",
        "Ei, {nome}! Seja muito bem-vindo(a)! Voce vai encontrar aquele produto que estava procurando por um preco incrivel!",
    ]
    idx = 0
    while True:
        try:
            r = req.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": ultimo_id+1, "timeout": 10, "allowed_updates": ["chat_member"]}, timeout=15)
            for update in r.json().get("result",[]):
                ultimo_id = update["update_id"]
                novo = update.get("chat_member",{}).get("new_chat_member",{})
                if novo.get("status") == "member":
                    nome = novo.get("user",{}).get("first_name","amigo(a)")
                    frase = msgs[idx % len(msgs)].format(nome=nome)
                    idx += 1
                    req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        json={"chat_id": GRUPO_ID, "text": frase}, timeout=15)
        except: pass
        time.sleep(5)


# ══════════════════════════════
# ANALYTICS DE CLIQUES
# ══════════════════════════════
@app.route("/api/click", methods=["POST"])
def registrar_click():
    data = request.json
    click = {
        "id": int(datetime.now(BRASILIA).timestamp() * 1000),
        "produto_id": data.get("produto_id"),
        "produto_nome": data.get("nome", ""),
        "categoria": data.get("categoria", ""),
        "timestamp": datetime.now(BRASILIA).isoformat()
    }
    try:
        req.post(f"{SUPA_URL}/rest/v1/clicks", headers=SUPA_HEADERS, json=click, timeout=10)
    except:
        pass
    return jsonify({"ok": True})

@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/clicks?select=*&order=timestamp.desc&limit=500", headers=SUPA_HEADERS, timeout=10)
        clicks = r.json() if r.ok else []
        # Agrupa por produto
        por_produto = {}
        por_categoria = {}
        for c in clicks:
            nome = c.get("produto_nome","")
            cat = c.get("categoria","")
            por_produto[nome] = por_produto.get(nome, 0) + 1
            por_categoria[cat] = por_categoria.get(cat, 0) + 1
        top_produtos = sorted(por_produto.items(), key=lambda x: x[1], reverse=True)[:10]
        top_cats = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)
        return jsonify({"total": len(clicks), "por_produto": top_produtos, "por_categoria": top_cats})
    except Exception as e:
        return jsonify({"total": 0, "por_produto": [], "por_categoria": []})

# ══════════════════════════════
# BOT COMMANDS (/ofertas, /start)
# ══════════════════════════════
def processar_commands():
    ultimo_id = [0]
    while True:
        try:
            r = req.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": ultimo_id[0]+1, "timeout": 10, "allowed_updates": ["message","chat_member"]},
                timeout=15
            )
            updates = r.json().get("result", [])
            for update in updates:
                ultimo_id[0] = update["update_id"]

                # Boas vindas
                membro = update.get("chat_member", {})
                novo = membro.get("new_chat_member", {})
                if novo.get("status") == "member":
                    user = novo.get("user", {})
                    nome = user.get("first_name", "amigo(a)")
                    enviar_boas_vindas(nome)

                # Comandos
                msg = update.get("message", {})
                texto = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")

                if texto.startswith("/ofertas") and chat_id:
                    produtos = supa_get("produtos")
                    if not produtos:
                        req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": "😅 Nenhum produto cadastrado ainda!"}, timeout=10)
                    else:
                        import random
                        hoje = random.sample(produtos, min(5, len(produtos)))
                        texto_resp = "🛍️ *Ofertas de Hoje!*\n\n"
                        for p in hoje:
                            texto_resp += f"▪️ *{p['nome']}*\n💰 R$ {p['preco']}\n🔗 {p['link']}\n\n"
                        req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": texto_resp, "parse_mode": "Markdown"}, timeout=15)

                elif texto.startswith("/start") and chat_id:
                    req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        json={"chat_id": chat_id, "text": "👋 Bem-vindo ao *ACHADINHOS DA CASA*!\n\n🛍️ Aqui você recebe as melhores ofertas da Shopee todo dia!\n\n📌 Comandos disponíveis:\n/ofertas — Ver ofertas de hoje\n/start — Ver esta mensagem", "parse_mode": "Markdown"}, timeout=15)

        except Exception as e:
            print(f"❌ Command loop: {e}")
        time.sleep(5)

# ══════════════════════════════
# RELATÓRIO SEMANAL
# ══════════════════════════════
def relatorio_semanal():
    while True:
        try:
            agora = datetime.now(BRASILIA)
            # Toda segunda-feira às 09:00
            if agora.weekday() == 0 and agora.strftime("%H:%M") == "09:00":
                produtos = supa_get("produtos")
                videos = supa_get("videos")
                total = len(produtos) + len(videos)

                # Conta por categoria
                cats = {}
                for p in produtos:
                    c = p.get("categoria","Outros")
                    cats[c] = cats.get(c,0)+1

                cat_txt = "\n".join([f"  • {c}: {n} produto(s)" for c,n in sorted(cats.items(),key=lambda x:x[1],reverse=True)[:5]])

                msg = (
                    f"📊 *Relatório Semanal — ACHADINHOS DA CASA*\n\n"
                    f"📦 Total de produtos: *{len(produtos)}*\n"
                    f"🎬 Total de vídeos: *{len(videos)}*\n"
                    f"📁 Total geral: *{total}*\n\n"
                    f"🏆 *Top categorias:*\n{cat_txt}\n\n"
                    f"✅ Sistema funcionando perfeitamente!\n"
                    f"🔗 Painel: https://bot-achadinhos-rsco.onrender.com"
                )

                req.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": GRUPO_ID, "text": msg, "parse_mode": "Markdown"},
                    timeout=15
                )
                print("📊 Relatório semanal enviado!")
                time.sleep(70)  # evita enviar duas vezes no mesmo minuto
        except Exception as e:
            print(f"❌ Relatório: {e}")
        time.sleep(60)

if os.environ.get("BOT_WORKER") == "true":
    threading.Thread(target=bot_loop, daemon=True).start()
    threading.Thread(target=ping_loop, daemon=True).start()
    threading.Thread(target=boas_vindas_loop, daemon=True).start()
    print("Bot iniciado!")

if __name__ == "__main__":
    os.environ["BOT_WORKER"] = "true"
    threading.Thread(target=bot_loop, daemon=True).start()
    threading.Thread(target=ping_loop, daemon=True).start()
    threading.Thread(target=boas_vindas_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
