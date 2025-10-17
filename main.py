# ===============================
# PRELUDE GOLDEN CHRISTMAS 2025
# main.py — versão refinada
# ===============================

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import pandas as pd
import os
import re
import requests

# --- CONFIGURAÇÕES INICIAIS ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vcorazrqkpuacpaverbl.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZjb3JhenJxa3B1YWNwYXZlcmJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA2MjgzODAsImV4cCI6MjA3NjIwNDM4MH0.Ql1swf-RE97yA8ntxjt-KyBxEcpikpcowD_tDAeGoqA")
SUPABASE_TABLE = "cadastros"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# --- BACKUP LOCAL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "backup_database.csv")

def salvar_backup_local(novo_registro):
    """Garante backup local de todos os cadastros."""
    if not os.path.exists(DB_PATH):
        df = pd.DataFrame(columns=["email", "whatsapp", "status", "timestamp"])
    else:
        df = pd.read_csv(DB_PATH)

    df = pd.concat([df, pd.DataFrame([novo_registro])], ignore_index=True)
    df.to_csv(DB_PATH, index=False)

# --- FUNÇÃO PRINCIPAL DE STATUS ---
def get_status(email: str, whatsapp: str):
    """Verifica o status da pessoa (Founder, Guest, Restrito)."""

    # Normaliza dados
    email = email.lower().strip()
    whatsapp = re.sub(r"^(\+55|55|5521|21)", "", whatsapp or "").strip()

    # 1. Busca no Supabase
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?email=eq.{email}&select=status",
            headers=HEADERS,
        )
        if r.ok and r.json():
            status = r.json()[0].get("status")
            if status in ["Founder", "Guest"]:
                return status
    except Exception as e:
        print("Erro Supabase:", e)

    # 2. Fallback local
    founders = [
        "fredwn@gmail.com",
        "tiago78@gmail.com",
        "camendoncaa@gmail.com",
    ]
    guests = [
        "fred@studioweissmann.com.br",
        "tiago@oficinapar.com.br",
        "tiago@tiagofreire.arq.br",
        "eucamendonca@gmail.com",
    ]

    if email in founders:
        return "Founder"
    elif email in guests:
        return "Guest"
    else:
        return "Restrito"

# --- ROTAS ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/verificar", response_class=HTMLResponse)
async def verificar(request: Request, email: str = Form(...), whatsapp: str = Form("")):
    """Processa a verificação de status e redireciona para página correspondente."""

    email = email.lower().strip()
    whatsapp = re.sub(r"^(\+55|55|5521|21)", "", whatsapp or "").strip()

    status = get_status(email, whatsapp)

    # Salva backup local
    salvar_backup_local({
        "email": email,
        "whatsapp": whatsapp,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    })

    # Redireciona para página específica
    if status == "Founder":
        return RedirectResponse(url="/founder", status_code=303)
    elif status == "Guest":
        return RedirectResponse(url="/guest", status_code=303)
    else:
        return RedirectResponse(url="/restrito", status_code=303)


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
        "Entendido. Nenhuma informação foi registrada.\n"
        "A Prelude agradece o interesse — talvez em outra edição.\n"
        "✨ Obrigado."
    )
    return templates.TemplateResponse("index.html", {"request": request, "mensagem": mensagem})


# --- TESTE LOCAL ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
