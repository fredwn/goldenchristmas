from fastapi import FastAPI, Request
from supabase import create_client
import os
import requests
import re

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    entry = data.get("entry", [])[0]
    changes = entry.get("changes", [])[0]
    message = changes.get("value", {}).get("messages", [])[0]

    from_number = message["from"]
    text = message["text"]["body"]

    # procura números de telefone na mensagem
    numeros = re.findall(r"\+?\d{10,14}", text)
    if not numeros:
        return {"message": "sem números encontrados"}

    # checa se o remetente é founder
    founder = supabase.table("cadastros").select("*").eq("whatsapp", from_number).eq("status", "Founder").execute()
    if not founder.data:
        return {"message": "não é founder"}

    # salva cada indicação
    for numero in numeros:
        supabase.table("indicacoes").insert({
            "founder_whatsapp": from_number,
            "convidado_whatsapp": numero,
            "status": "pendente"
        }).execute()

        # envia convite ao convidado
        convite_texto = (
            "🎄 Prelude — Golden Christmas 2025\n\n"
            "Você foi indicado para o Natal da Prelude.\n"
            "Um espaço reservado para reencontros entre amigos.\n\n"
            "Confirme sua presença respondendo com seu nome completo.\n"
            "— Prelude"
        )
        enviar_whatsapp(numero, convite_texto)

    # atualiza contador
    supabase.rpc("decrementar_convites", {"founder": from_number}).execute()

    return {"message": "indicações processadas"}

def enviar_whatsapp(numero, texto):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    r = requests.post(url, headers=headers, json=payload)
    print("📤 Enviado:", numero, "->", r.status_code)
