# ===============================
# PRELUDE GOLDEN CHRISTMAS 2025
# main.py — versão otimizada
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
load_dotenv()  # carrega variáveis do .env
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="Prelude Golden Christmas 2025")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- SUPABASE CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = "cadastros"

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.warning("⚠️ Variáveis de ambiente SUPABASE_URL e SUPABASE_KEY não configuradas.")

HEADERS = {
    "apikey": SUPABASE_KEY or "",
    "Authorization": f"Bearer {SUPABASE_KEY or ''}",
    "Content-Type": "application/json",
}

# --- BACKUP LOCAL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "backup_database.csv")


def salvar_backup_local(registro: dict) -> None:
    """Salva o registro localmente como backup CSV (anexando nova linha)."""
    try:
        df = pd.DataFrame([registro])
        if os.path.exists(DB_PATH):
            df.to_csv(DB_PATH, mode="a", index=False, header=False)
        else:
            df.to_csv(DB_PATH, index=False)
    except Exception as e:
        logging.error(f"Erro ao salvar backup local: {e}")


# --- FUNÇÃO PRINCIPAL ---
def get_status(email: str, whatsapp: str) -> str:
    """Verifica o status da pessoa no Supabase (Founder, Guest, Restrito)."""
    email = email.lower().strip()
    whatsapp = re.sub(r"^(\+55|55|5521|21)", "", whatsapp or "").strip()

    # 1. Busca no Supabase
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?email=eq.{email}&select=status"
            r = requests.get(url, headers=HEADERS, timeout=5)
            if r.ok and r.json():
                status = r.json()[0].get("status")
                if status in {"Founder", "Guest"}:
                    return status
        except requests.exceptions.RequestException as e:
            logging.warning(f"Falha na conexão com o Supabase: {e}")

    # 2. Fallback local — emails de contingência
    founders = {
        "fredwn@gmail.com",
        "tiago78@gmail.com",
        "camendoncaa@gmail.com",
    }
    guests = {
        "fred@studioweissmann.com.br",
        "tiago@oficinapar.com.br",
        "tiago@tiagofreire.arq.br",
        "eucamendonca@gmail.com",
    }

    if email in founders:
        return "Founder"
    elif email in guests:
        return "Guest"
    return "Restrito"


# --- ROTAS ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Página inicial — formulário de verificação."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/verificar", response_class=HTMLResponse)
async def verificar(request: Request, email: str = Form(...), whatsapp: str = Form("")):
    """Processa o formulário e redireciona conforme status."""

    email = email.lower().strip()
    whatsapp = re.sub(r"^(\+55|55|5521|21)", "", whatsapp or "").strip()

    status = get_status(email, whatsapp)
    timestamp = datetime.now().isoformat()

    salvar_backup_local({
        "email": email,
        "whatsapp": whatsapp,
        "status": status,
        "timestamp": timestamp,
    })

    logging.info(f"Consulta — {email} ({status})")

    redirect_map = {
        "Founder": "/founder",
        "Guest": "/guest",
        "Restrito": "/restrito",
    }
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
    """Página de opt-out para exclusão voluntária."""
    mensagem = (
        "Entendido. Nenhuma informação foi registrada.<br>"
        "A Prelude agradece o interesse — talvez em outra edição.<br>✨ Obrigado."
    )
    return templates.TemplateResponse("index.html", {"request": request, "mensagem": mensagem})


# --- EXECUÇÃO LOCAL ---
if __name__ == "__main__":
    import uvicorn

    logging.info("🚀 Servidor iniciado em http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
