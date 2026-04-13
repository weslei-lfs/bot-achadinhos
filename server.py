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

CATS_PALAVRAS = {
    "Cozinha": ["frigideira","panela","faca","talheres","copo","prato","xicara","liquidificador","batedeira","airfryer","fritadeira","espremedor","descascador","tabua","forma","assadeira","grelha","coador","utensil","gadget","cozinha","caneca","chaleira","torradeira","cuba","cafeteira"],
    "Eletronicos": ["celular","fone","headphone","carregador","cabo","adaptador","tablet","notebook","computador","teclado","mouse","webcam","camera","smart","tv","led","bluetooth","wifi","usb","hdmi","speaker","caixa de som","relogio","smartwatch","drone"],
    "Casa": ["organizador","caixa","suporte","prateleira","cabide","gancho","ventilador","lampada","cortina","tapete","almofada","vaso","quadro","espelho","decoracao","casa","quarto","sala","banheiro","limpeza","vassoura","balde","ferro","torneira"],
    "Beleza": ["creme","perfume","maquiagem","escova","pente","secador","chapinha","massageador","saude","beleza","skincare","hidratante","protetor","batom","esmalte","shampoo","condicionador","serum"],
    "Calcados": ["tenis","sapato","sandalia","chinelo","bota","sapatilha","mocassim","calcado","solado","palmilha","nike","adidas","puma"],
    "Moda Feminina": ["vestido","blusa","saia","calca feminina","top","crop","conjunto feminino","lingerie","sutia","calcinha","pijama feminino","moda feminina","macacao","shorts feminino"],
    "Moda Masculina": ["camisa","camiseta","calca masculina","bermuda","shorts masculino","polo","moletom","jaqueta","casaco","terno","gravata","cueca","moda masculina","regata"],
    "Acessorios": ["pulseira","colar","brinco","anel","bolsa","carteira","mochila","cinto","oculos","chapeu","bone","tiara","joias","bijuteria","acessorio"],
    "Informatica": ["hd","ssd","pendrive","hub","impressora","scanner","roteador","switch","modem","memoria","processador","placa","monitor"],
    "Games": ["jogo","game","controle","joystick","headset gamer","mousepad","cadeira gamer","console","playstation","xbox","nintendo","gamer","rgb"],
    "Bebe": ["bebe","infantil","crianca","brinquedo","mamadeira","fraldas","carrinho","berco","chupeta","babador"],
    "Esporte": ["academia","exercicio","musculacao","yoga","corrida","bicicleta","esporte","fitness","treino","suplemento","haltere","corda"],
    "Pets": ["pet","cachorro","gato","aquario","racao","coleira","arranhador","comedouro"],
}

def detectar_categoria(nome):
    n = nome.lower()
    for cat, palavras in CATS_PALAVRAS.items():
        if any(p in n for p in palavras):
            return cat
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

def get_config():
    try:
        r = req.get(f"{SUPA_URL}/rest/v1/config?select=*", headers=SUPA_HEADERS, timeout=10)
        data = r.json() if r.ok else []
        return data[0] if data else {}
    except: return {}

def save_config(cfg):
    try:
        existing = get_config()
        if existing:
            req.patch(f"{SUPA_URL}/rest/v1/config?id=eq.{existing.get('id',1)}", headers=SUPA_HEADERS, json=cfg, timeout=10)
        else:
            cfg["id"] = 1
            req.post(f"{SUPA_URL}/rest/v1/config", headers=SUPA_HEADERS, json=cfg, timeout=10)
    except: pass

def get_enviados():
    if os.path.exists("enviados.json"):
        with open("enviados.json") as f: return json.load(f)
    return {}

def save_enviados(d):
    with open("enviados.json","w") as f: json.dump(d, f)

def redistribuir_produtos():
    cfg = get_config()
    produtos = get_produtos()
    if not produtos: return

    hora_inicio = int(cfg.get("hora_inicio", 7))
    hora_fim = int(cfg.get("hora_fim", 22))
    data_inicio_str = cfg.get("data_inicio", datetime.now(BRASILIA).strftime("%Y-%m-%d"))
    data_fim_str = cfg.get("data_fim", (datetime.now(BRASILIA) + timedelta(days=7)).strftime("%Y-%m-%d"))

    try:
        dt_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d")
        dt_fim = datetime.strptime(data_fim_str, "%Y-%m-%d")
        total_dias = max(1, (dt_fim - dt_inicio).days + 1)
    except:
        dt_inicio = datetime.now(BRASILIA)
        total_dias = 7

    minutos_por_dia = (hora_fim - hora_inicio) * 60
    total_minutos = total_dias * minutos_por_dia
    total_produtos = len(produtos)
    intervalo = max(30, total_minutos // total_produtos)

    for i, produto in enumerate(produtos):
        offset = i * intervalo
        dia_idx = offset // minutos_por_dia
        min_no_dia = offset % minutos_por_dia
        hora = hora_inicio + (min_no_dia // 60)
        minuto = min_no_dia % 60
        if hora >= hora_fim:
            hora = hora_inicio
            minuto = 0
        data = dt_inicio + timedelta(days=dia_idx)
        update_produto(produto["id"], {
            "horarios": [f"{hora:02d}:{minuto:02d}"],
            "data_envio": data.strftime("%Y-%m-%d")
        })
    print(f"Redistribuidos {total_produtos} produtos em {total_dias} dias")

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
            hoje = agora.strftime("%Y-%m-%d")
            produtos = get_produtos()
            videos = get_videos()
            enviados = get_enviados()

            for produto in produtos:
                pid = str(produto.get("id",""))
                horarios = produto.get("horarios",[])
                data_envio = produto.get("data_envio")
                if isinstance(horarios, str):
                    try: horarios = json.loads(horarios)
                    except: horarios = []
                for h in horarios:
                    chave = f"{pid}_{hoje}_{h}"
                    cond = (data_envio is None) or (data_envio == hoje)
                    if h == hora_str and cond and chave not in enviados:
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
                    chave = f"vid_{vid_id}_{hoje}_{h}"
                    if h == hora_str and chave not in enviados:
                        enviar_video_telegram(video, FRASES[frase_idx % len(FRASES)])
                        frase_idx += 1
                        enviados[chave] = True
                        save_enviados(enviados)
                        time.sleep(2)
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
