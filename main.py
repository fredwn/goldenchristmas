from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import os

app = FastAPI()

# Configurações de diretórios
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Garante caminho correto do CSV mesmo na nuvem
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.csv")

def carregar_dados():
    if os.path.exists(DB_PATH):
        df = pd.read_csv(DB_PATH)
        df["email"] = df["email"].astype(str).str.lower().str.strip()
        df["whatsapp"] = df["whatsapp"].astype(str).str.strip()
        return df
    else:
        return pd.DataFrame(columns=["nome", "email", "whatsapp", "status", "convites_disponiveis"])

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/verificar", response_class=HTMLResponse)
def verificar(request: Request, email: str = Form(""), whatsapp: str = Form("")):
    df = carregar_dados()
    email = email.lower().strip()
    whatsapp = whatsapp.strip()

    row = df[(df["email"] == email) | (df["whatsapp"] == whatsapp)]

    if row.empty:
        # Novo registro Restrito
        novo = pd.DataFrame([{
            "nome": "",
            "email": email,
            "whatsapp": whatsapp,
            "status": "Restrito",
            "convites_disponiveis": 0
        }])
        df = pd.concat([df, novo], ignore_index=True)
        df.to_csv(DB_PATH, index=False)
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
