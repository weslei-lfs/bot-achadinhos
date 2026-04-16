from flask import Flask, request, jsonify, send_file
import json, os, re, requests as req
from datetime import datetime, timedelta
import threading, time
from zoneinfo import ZoneInfo

BRASILIA = ZoneInfo("America/Sao_Paulo")
app = Flask(__name__)

# ── VARIÁVEIS ──
TOKEN    = os.environ.get("TOKEN",    "8660560171:AAHW5OcfhgnpGDaoXeadaSnf2NGLadIFh64")
GRUPO_ID = os.environ.get("GRUPO_ID", "-5116230681")
SENHA    = os.environ.get("SENHA",    "achadinhos2024")
APP_URL  = os.environ.get("APP_URL",  "https://bot-achadinhos-rsco.onrender.com")
SUPA_URL = os.environ.get("SUPA_URL", "https://tolockvnctthjqphfkyw.supabase.co")
SUPA_KEY = os.environ.get("SUPA_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRvbG9ja3ZuY3R0aGpxcGhma3l3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU1NDI2ODMsImV4cCI6MjA5MTExODY4M30.6U6HoiS-DyOF1Re0q8vyVWXX2zEjOEQ0A4G4srVzspo")
IG_USER_ID = os.environ.get("IG_USER_ID", "17841437071615075")

