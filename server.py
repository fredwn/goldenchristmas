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

base_dir = Path(__file__).resolve().parent
env_path = base_dir / ".env"
print("🧠 Carregando variáveis de ambiente...", env_path)
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("✅ .env encontrado:", env_path.exists())
print("🔗 SUPABASE_URL =", SUPABASE_URL)
print("🔑 SUPABASE_KEY =", (SUPABASE_KEY[:8] + "...") if SUPABASE_KEY else None)

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

templates_dir = base_dir / "templates"
static_dir = base_dir / "static"
print("📂 templates_dir:", templates_dir.resolve())
print("📂 static_dir   :", static_dir.resolve())

try:
    app.mount("/static", StaticFiles(directory=str(static_dir), check_dir=False), name="static")
    if not static_dir.exists():
        print("⚠️ AVISO: pasta 'static/' não encontrada. O app sobe mesmo assim; arquivos estáticos retornarão 404.")
except Exception as e:
    print("🚨 Falha ao montar /static:", e)

templates = Jinja2Templates(directory=str(templates_dir.resolve()))

# ==============================================================
# 🏥 Health-check rápido
# ==============================================================

@app.get("/health", response_class=HTMLResponse)
async def health():
    return HTMLResponse("ok")

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
        # Busca o registro existente
        if email:
            result = query.select("*").ilike("email", f"%{email}%").execute()
        elif whatsapp:
            result = query.select("*").ilike("whatsapp", f"%{whatsapp}%").execute()
        else:
            return HTMLResponse("<h3>Informe seu e-mail ou WhatsApp.</h3>", status_code=400)

        data = result.data

        # 🚨 Se não existir: grava e salva ID no localStorage
        if not data:
            print("⚠️ Nenhum registro encontrado — criando novo")

            novo = {
                "email": email,
                "whatsapp": whatsapp,
                "status": "aguardando",
                "convites_disponiveis": 0
            }

            insert_resp = query.insert(novo).execute()
            pessoa = insert_resp.data[0]
            pessoa_id = pessoa["id"]

            html = f"""
            <script>
              localStorage.setItem("socio_id", "{pessoa_id}");
              localStorage.setItem("email", "{email or ''}");
              localStorage.setItem("whatsapp", "{whatsapp or ''}");
              window.location.href = "/restrito";
            </script>
            """
            return HTMLResponse(html)

        # Registro existe — redireciona com dados carregados
        pessoa = data[0]
        status = pessoa.get("status", "").lower()
        destino = "/socio" if status in ["socio", "sócio"] else "/convidado"

        html = f"""
        <script>
          localStorage.setItem("socio_id", "{pessoa['id']}");
          localStorage.setItem("email", "{pessoa.get('email','')}");
          localStorage.setItem("whatsapp", "{pessoa.get('whatsapp','')}");
          window.location.href = "{destino}";
        </script>
        """
        return HTMLResponse(content=html)

    except Exception as e:
        print("🚨 Erro interno no /verificar:", repr(e))
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
    print("🔎 GET /restrito ->", html_path.resolve(), "existe?", html_path.exists())
    if not html_path.exists():
        return HTMLResponse(
            content=f"<h1>Arquivo não encontrado:</h1><p>{html_path}</p>",
            status_code=500
        )
    try:
        return templates.TemplateResponse("restrito.html", {"request": request})
    except Exception as e:
        print("🚨 Erro ao renderizar restrito.html:", repr(e))
        return HTMLResponse(f"<h3>Erro ao renderizar restrito.html:</h3><pre>{e}</pre>", status_code=500)

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
        socio_resp = supabase.table("cadastros").select("id, convites_disponiveis").eq("id", socio_id).single().execute()
        socio = socio_resp.data
        print("🎯 Sócio encontrado:", socio)

        if not socio:
            return JSONResponse({"erro": "Sócio não encontrado."}, status_code=404)

        convites_restantes = int(socio.get("convites_disponiveis") or 0)
        if convites_restantes <= 0:
            return JSONResponse({"erro": "Você já usou todos os convites disponíveis."}, status_code=400)

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

        novo_total = convites_restantes - 1
        update_resp = supabase.table("cadastros").update({"convites_disponiveis": novo_total}).eq("id", socio_id).execute()
        print("📉 Resultado do update:", update_resp)

        return JSONResponse({
            "ok": True,
            "mensagem": f"Convite registrado.",
            "convites_restantes": novo_total
        })

    except Exception as e:
        print("🚨 Erro geral no convite:", e)
        return JSONResponse({"erro": f"Erro ao salvar convidado: {str(e)}"}, status_code=500)

# ==============================================================
# ❌ Opt-out: remove pelo ID
# ==============================================================

@app.get("/optout", response_class=HTMLResponse)
async def optout(request: Request, id: int = None):
    if not supabase:
        return HTMLResponse("<h3>Serviço Supabase indisponível.</h3>", status_code=503)

    if not id:
        return HTMLResponse("<h3>ID não encontrado. Volte e tente novamente.</h3>", status_code=400)

    try:
        supabase.table("cadastros").delete().eq("id", id).execute()

        html = """
        <script>
          localStorage.removeItem('socio_id');
          localStorage.removeItem('email');
          localStorage.removeItem('whatsapp');
          alert('Seus dados foram removidos com sucesso.');
          window.location.href = "/";
        </script>
        """
        return HTMLResponse(html)

    except Exception as e:
        print("🚨 Erro ao excluir dados:", e)
        return HTMLResponse(f"<h3>Erro ao excluir dados:</h3><pre>{e}</pre>", status_code=500)

# ==============================================================
# ✳️ Registrar interesse futuro — atualiza o mesmo ID
# ==============================================================

@app.post("/api/interesse")
async def registrar_interesse(request: Request):
    if not supabase:
        return JSONResponse({"erro": "Serviço Supabase indisponível."}, status_code=503)

    data = await request.json()
    pessoa_id = data.get("id")

    if not pessoa_id:
        return JSONResponse({"erro": "ID não enviado"}, status_code=400)

    try:
        supabase.table("cadastros").update({
            "nome": data.get("nome"),
            "apelido": data.get("apelido"),
            "status": "interessado"
        }).eq("id", pessoa_id).execute()

        return JSONResponse({"mensagem": "Seu interesse foi registrado com sucesso"})
    except Exception as e:
        print("🚨 Erro ao registrar interesse:", e)
        return JSONResponse({"erro": str(e)}, status_code=500)

# ==============================================================
# ✅ Mensagem de inicialização
# ==============================================================

@app.on_event("startup")
async def startup_event():
    print("🌟 Servidor Prelude Golden Christmas iniciado com sucesso.")
