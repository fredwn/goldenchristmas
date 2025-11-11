# ===============================
# PRELUDE GOLDEN CHRISTMAS 2025
# main.py — versão com Supabase (busca exata e sem duplicatas)
# ===============================

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import os
import re
import requests
import logging

# --- CONFIGURAÇÕES GERAIS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="Prelude Golden Christmas 2025")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- SUPABASE CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = "cadastros"

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.warning("⚠️ Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas.")
else:
    logging.info(f"🔗 Conectando ao Supabase: {SUPABASE_URL}")

HEADERS = {
    "apikey": SUPABASE_KEY or "",
    "Authorization": f"Bearer {SUPABASE_KEY or ''}",
    "Content-Type": "application/json",
}

DB_PATH = os.path.join(BASE_DIR, "backup_database.csv")


# ============================================================
# 📱 FUNÇÃO DE NORMALIZAÇÃO DE TELEFONE
# ============================================================
def normalizar_telefone(numero: str) -> str:
    """Normaliza números de telefone para formato padrão (5521XXXXXXXX)."""
    if not numero:
        return ""
    numero = re.sub(r"\D", "", numero)
    numero = numero.lstrip("0")
    if not numero.startswith("55"):
        if numero.startswith("21"):
            numero = "55" + numero
        elif len(numero) == 11:
            numero = "55" + numero
    return numero


# ============================================================
# 💾 BACKUP LOCAL
# ============================================================
def salvar_backup_local(registro: dict) -> None:
    try:
        df = pd.DataFrame([registro])
        if os.path.exists(DB_PATH):
            df.to_csv(DB_PATH, mode="a", index=False, header=False)
        else:
            df.to_csv(DB_PATH, index=False)
        logging.info(f"💾 Backup local salvo: {registro['email']}")
    except Exception as e:
        logging.error(f"Erro ao salvar backup local: {e}")


# ============================================================
# 🔍 BUSCA NO SUPABASE
# ============================================================
def buscar_supabase(email: str, whatsapp: str):
    """Busca registro existente por e-mail OU WhatsApp."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    email = (email or "").strip().lower()
    whatsapp = normalizar_telefone(whatsapp)

    try:
        # Busca exata por e-mail (sem codificação de %25)
        query_email = f"?email=eq.{email}&select=*"
        url_email = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}{query_email}"
        r1 = requests.get(url_email, headers=HEADERS, timeout=10)
        logging.info(f"🔍 Busca por e-mail → {url_email} → {r1.status_code}")
        if r1.ok and r1.json():
            logging.info(f"✅ Registro encontrado via e-mail: {r1.json()[0]}")
            return r1.json()[0]

        # Busca exata por WhatsApp
        if whatsapp:
            query_whatsapp = f"?whatsapp=eq.{whatsapp}&select=*"
            url_whatsapp = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}{query_whatsapp}"
            r2 = requests.get(url_whatsapp, headers=HEADERS, timeout=10)
            logging.info(f"🔍 Busca por WhatsApp → {url_whatsapp} → {r2.status_code}")
            if r2.ok and r2.json():
                logging.info(f"✅ Registro encontrado via WhatsApp: {r2.json()[0]}")
                return r2.json()[0]

        logging.info("⚠️ Nenhum registro correspondente encontrado (email/whatsapp).")
        return None

    except Exception as e:
        logging.error(f"Erro na busca Supabase: {e}")
        return None


# ============================================================
# 💾 SALVAMENTO NO SUPABASE
# ============================================================
def salvar_supabase(registro: dict) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.warning("⚠️ Supabase não configurado, pulando upload remoto.")
        return
    try:
        url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
        response = requests.post(url, headers=HEADERS, json=registro, timeout=10)
        logging.info(f"Resposta Supabase: {response.status_code} — {response.text}")
        if response.status_code in (200, 201):
            logging.info(f"✅ Registro salvo: {registro['email']} ({registro['status']})")
        else:
            logging.error(f"❌ Erro Supabase: {response.status_code} — {response.text}")
    except Exception as e:
        logging.error(f"⚠️ Falha ao conectar com Supabase: {e}")


# ============================================================
# 🧠 FUNÇÃO PRINCIPAL
# ============================================================
def get_status(email: str, whatsapp: str) -> str:
    registro = buscar_supabase(email, whatsapp)
    if registro:
        status = registro.get("status", "restrito")
        logging.info(f"✅ Registro identificado: {registro}")
        return status
    return "restrito"


# ============================================================
# 🌐 ROTAS FASTAPI
# ============================================================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/verificar", response_class=HTMLResponse)
async def verificar(request: Request, email: str = Form(...), whatsapp: str = Form("")):
    email = (email or "").strip().lower()
    whatsapp = normalizar_telefone(whatsapp)
    timestamp = datetime.now().isoformat()

    existente = buscar_supabase(email, whatsapp)

    if existente:
        status = existente.get("status", "restrito")
        logging.info(f"⚠️ Registro existente, não será duplicado: {email} ({status})")
    else:
        status = "restrito"
        registro = {
            "email": email,
            "whatsapp": whatsapp,
            "status": status,
            "apelido": None,
            "conhecido_como": None,
            "quem_indicou": None,
            "convites_disponiveis": 0,
            "created_at": timestamp,
        }
        salvar_backup_local(registro)
        salvar_supabase(registro)
        logging.info(f"🆕 Novo registro criado: {email} ({status})")

    redirect_map = {"sócio": "/founder", "convidado": "/guest", "restrito": "/restrito"}
    return RedirectResponse(url=redirect_map.get(status, "/restrito"), status_code=303)


@app.get("/founder", response_class=HTMLResponse)
def founder_page(request: Request):
    return templates.TemplateResponse("founder.html", {"request": request})


@app.get("/guest", response_class=HTMLResponse)
def guest_page(request: Request):
    return templates.TemplateResponse("guest.html", {"request": request})


@app.get("/restrito", response_class=HTMLResponse)
def restrito_page(request: Request):
    return templates.TemplateResponse("restrito.html", {"request": request})


@app.get("/optout", response_class=HTMLResponse)
def optout(request: Request):
    mensagem = (
        "Entendido. Nenhuma informação foi registrada.<br>"
        "A Prelude agradece o interesse — talvez em outra edição.<br>✨ Obrigado."
    )
    return templates.TemplateResponse("index.html", {"request": request, "mensagem": mensagem})


# ============================================================
# 🚀 EXECUÇÃO LOCAL
# ============================================================
if __name__ == "__main__":
    import uvicorn
    logging.info("🚀 Servidor iniciado em http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