HEADERS = {
    "apikey": SUPA_KEY,
    "Authorization": f"Bearer {SUPA_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}
HEADERS_UPSERT = {**HEADERS, "Prefer": "resolution=merge-duplicates"}

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
frase_idx = 0

# ══════════════════════════════
# SUPABASE HELPERS
# ══════════════════════════════
def db_get(table, params=""):
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/{table}?select=*{params}", headers=HEADERS, timeout=10)
        return r.json() if r.ok else []
    except: return []

def db_post(table, data):
    try: req.post(f"{SUPA_URL}/rest/v1/{table}", headers=HEADERS, json=data, timeout=10)
    except: pass

def db_upsert(table, data):
    try: req.post(f"{SUPA_URL}/rest/v1/{table}", headers=HEADERS_UPSERT, json=data, timeout=10)
    except: pass

def db_patch(table, filter_str, data):
    try: req.patch(f"{SUPA_URL}/rest/v1/{table}?{filter_str}", headers=HEADERS, json=data, timeout=10)
    except: pass

def db_delete(table, filter_str):
    try: req.delete(f"{SUPA_URL}/rest/v1/{table}?{filter_str}", headers=HEADERS, timeout=10)
    except: pass

# ══════════════════════════════
# CONFIGURAÇÕES
# ══════════════════════════════
def get_configs():
    """Retorna todas as configurações como dict"""
    try:
        rows = db_get("configuracoes")
        result = {}
        for row in rows:
            val = row.get("valor", {})
            if isinstance(val, str):
                try: val = json.loads(val)
                except: pass
            result[row["chave"]] = val
        return result
    except: return {}

def salvar_config(chave, valor):
    db_upsert("configuracoes", {"chave": chave, "valor": valor})

def get_periodo_tg():
    cfg = get_configs()
    p = cfg.get("periodo", {})
    if not isinstance(p, dict): p = {}
    return {
        "inicio": p.get("inicio", "08:00"),
        "fim":    p.get("fim",    "22:00"),
        "dias":   int(p.get("dias", 7))
    }

def get_config_ig():
    cfg = get_configs()
    p = cfg.get("ig_config", {})
    if not isinstance(p, dict): p = {}
    return {
        "inicio": p.get("inicio", "08:00"),
        "fim":    p.get("fim",    "22:00"),
        "dias":   int(p.get("dias", 7))
    }

# ══════════════════════════════
# CATEGORIAS
# ══════════════════════════════
def get_categorias():
    return db_get("categorias", "&order=id")

def detectar_categoria(nome):
    cats = get_categorias()
    n = nome.lower()
    for cat in cats:
        if cat.get("nome","").lower() == "outros": continue
        palavras = cat.get("palavras_chave", [])
        if isinstance(palavras, str):
            try: palavras = json.loads(palavras)
            except: palavras = []
        for p in palavras:
            p = p.lower().strip()
            if len(p) <= 3:
                if re.search(r'\b' + re.escape(p) + r'\b', n):
                    return cat.get("nome", "Outros")
            else:
                if p in n:
                    return cat.get("nome", "Outros")
    return "Outros"

# ══════════════════════════════
# REDISTRIBUIÇÃO
# ══════════════════════════════
def calcular_slots(items, inicio_str, fim_str, dias):
    """Distribui items uniformemente e retorna lista de (id, horario_str)"""
    try:
        hi_h, hi_m = map(int, inicio_str.split(":"))
        hf_h, hf_m = map(int, fim_str.split(":"))
    except:
        hi_h, hi_m = 8, 0
        hf_h, hf_m = 22, 0

    inicio_min = hi_h * 60 + hi_m
    fim_min    = hf_h * 60 + hf_m
    minutos_dia = max(1, fim_min - inicio_min)
    total_min   = minutos_dia * dias
    total       = len(items)
    intervalo   = total_min / total if total > 0 else 0

    hoje    = datetime.now(BRASILIA)
    dt_base = hoje.replace(hour=hi_h, minute=hi_m, second=0, microsecond=0)

    resultado = []
    for i, item in enumerate(items):
        offset    = i * intervalo
        dia_idx   = int(offset // minutos_dia)
        min_dia   = offset % minutos_dia
        hora_abs  = inicio_min + min_dia
        h = int(hora_abs) // 60
        m = int(hora_abs) % 60
        if h * 60 + m >= fim_min:
            h, m = hi_h, hi_m
        data = dt_base + timedelta(days=dia_idx)
        horario = f"{data.strftime('%d/%m')} {h:02d}:{m:02d}"
        resultado.append((item["id"], horario))
    return resultado

def redistribuir(tabela, items, inicio, fim, dias):
    if not items:
        print(f"Nenhum item em {tabela}")
        return
    slots = calcular_slots(items, inicio, fim, dias)
    for item_id, horario in slots:
        db_patch(tabela, f"id=eq.{item_id}", {"horarios": [horario]})
    print(f"✅ {len(slots)} itens de {tabela} redistribuídos ({inicio}-{fim}, {dias}d)")

def redistribuir_produtos():
    p = get_periodo_tg()
    redistribuir("produtos", db_get("produtos"), p["inicio"], p["fim"], p["dias"])

def redistribuir_videos():
    p = get_periodo_tg()
    redistribuir("videos", db_get("videos"), p["inicio"], p["fim"], p["dias"])

def redistribuir_reels():
    p = get_config_ig()
    redistribuir("reels", db_get("reels"), p["inicio"], p["fim"], p["dias"])

# ══════════════════════════════
# ENVIADOS (controle local)
# ══════════════════════════════
def get_enviados():
    if os.path.exists("enviados.json"):
        with open("enviados.json") as f:
            try: return json.load(f)
            except: return {}
    return {}

def marcar_enviado(chave):
    enviados = get_enviados()
    enviados[chave] = True
    with open("enviados.json", "w") as f:
        json.dump(enviados, f)

def ja_enviado(chave):
    return get_enviados().get(chave, False)

# ══════════════════════════════
# TELEGRAM — ENVIO
# ══════════════════════════════
def montar_legenda(nome, preco, link, frase):
    return f"🛒 *{nome}*\n\n💲 *Preço: R$ {preco}*\n\n{frase}\n\n👇 *Compre aqui:*\n{link}"

def enviar_produto(produto, frase):
    legenda = montar_legenda(produto["nome"], produto["preco"], produto["link"], frase)
    try:
        img = produto.get("imagem","")
        if img:
            r = req.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                json={"chat_id": GRUPO_ID, "photo": img, "caption": legenda, "parse_mode": "Markdown"}, timeout=15)
            if r.json().get("ok"): return
        req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": GRUPO_ID, "text": legenda, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e: print(f"❌ Produto TG: {e}")

def enviar_video(video, frase):
    legenda = montar_legenda(video["nome"], video["preco"], video["link"], frase)
    url = video.get("video","")
    try:
        if url:
            r = req.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo",
                json={"chat_id": GRUPO_ID, "video": url, "caption": legenda, "parse_mode": "Markdown"}, timeout=30)
            if r.json().get("ok"): return
        req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": GRUPO_ID, "text": legenda, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e: print(f"❌ Vídeo TG: {e}")

