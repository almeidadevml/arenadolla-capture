# Arena Dolla — Serviço de Captura de Replays

Serviço que roda ao lado da câmera da quadra. Ele grava o jogo o tempo todo e, quando alguém aperta o botão "Salvar Replay", transforma os últimos 30 segundos num vídeo e envia automaticamente para a [API do Arena Dolla](https://github.com/almeidadevml/arenadolla-backend).

## Como funciona

1. O **ffmpeg** grava a câmera sem parar, em pedaços de 5 segundos (o *buffer*).
2. Um processo em segundo plano apaga os pedaços com mais de 12 minutos, para o disco não encher.
3. Quando o botão é clicado, os pedaços dos últimos 30 segundos são juntados num único vídeo.
4. O vídeo é salvo na pasta `clips/` e enviado para a API.

## Tecnologias

- **Python** — linguagem principal
- **FastAPI** e **Uvicorn** — página do botão e endpoint que salva o replay
- **ffmpeg** — gravação da câmera e montagem do vídeo
- **requests** — envio do replay para a API
- **threading** — limpeza do buffer em segundo plano

## Como rodar localmente

**Antes de tudo:** instale o [ffmpeg](https://ffmpeg.org/download.html). No Windows 11:

```bash
winget install ffmpeg
```

1. Clone o repositório e crie o ambiente virtual:

```bash
git clone https://github.com/almeidadevml/arenadolla-capture.git
cd arenadolla-capture
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Coloque um vídeo qualquer na pasta com o nome `test_video.mp4`. Ele simula a câmera enquanto não há uma de verdade.

3. Rode o servidor:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

4. Abra http://localhost:8000, espere uns 40 segundos e clique em **Salvar Replay**.

Para usar uma câmera real, defina a variável `CAMERA_SOURCE` com o endereço RTSP da câmera e `LOOP_SOURCE=0`.