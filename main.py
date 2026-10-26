import os  # funções do sistema operacional — criar pastas, apagar arquivos, pegar data de modificação de um arquivo, etc.
from datetime import datetime  # pra gerar o nome do arquivo com data/hora
import requests # biblioteca para enviar o video do replay para o backend pela rede.

from fastapi import FastAPI  # importa a classe principal do FastAPI, que vamos usar pra criar nossa aplicação/API
from fastapi.responses import HTMLResponse, JSONResponse  # tipos de resposta que nossos endpoints podem devolver
from fastapi.staticfiles import StaticFiles  # ferramenta pra "servir arquivos estáticos" — deixa a pasta clips/ acessível via navegador

from buffer_manager import BufferManager, concat_segments  # importa as duas coisas que criamos no buffer_manager.py


# --- Configuração ---
CAMERA_SOURCE = os.environ.get("CAMERA_SOURCE", "test_video.mp4")
LOOP_SOURCE = os.environ.get("LOOP_SOURCE", "1") == "1"
REPLAY_SECONDS = int(os.environ.get("REPLAY_SECONDS", "30"))
BUFFER_DIR = "buffer"
CLIPS_DIR = "clips"
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001/api/replays") # endereço do backend que recebe os replays 

os.makedirs(CLIPS_DIR, exist_ok=True)


# --- API ---

app = FastAPI(title="Arena Dolla - Replay Capture Service")
app.mount("/clips", StaticFiles(directory=CLIPS_DIR), name="clips")

buffer_manager = BufferManager(
    camera_source=CAMERA_SOURCE,
    buffer_dir=BUFFER_DIR,
    segment_seconds=5,
    buffer_minutes=12,
    loop_source=LOOP_SOURCE,
)


@app.on_event("startup")
def startup():
    buffer_manager.start()


@app.on_event("shutdown")
def shutdown():
    buffer_manager.stop()

def enviar_para_backend(output_path):
    """Envia o clipe salvo para o backend. Retorna a resposta ou None se falhar."""
    try:
        with open(output_path, "rb") as f:
            resposta = requests.post(
                BACKEND_URL,
                files={"video": (os.path.basename(output_path), f, "video/mp4")},
                params={"duracao_segundos": REPLAY_SECONDS},
                timeout=60, 
            )
        resposta.raise_for_status()
        return resposta.json()
    except requests.RequestException as e:
        print(f"[Upload] Falha ao enviar {output_path}: {e}")
        return None
    
# --- endpoints ---

@app.get("/", response_class=HTMLResponse)
def trigger_page():
    with open("static/trigger.html", encoding="utf-8") as f:
        return f.read()


@app.post("/save-replay")
def save_replay():
    if not buffer_manager._replay_lock.acquire(blocking=False):
        return JSONResponse(
            status_code=409,
            content={"ok": False, "error": "Já existe um replay sendo salvo. Aguarde."},
        )

    try:
        segments = buffer_manager.get_segments_last_n_seconds(REPLAY_SECONDS)

        if not segments:
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "error": "Buffer ainda não tem segundos suficientes gravados. "
                             "Aguarde alguns segundos após iniciar o serviço e tente de novo.",
                },
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"replay_{timestamp}.mp4"
        output_path = os.path.join(CLIPS_DIR, filename)

        try:
            concat_segments(segments, output_path)
        except Exception as e:
            return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

        upload = enviar_para_backend(output_path)

        return {
            "ok": True,
            "filename": filename,
            "url": f"/clips/{filename}",
            "duration_seconds": REPLAY_SECONDS,
            "created_at": timestamp,
            "enviado_backend": upload is not None,
            "backend": upload,
        }

    finally:
        buffer_manager._replay_lock.release()


@app.get("/health")
def health():
    return {"status": "ok", "camera_source": CAMERA_SOURCE, "loop_source": LOOP_SOURCE}