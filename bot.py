import requests
import time
import json
import os

# ========== CONFIGURAÇÕES ==========
TOKEN = "8660560171:AAHW5OcfhgnpGDaoXeadaSnf2NGLadIFh64"
GRUPO_ID = "-5116230681"
SHEET_ID = "1cpcad2wshKq1ol5mWQgHjZBF7h-gC5h7kX3EbYUVjAw"
INTERVALO_HORAS = 1  # Envia a cada 1 hora

# Frases chamativas para alternar
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

# Arquivo para salvar o índice atual
INDEX_FILE = "index.json"

def get_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            data = json.load(f)
            return data.get("index", 0), data.get("frase_index", 0)
    return 0, 0

def save_index(index, frase_index):
    with open(INDEX_FILE, "w") as f:
        json.dump({"index": index, "frase_index": frase_index}, f)

def get_produtos():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json"
    try:
        response = requests.get(url, timeout=10)
        text = response.text
        # Remove o prefixo que o Google adiciona
        text = text[text.index("(") + 1:text.rindex(")")]
        data = json.loads(text)
        rows = data["table"]["rows"]
        produtos = []
        for row in rows[1:]:  # Pula o cabeçalho
            cells = row.get("c", [])
            if len(cells) >= 4 and cells[0] and cells[0].get("v"):
                produto = {
                    "nome": cells[0]["v"] if cells[0] else "",
                    "preco": cells[1]["v"] if cells[1] else "",
                    "link": cells[2]["v"] if cells[2] else "",
                    "imagem": cells[3]["v"] if cells[3] else "",
                }
                produtos.append(produto)
        return produtos
    except Exception as e:
        print(f"Erro ao buscar planilha: {e}")
        return []

def enviar_produto(produto, frase):
    nome = produto["nome"]
    preco = produto["preco"]
    link = produto["link"]
    imagem = produto["imagem"]

    legenda = (
        f"🛒 *{nome}*\n\n"
        f"💲 *Preço: R$ {preco}*\n\n"
        f"{frase}\n\n"
        f"👇 *Compre aqui:*\n{link}"
    )

    try:
        # Tenta enviar com imagem
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        payload = {
            "chat_id": GRUPO_ID,
            "photo": imagem,
            "caption": legenda,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=15)
        result = response.json()

        if not result.get("ok"):
            # Se falhar com imagem, envia só o texto
            print(f"Erro com imagem, enviando só texto: {result}")
            url2 = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload2 = {
                "chat_id": GRUPO_ID,
                "text": legenda,
                "parse_mode": "Markdown"
            }
            requests.post(url2, json=payload2, timeout=15)
        else:
            print(f"✅ Produto enviado: {nome}")

    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def main():
    print("🤖 Bot iniciado! Aguardando para enviar produtos...")

    while True:
        produtos = get_produtos()

        if not produtos:
            print("⚠️ Nenhum produto encontrado na planilha. Verifique se há dados cadastrados.")
        else:
            index, frase_index = get_index()

            # Volta ao início se chegou no fim da lista
            if index >= len(produtos):
                index = 0

            produto = produtos[index]
            frase = FRASES[frase_index % len(FRASES)]

            enviar_produto(produto, frase)

            # Salva os próximos índices
            save_index(index + 1, frase_index + 1)

        # Aguarda o intervalo definido
        print(f"⏳ Próximo envio em {INTERVALO_HORAS} hora(s)...")
        time.sleep(INTERVALO_HORAS * 3600)

if __name__ == "__main__":
    main()