# ══════════════════════════════
# INSTAGRAM — TOKEN E ENVIO
# ══════════════════════════════
def get_ig_token():
    cfg = get_configs()
    tok = cfg.get("ig_access_token", {})
    if isinstance(tok, dict): return tok.get("token","")
    return str(tok) if tok else os.environ.get("IG_TOKEN","IGAAgguE5mWbxBZAGE5TzdnRHRuSENYcFBjcE56SE1KT2NEZA1NETldNbVNya0lrUk0yNmpnVjZAHaTQxWmtWbWVMa2JYaEZABZAnlESEIzRXpXN0l4ZAFBsMk10VW8tZA2FMQ2ZAmLTBjekRfY0JibXN5RGpmdWVja05hdUZA4WTFkdDBlUQZDZD")

def salvar_ig_token(token):
    salvar_config("ig_access_token", {"token": token, "at": datetime.now(BRASILIA).isoformat()})

def renovar_ig_token():
    token = get_ig_token()
    if not token: return
    try:
        r = req.get("https://graph.instagram.com/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=15)
        novo = r.json().get("access_token")
        if novo:
            salvar_ig_token(novo)
            print("✅ Token IG renovado!")
    except Exception as e: print(f"❌ Renovar token: {e}")

def postar_reel(video_url, legenda):
    token = get_ig_token()
    if not token: print("❌ Sem token IG"); return False
    try:
        # Cria container
        r1 = req.post(f"https://graph.instagram.com/v21.0/{IG_USER_ID}/media",
            params={"media_type":"REELS","video_url":video_url,"caption":legenda,"access_token":token}, timeout=30)
        container_id = r1.json().get("id")
        if not container_id: print(f"❌ Container IG: {r1.json()}"); return False

        # Aguarda processamento
        for _ in range(12):
            time.sleep(10)
            s = req.get(f"https://graph.instagram.com/v21.0/{container_id}",
                params={"fields":"status_code","access_token":token}, timeout=15).json()
            status = s.get("status_code","")
            if status == "FINISHED": break
            if status == "ERROR": print("❌ IG processamento falhou"); return False

        # Publica
        r2 = req.post(f"https://graph.instagram.com/v21.0/{IG_USER_ID}/media_publish",
            params={"creation_id":container_id,"access_token":token}, timeout=15)
        if r2.json().get("id"):
            print(f"✅ Reel publicado!"); return True
        print(f"❌ Publicar: {r2.json()}"); return False
    except Exception as e: print(f"❌ Reel IG: {e}"); return False

# ══════════════════════════════
# BOT LOOPS
# ══════════════════════════════
def verificar_e_enviar(items, prefixo, func_enviar):
    """Loop genérico que verifica horários e envia"""
    global frase_idx
    agora     = datetime.now(BRASILIA)
    hora_str  = agora.strftime("%H:%M")
    hoje_dmm  = agora.strftime("%d/%m")
    hoje_ymd  = agora.strftime("%Y-%m-%d")

    for item in items:
        item_id  = str(item.get("id",""))
        horarios = item.get("horarios",[])
        if isinstance(horarios, str):
            try: horarios = json.loads(horarios)
            except: horarios = []

        for h in horarios:
            h = str(h).strip()
            if " " in h:
                partes = h.split(" ")
                deve = (partes[0] == hoje_dmm and partes[1] == hora_str)
            else:
                deve = (h == hora_str)

            chave = f"{prefixo}_{item_id}_{hoje_ymd}_{h}"
            if deve and not ja_enviado(chave):
                frase = FRASES[frase_idx % len(FRASES)]
                frase_idx += 1
                func_enviar(item, frase)
                marcar_enviado(chave)
                time.sleep(2)

def bot_loop():
    """Envia produtos e vídeos no Telegram"""
    while True:
        try:
            verificar_e_enviar(db_get("produtos"), "p", enviar_produto)
            verificar_e_enviar(db_get("videos"),   "v", enviar_video)

            # Reinicia ciclo se passou do último horário
            agora = datetime.now(BRASILIA)
            todos = db_get("produtos") + db_get("videos")
            ultimas = []
            for item in todos:
                hs = item.get("horarios",[])
                if isinstance(hs, str):
                    try: hs = json.loads(hs)
                    except: hs = []
                ultimas.extend([str(h) for h in hs])

            if ultimas:
                ultima = sorted(ultimas)[-1]
                if " " in ultima:
                    d, h = ultima.split(" ")
                    dia = int(d.split("/")[0])
                    if agora.day > dia or (agora.day == dia and agora.strftime("%H:%M") > h):
                        print("🔄 Ciclo TG completo! Reiniciando...")
                        redistribuir_produtos()
                        redistribuir_videos()

        except Exception as e: print(f"❌ bot_loop: {e}")
        time.sleep(60)

def reels_loop():
    """Envia Reels no Instagram"""
    while True:
        try:
            agora    = datetime.now(BRASILIA)
            hora_str = agora.strftime("%H:%M")
            hoje_dmm = agora.strftime("%d/%m")
            hoje_ymd = agora.strftime("%Y-%m-%d")

            reels = db_get("reels")
            if not reels:
                time.sleep(60); continue

            for reel in reels:
                rid = str(reel.get("id",""))
                hs  = reel.get("horarios",[])
                if isinstance(hs, str):
                    try: hs = json.loads(hs)
                    except: hs = []

                for h in hs:
                    h = str(h).strip()
                    if " " in h:
                        partes = h.split(" ")
                        deve = (partes[0] == hoje_dmm and partes[1] == hora_str)
                    else:
                        deve = (h == hora_str)

                    chave = f"reel_{rid}_{hoje_ymd}_{h}"
                    if deve and not ja_enviado(chave):
                        url  = reel.get("video","")
                        nome = reel.get("nome","")
                        preco= reel.get("preco","")
                        link = reel.get("link","")
                        if url:
                            legenda = (f"🔥 {nome}\n\n💰 Por apenas R$ {preco}\n\n"
                                      f"🛒 Link na bio:\n{link}\n\n"
                                      f"#achadinhos #shopee #oferta #promoção")
                            ok = postar_reel(url, legenda)
                        else:
                            ok = True  # sem vídeo, pula
                        if ok:
                            marcar_enviado(chave)

            # Reinicia ciclo reels
            ultimas = []
            for r in reels:
                hs = r.get("horarios",[])
                if isinstance(hs, str):
                    try: hs = json.loads(hs)
                    except: hs = []
                ultimas.extend([str(h) for h in hs])

            if ultimas:
                ultima = sorted(ultimas)[-1]
                if " " in ultima:
                    d, h = ultima.split(" ")
                    dia = int(d.split("/")[0])
                    if agora.day > dia or (agora.day == dia and hora_str > h):
                        print("🔄 Ciclo Reels completo! Reiniciando...")
                        redistribuir_reels()

        except Exception as e: print(f"❌ reels_loop: {e}")
        time.sleep(60)

def ping_loop():
    while True:
        try: req.get(APP_URL+"/ping", timeout=10)
        except: pass
        time.sleep(600)

def ig_token_loop():
    while True:
        time.sleep(50 * 24 * 3600)
        renovar_ig_token()

# ══════════════════════════════
# BOAS VINDAS + COMANDOS
# ══════════════════════════════
MSGS_BV = [
    "Oi, {nome}! 👋 Que bom ter você aqui no *ACHADINHOS DA CASA*! 🛍️\n\nPrepara o bolso porque vêm muitas ofertas incríveis por aí! 🔥",
    "Seja bem-vindo(a), {nome}! 🎉\n\nVocê chegou no lugar certo! Aqui garimpamos os melhores produtos da Shopee todo dia! 💰",
    "Olá, {nome}! 😊\n\nBem-vindo(a) ao *ACHADINHOS DA CASA*! Os preços aqui são de cair o queixo! 😱🛒",
    "{nome}, que ótimo ter você aqui! 🙌\n\nSó divulgamos o que realmente vale a pena. Aproveita! ✅",
    "Boa vinda, {nome}! 🏠✨\n\nVocê entrou no grupo de ofertas mais quente do Telegram! 💸🔥",
    "Ei, {nome}! 👀\n\nSeja bem-vindo(a)! Aqui você vai encontrar o produto que procura pelo preço que não acredita! 🎯",
    "Olá, {nome}! 🌟\n\nQue bom que chegou! Tem oferta boa todo dia. Ativa as notificações! 🔔",
    "Bem-vindo(a), {nome}! 🛍️❤️\n\nAqui é família! Compartilha com seus amigos, todo mundo merece economizar! 😄",
]
bv_idx = [0]

def enviar_boas_vindas(nome):
    msg = MSGS_BV[bv_idx[0] % len(MSGS_BV)].format(nome=nome)
    bv_idx[0] += 1
    try:
        req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": GRUPO_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except: pass

def commands_loop():
    ultimo_id = [0]
    while True:
        try:
            r = req.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": ultimo_id[0]+1, "timeout": 10,
                        "allowed_updates": ["message","chat_member"]}, timeout=15)
            for upd in r.json().get("result",[]):
                ultimo_id[0] = upd["update_id"]

                # Boas vindas
                novo = upd.get("chat_member",{}).get("new_chat_member",{})
                if novo.get("status") == "member":
                    enviar_boas_vindas(novo.get("user",{}).get("first_name","amigo(a)"))

                # Comandos
                msg    = upd.get("message",{})
                texto  = msg.get("text","")
                chat_id= msg.get("chat",{}).get("id")
                if not chat_id: continue

                if texto.startswith("/start"):
                    req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        json={"chat_id": chat_id,
                              "text": "👋 Bem-vindo ao *ACHADINHOS DA CASA*!\n\n🛍️ Aqui você recebe as melhores ofertas da Shopee todo dia!\n\n📌 Comandos:\n/ofertas — Ver ofertas de hoje",
                              "parse_mode": "Markdown"}, timeout=15)

                elif texto.startswith("/ofertas"):
                    produtos = db_get("produtos")
                    if not produtos:
                        req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": "😅 Nenhum produto ainda!"}, timeout=10)
                    else:
                        import random
                        sel = random.sample(produtos, min(5, len(produtos)))
                        txt = "🛍️ *Ofertas de Hoje!*\n\n"
                        for p in sel:
                            txt += f"▪️ *{p['nome']}*\n💰 R$ {p['preco']}\n🔗 {p['link']}\n\n"
                        req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": txt, "parse_mode": "Markdown"}, timeout=15)

        except Exception as e: print(f"❌ commands_loop: {e}")
        time.sleep(5)

