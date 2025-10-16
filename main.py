from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import os
import requests
from datetime import datetime

# --------------------------------------------------------
# 🔐 Configurações de integração com Supabase
# --------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --------------------------------------------------------
# ⚙️ Inicialização do app e diretórios
# --------------------------------------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.csv")

# --------------------------------------------------------
# 📂 Funções auxiliares
# --------------------------------------------------------
def carregar_dados():
    """Carrega o CSV local, se existir, e normaliza campos"""
    if os.path.exists(DB_PATH):
        df = pd.read_csv(DB_PATH)
        df["email"] = df["email"].astype(str).str.lower().str.strip()
        df["whatsapp"] = df["whatsapp"].astype(str).str.strip()
        return df
    else:
        return pd.DataFrame(columns=["nome", "email", "whatsapp", "status", "convites_disponiveis"])

def salvar_local(dados):
    """Grava localmente no CSV"""
    df = carregar_dados()
    df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
    df.to_csv(DB_PATH, index=False)

def salvar_supabase(dados):
    """Envia o registro também para o Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ SUPABASE_URL ou SUPABASE_KEY não configurados. Pulando upload.")
        return
    try:
        url = f"{SUPABASE_URL}/rest/v1/cadastros"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        r = requests.post(url, headers=headers, json=dados)
        print(f"📤 Supabase -> {r.status_code}: {r.text}")
    except Exception as e:
        print("❌ Erro ao enviar para Supabase:", e)

# --------------------------------------------------------
# 🏠 Rotas
# --------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Renderiza a landing page inicial"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/verificar", response_class=HTMLResponse)
def verificar(request: Request, email: str = Form(""), whatsapp: str = Form("")):
    """Verifica status do email/whatsapp e salva se novo"""
    df = carregar_dados()
    email = email.lower().strip()
    whatsapp = whatsapp.strip()

    row = df[(df["email"] == email) | (df["whatsapp"] == whatsapp)]

    # Caso novo cadastro (não encontrado)
    if row.empty:
        novo = {
            "nome": "",
            "email": email,
            "whatsapp": whatsapp,
            "status": "Restrito",
            "convites_disponiveis": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        salvar_local(novo)
        salvar_supabase(novo)

        mensagem = (
            "⚪ No momento, os convites estão restritos.\n"
            "Caso um convidado o indique, você será notificado.\n"
            "Nenhuma venda pública será aberta.\n"
            "Agradecemos por deixar o seu nome."
        )
    else:
        convidado = row.iloc[0]
        nome = convidado["nome"]
        status = convidado["status"]

        if status == "Founder":
            mensagem = (
                f"✅ {nome}, você é Founder.\n"
                "O código e as instruções serão enviados pessoalmente por WhatsApp.\n"
                "Você pode indicar até 6 convidados."
            )
        elif status == "Guest":
            mensagem = (
                f"✅ {nome}, seu nome está confirmado.\n"
                "Convite nominal válido para você e seu acompanhante.\n"
                "Detalhes serão enviados por WhatsApp."
            )
        else:
            mensagem = (
                f"⚪ {nome}, os convites estão restritos.\n"
                "Caso um convidado o indique, você será notificado."
            )

    return templates.TemplateResponse("index.html", {"request": request, "mensagem": mensagem})

# --------------------------------------------------------
# 🔍 Endpoint opcional para administração (ver últimos cadastros)
# --------------------------------------------------------
@app.get("/admin/db")
def listar_registros():
    df = carregar_dados()
    return {
        "total_local": len(df),
        "amostra_local": df.tail(10).to_dict(orient="records")
    }