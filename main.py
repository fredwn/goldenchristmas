from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import pandas as pd
import os
import requests

app = FastAPI()

# --- Configuração de diretórios ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Configuração Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vcorazrqkpuacpaverbl.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZjb3JhenJxa3B1YWNwYXZlcmJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA2MjgzODAsImV4cCI6MjA3NjIwNDM4MH0.Ql1swf-RE97yA8ntxjt-KyBxEcpikpcowD_tDAeGoqA")  # substitua pela sua
SUPABASE_TABLE = "cadastros"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# --- Backup local (garantia) ---
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


# --- Rotas ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/verificar", response_class=HTMLResponse)
def verificar(request: Request, email: str = Form(""), whatsapp: str = Form("")):
    email = email.lower().strip()
    whatsapp = whatsapp.strip().replace("+55", "").replace(" ", "").replace("-", "")

    data = {
        "email": email,
        "whatsapp": whatsapp,
        "status": "Restrito",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # --- Tenta enviar para Supabase ---
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
            headers=headers,
            json=data,
            timeout=5
        )
        if res.status_code not in [200, 201]:
            print(f"❌ Erro ao enviar para Supabase: {res.status_code} -> {res.text}")
    except Exception as e:
        print(f"❌ Erro Supabase: {e}")

    # --- Salva backup local ---
    salvar_backup_local(data)

    # --- Define mensagens conforme status ---
    status = verificar_status(email, whatsapp)

    if status == "Founder":
        mensagem = (
            "✅ Seu nome foi reconhecido.\n"
            "Acesso garantido ao nosso Natal — Golden Christmas.\n"
            "O código e as instruções serão enviados por e-mail.\n"
            "📅 Save the Date: 20 de Dezembro de 2025 — 20h\n"
            "Pela primeira vez, em um salão lendário.\n\n"
            '<a href="https://wa.me/5521976954450?text=Oi%20Fred!%20Sou%20Founder%20da%20Prelude%20Golden%20Christmas%20e%20quero%20indicar%20meus%20amigos." class="whatsapp-btn">Enviar mensagem pelo WhatsApp</a>'
        )
    elif status == "Guest":
        mensagem = (
            "✅ Seu nome está confirmado.\n"
            "Convite nominal válido para você e seu acompanhante.\n"
            "📅 Save the Date: 20 de Dezembro de 2025 — 20h\n"
            "Pela primeira vez, em um salão lendário.\n\n"
            '<a href="https://wa.me/5521976954450?text=Oi%20Fred!%20Sou%20Guest%20da%20Prelude%20Golden%20Christmas%20e%20quero%20confirmar%20meu%20acompanhante." class="whatsapp-btn">Enviar mensagem pelo WhatsApp</a>'
        )
    else:
        mensagem = (
            "⚪ No momento, os convites estão restritos.\n"
            "Caso um convidado o indique, você será notificado.\n"
            "Nenhuma venda pública será aberta.\n"
            '<div class="optout"><a href="/optout">❌ Remover meus dados</a></div>'
        )

    return templates.TemplateResponse("index.html", {"request": request, "mensagem": mensagem})


def verificar_status(email, whatsapp):
    """Simulação local de status (teste de UX)."""
    if email.endswith("@founder.com"):
        return "Founder"
    elif email.endswith("@guest.com"):
        return "Guest"
    else:
        return "Restrito"


@app.get("/optout", response_class=HTMLResponse)
def optout(request: Request):
    mensagem = (
        "Entendido. Nenhuma informação foi registrada.\n"
        "A Prelude agradece o interesse — talvez em outra edição.\n"
        "✨ Obrigado."
    )
    return templates.TemplateResponse("index.html", {"request": request, "mensagem": mensagem})
