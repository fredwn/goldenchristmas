from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path
import os

# ==============================================================
# 🚀 Inicialização e leitura do .env
# ==============================================================

env_path = Path(__file__).resolve().parent / ".env"
print("🧠 Carregando variáveis de ambiente...")
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("✅ .env encontrado:", env_path.exists())
print("🔗 SUPABASE_URL =", SUPABASE_URL)
print("🔑 SUPABASE_KEY =", SUPABASE_KEY[:8] + "..." if SUPABASE_KEY else None)

# ==============================================================
# ⚙️ Conexão com o Supabase
# ==============================================================

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Conectado ao Supabase com sucesso.")
    except Exception as e:
        print("🚨 Erro ao conectar ao Supabase:", e)
else:
    print("⚠️ Variáveis SUPABASE_URL ou SUPABASE_KEY não definidas no .env")

# ==============================================================
# 🌐 Configuração do servidor FastAPI
# ==============================================================

app = FastAPI(title="Prelude Golden Christmas 2025 — Sistema de Convites")

# Arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# ==============================================================
# 🏠 Página inicial (index)
# ==============================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    html_path = templates_dir / "index.html"
    if not html_path.exists():
        return HTMLResponse(
            content=f"<h1>Arquivo não encontrado:</h1><p>{html_path}</p>",
            status_code=500
        )
    return templates.TemplateResponse("index.html", {"request": request})

# ==============================================================
# 🔍 Verificação de e-mail/whatsapp
# ==============================================================

@app.post("/verificar")
async def verificar(
    request: Request,
    email: str = Form(None),
    whatsapp: str = Form(None)
):
    if not supabase:
        return JSONResponse({"erro": "Serviço Supabase indisponível."}, status_code=503)

    query = supabase.table("cadastros")

    try:
        if email:
            result = query.select("*").ilike("email", f"%{email}%").execute()
        elif whatsapp:
            result = query.select("*").ilike("whatsapp", f"%{whatsapp}%").execute()
        else:
            return HTMLResponse("<h3>Informe seu e-mail ou WhatsApp.</h3>", status_code=400)

        data = result.data

        # 🚨 Redireciona para /restrito se não encontrar o registro
        if not data:
            print("⚠️ Nenhum registro encontrado — redirecionando para /restrito")
            return RedirectResponse(url="/restrito", status_code=303)

        pessoa = data[0]
        status = pessoa.get("status", "").lower()
        destino = "/socio" if status in ["socio", "sócio"] else "/convidado"

        html = f"""
        <script>
          localStorage.setItem("socio_id", "{pessoa['id']}");
          window.location.href = "{destino}";
        </script>
        """
        return HTMLResponse(content=html)

    except Exception as e:
        return HTMLResponse(f"<h3>Erro interno:</h3><pre>{e}</pre>", status_code=500)

# ==============================================================
# 🖥️ Página do sócio
# ==============================================================

@app.get("/socio", response_class=HTMLResponse)
async def socio_page(request: Request):
    html_path = templates_dir / "socio.html"
    if not html_path.exists():
        return HTMLResponse(
            content=f"<h1>Arquivo não encontrado:</h1><p>{html_path}</p>",
            status_code=500
        )
    return templates.TemplateResponse("socio.html", {"request": request})

# ==============================================================
# 🖥️ Página do convidado
# ==============================================================

@app.get("/convidado", response_class=HTMLResponse)
async def convidado_page(request: Request):
    html_path = templates_dir / "convidado.html"
    if not html_path.exists():
        return HTMLResponse(
            content=f"<h1>Arquivo não encontrado:</h1><p>{html_path}</p>",
            status_code=500
        )
    return templates.TemplateResponse("convidado.html", {"request": request})

# ==============================================================
# 🖥️ Página restrita
# ==============================================================

@app.get("/restrito", response_class=HTMLResponse)
async def restrito_page(request: Request):
    html_path = templates_dir / "restrito.html"
    if not html_path.exists():
        return HTMLResponse(
            content=f"<h1>Arquivo não encontrado:</h1><p>{html_path}</p>",
            status_code=500
        )
    return templates.TemplateResponse("restrito.html", {"request": request})

# ==============================================================
# 📡 Endpoint: buscar dados do sócio
# ==============================================================

@app.get("/api/socio/{id}")
async def get_socio(id: int):
    if not supabase:
        return JSONResponse({"erro": "Serviço Supabase indisponível."}, status_code=503)

    try:
        result = supabase.table("cadastros").select("*").eq("id", id).single().execute()
        if not result.data:
            return JSONResponse({"erro": "Sócio não encontrado"}, status_code=404)
        return result.data
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)

# ==============================================================
# 📩 Endpoint: cadastrar convidado e reduzir convites
# ==============================================================

@app.post("/api/convidar")
async def convidar_amigo(request: Request):
    if not supabase:
        return JSONResponse({"erro": "Serviço Supabase indisponível."}, status_code=503)

    data = await request.json()
    socio_id = data.get("quem_indicou")

    try:
        # 1️⃣ Buscar sócio
        socio_resp = supabase.table("cadastros").select("id, convites_disponiveis").eq("id", socio_id).single().execute()
        socio = socio_resp.data
        print("🎯 Sócio encontrado:", socio)

        if not socio:
            return JSONResponse({"erro": "Sócio não encontrado."}, status_code=404)

        convites_restantes = int(socio.get("convites_disponiveis") or 0)
        if convites_restantes <= 0:
            return JSONResponse({"erro": "Você já usou todos os convites disponíveis."}, status_code=400)

        # 2️⃣ Inserir convidado
        convidado = {
            "nome": data.get("nome"),
            "apelido": data.get("apelido"),
            "whatsapp": data.get("whatsapp"),
            "email": data.get("email"),
            "status": "convidado",
            "quem_indicou": socio_id
        }

        insert_resp = supabase.table("cadastros").insert(convidado).execute()
        print("✅ Convidado adicionado:", insert_resp.data)

        # 3️⃣ Atualizar convites disponíveis (com fallback)
        novo_total = convites_restantes - 1
        update_resp = supabase.table("cadastros") \
            .update({"convites_disponiveis": novo_total}) \
            .eq("id", socio_id).execute()
        print("📉 Resultado do update:", update_resp)

        # 4️⃣ Rechecar valor após o update
        check_resp = supabase.table("cadastros").select("convites_disponiveis").eq("id", socio_id).single().execute()
        novo_valor = int(check_resp.data.get("convites_disponiveis", convites_restantes))
        print("🔎 Valor após update:", novo_valor)

        # 5️⃣ Fallback de segurança (update forçado)
        if novo_valor == convites_restantes:
            print("⚠️ Fallback acionado — tentando update forçado")
            supabase.table("cadastros").update({"convites_disponiveis": convites_restantes - 1}).eq("id", socio_id).execute()
            check_resp = supabase.table("cadastros").select("convites_disponiveis").eq("id", socio_id).single().execute()
            novo_valor = int(check_resp.data.get("convites_disponiveis", convites_restantes))

        return JSONResponse({
            "ok": True,
            "mensagem": f"Convite registrado. Convites restantes: {novo_valor}",
            "convites_restantes": novo_valor
        })

    except Exception as e:
        print("🚨 Erro geral no convite:", e)
        return JSONResponse({"erro": f"Erro ao salvar convidado: {str(e)}"}, status_code=500)

# ==============================================================
# ✅ Mensagem de inicialização
# ==============================================================

@app.on_event("startup")
async def startup_event():
    print("🌟 Servidor Prelude Golden Christmas iniciado com sucesso.")