def relatorio_semanal_loop():
    while True:
        try:
            agora = datetime.now(BRASILIA)
            if agora.weekday() == 0 and agora.strftime("%H:%M") == "09:00":
                produtos = db_get("produtos")
                videos   = db_get("videos")
                reels    = db_get("reels")
                cats = {}
                for p in produtos:
                    c = p.get("categoria","Outros")
                    cats[c] = cats.get(c,0)+1
                cat_txt = "\n".join([f"  • {c}: {n}" for c,n in sorted(cats.items(),key=lambda x:x[1],reverse=True)[:5]])
                msg = (f"📊 *Relatório Semanal — ACHADINHOS DA CASA*\n\n"
                       f"📦 Produtos: *{len(produtos)}*\n"
                       f"🎬 Vídeos TG: *{len(videos)}*\n"
                       f"📸 Reels IG: *{len(reels)}*\n\n"
                       f"🏆 *Top categorias:*\n{cat_txt}\n\n"
                       f"✅ Sistema funcionando!\n🔗 {APP_URL}")
                req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    json={"chat_id": GRUPO_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
                print("📊 Relatório enviado!")
                time.sleep(70)
        except Exception as e: print(f"❌ relatorio: {e}")
        time.sleep(60)

# ══════════════════════════════
# ROTAS — PÁGINAS
# ══════════════════════════════
@app.route("/")
def painel(): return send_file("painel.html")

@app.route("/loja")
def loja(): return send_file("index.html")

@app.route("/ping")
def ping(): return "pong", 200

# ══════════════════════════════
# ROTAS — AUTH
# ══════════════════════════════
@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    if d.get("senha") == SENHA: return jsonify({"ok": True})
    return jsonify({"ok": False}), 401

# ══════════════════════════════
# ROTAS — PRODUTOS
# ══════════════════════════════
@app.route("/api/produtos", methods=["GET"])
def api_get_produtos(): return jsonify(db_get("produtos"))

@app.route("/api/produtos", methods=["POST"])
def api_add_produto():
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    cat = d.get("categoria") or detectar_categoria(d.get("nome",""))
    item = {"id": int(datetime.now(BRASILIA).timestamp()*1000),
            "nome": d.get("nome",""), "preco": d.get("preco",""),
            "link": d.get("link",""), "imagem": d.get("imagem",""),
            "categoria": cat, "horarios": []}
    db_post("produtos", item)
    redistribuir_produtos()
    return jsonify({"ok": True})

@app.route("/api/produtos/<int:pid>", methods=["PATCH"])
def api_edit_produto(pid):
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    campos = {k:v for k,v in d.items() if k in ["nome","preco","link","imagem","categoria","horarios"]}
    db_patch("produtos", f"id=eq.{pid}", campos)
    return jsonify({"ok": True})

@app.route("/api/produtos/<int:pid>", methods=["DELETE"])
def api_del_produto(pid):
    if request.args.get("senha") != SENHA: return jsonify({"ok":False}),401
    db_delete("produtos", f"id=eq.{pid}")
    return jsonify({"ok": True})

# ══════════════════════════════
# ROTAS — VÍDEOS (Telegram)
# ══════════════════════════════
@app.route("/api/videos", methods=["GET"])
def api_get_videos(): return jsonify(db_get("videos"))

@app.route("/api/videos", methods=["POST"])
def api_add_video():
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    cat = d.get("categoria") or detectar_categoria(d.get("nome",""))
    item = {"id": int(datetime.now(BRASILIA).timestamp()*1000),
            "nome": d.get("nome",""), "preco": d.get("preco",""),
            "link": d.get("link",""), "video": d.get("video",""),
            "categoria": cat, "horarios": []}
    db_post("videos", item)
    time.sleep(1)
    redistribuir_videos()
    return jsonify({"ok": True})

@app.route("/api/videos/<int:vid>", methods=["PATCH"])
def api_edit_video(vid):
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    campos = {k:v for k,v in d.items() if k in ["nome","preco","link","video","categoria","horarios"]}
    db_patch("videos", f"id=eq.{vid}", campos)
    return jsonify({"ok": True})

@app.route("/api/videos/<int:vid>", methods=["DELETE"])
def api_del_video(vid):
    if request.args.get("senha") != SENHA: return jsonify({"ok":False}),401
    db_delete("videos", f"id=eq.{vid}")
    return jsonify({"ok": True})

# ══════════════════════════════
# ROTAS — REELS (Instagram)
# ══════════════════════════════
@app.route("/api/reels", methods=["GET"])
def api_get_reels(): return jsonify(db_get("reels"))

@app.route("/api/reels", methods=["POST"])
def api_add_reel():
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    cat = d.get("categoria") or detectar_categoria(d.get("nome",""))
    item = {"id": int(datetime.now(BRASILIA).timestamp()*1000),
            "nome": d.get("nome",""), "preco": d.get("preco",""),
            "link": d.get("link",""), "video": d.get("video",""),
            "categoria": cat, "horarios": []}
    db_post("reels", item)
    time.sleep(1)
    redistribuir_reels()
    return jsonify({"ok": True})

@app.route("/api/reels/<int:rid>", methods=["PATCH"])
def api_edit_reel(rid):
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    campos = {k:v for k,v in d.items() if k in ["nome","preco","link","video","categoria","horarios"]}
    db_patch("reels", f"id=eq.{rid}", campos)
    return jsonify({"ok": True})

@app.route("/api/reels/<int:rid>", methods=["DELETE"])
def api_del_reel(rid):
    if request.args.get("senha") != SENHA: return jsonify({"ok":False}),401
    db_delete("reels", f"id=eq.{rid}")
    return jsonify({"ok": True})

# ══════════════════════════════
# ROTAS — CATEGORIAS
# ══════════════════════════════
@app.route("/api/categorias", methods=["GET"])
def api_get_cats(): return jsonify(get_categorias())

@app.route("/api/categorias", methods=["POST"])
def api_add_cat():
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    pals = [p.strip().lower() for p in d.get("palavras_chave",[]) if isinstance(d.get("palavras_chave",[]),list)]
    cat = {"id": int(datetime.now(BRASILIA).timestamp()*1000),
           "nome": d.get("nome",""), "emoji": d.get("emoji","📦"),
           "palavras_chave": pals}
    db_post("categorias", cat)
    return jsonify({"ok": True})

@app.route("/api/categorias/<int:cid>", methods=["DELETE"])
def api_del_cat(cid):
    if request.args.get("senha") != SENHA: return jsonify({"ok":False}),401
    db_delete("categorias", f"id=eq.{cid}")
    return jsonify({"ok": True})

# ══════════════════════════════
# ROTAS — CONFIGURAÇÕES
# ══════════════════════════════
@app.route("/api/configuracoes", methods=["GET"])
def api_get_configs(): return jsonify(get_configs())

@app.route("/api/configuracoes", methods=["POST"])
def api_save_configs():
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401

    periodo   = d.get("periodo",   {"inicio":"08:00","fim":"22:00","dias":7})
    ig_config = d.get("ig_config", {"inicio":"08:00","fim":"22:00","dias":7})

    salvar_config("periodo",   periodo)
    salvar_config("ig_config", ig_config)
    print(f"✅ Config TG: {periodo}")
    print(f"✅ Config IG: {ig_config}")

    redistribuir_produtos()
    redistribuir_videos()
    redistribuir_reels()
    return jsonify({"ok": True})

# ══════════════════════════════
# ROTAS — REDISTRIBUIR
# ══════════════════════════════
@app.route("/api/redistribuir", methods=["POST"])
def api_redistribuir():
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    redistribuir_produtos()
    redistribuir_videos()
    return jsonify({"ok": True})

@app.route("/api/redistribuir/reels", methods=["POST"])
def api_redistribuir_reels():
    d = request.json
    if d.get("senha") != SENHA: return jsonify({"ok":False}),401
    redistribuir_reels()
    return jsonify({"ok": True})

# ══════════════════════════════
# ROTAS — ANALYTICS
# ══════════════════════════════
@app.route("/api/click", methods=["POST"])
def api_click():
    d = request.json
    click = {"id": int(datetime.now(BRASILIA).timestamp()*1000),
             "produto_id": d.get("produto_id"),
             "produto_nome": d.get("nome",""),
             "categoria": d.get("categoria",""),
             "timestamp": datetime.now(BRASILIA).isoformat()}
    db_post("clicks", click)
    return jsonify({"ok": True})

@app.route("/api/analytics", methods=["GET"])
def api_analytics():
    clicks = db_get("clicks", "&order=timestamp.desc&limit=500")
    por_p, por_c = {}, {}
    for c in clicks:
        n = c.get("produto_nome",""); cat = c.get("categoria","")
        por_p[n] = por_p.get(n,0)+1
        por_c[cat] = por_c.get(cat,0)+1
    return jsonify({
        "total": len(clicks),
        "por_produto":   sorted(por_p.items(), key=lambda x:x[1], reverse=True)[:10],
        "por_categoria": sorted(por_c.items(), key=lambda x:x[1], reverse=True)
    })

# ══════════════════════════════
# ROTAS — INSTAGRAM STATUS
# ══════════════════════════════
@app.route("/api/ig/status", methods=["GET"])
def api_ig_status():
    token = get_ig_token()
    if not token: return jsonify({"ok":False,"erro":"Token não encontrado"})
    try:
        r = req.get(f"https://graph.instagram.com/v21.0/me",
            params={"fields":"id,username","access_token":token}, timeout=10)
        d = r.json()
        if d.get("id"): return jsonify({"ok":True,"username":d.get("username","")})
        return jsonify({"ok":False,"erro":d.get("error",{}).get("message","Token inválido")})
    except Exception as e: return jsonify({"ok":False,"erro":str(e)})

# ══════════════════════════════
# INICIAR
# ══════════════════════════════
def iniciar_threads():
    threading.Thread(target=bot_loop,              daemon=True).start()
    threading.Thread(target=reels_loop,            daemon=True).start()
    threading.Thread(target=ping_loop,             daemon=True).start()
    threading.Thread(target=commands_loop,         daemon=True).start()
    threading.Thread(target=relatorio_semanal_loop,daemon=True).start()
    threading.Thread(target=ig_token_loop,         daemon=True).start()
    # Salva token inicial se não existir
    try:
        if not get_ig_token():
            salvar_ig_token("IGAAgguE5mWbxBZAGE5TzdnRHRuSENYcFBjcE56SE1KT2NEZA1NETldNbVNya0lrUk0yNmpnVjZAHaTQxWmtWbWVMa2JYaEZABZAnlESEIzRXpXN0l4ZAFBsMk10VW8tZA2FMQ2ZAmLTBjekRfY0JibXN5RGpmdWVja05hdUZA4WTFkdDBlUQZDZD")
    except: pass
    print("🤖 Bot Achadinhos iniciado!")

if os.environ.get("BOT_WORKER") == "true":
    iniciar_threads()

if __name__ == "__main__":
    os.environ["BOT_WORKER"] = "true"
    iniciar_threads()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
