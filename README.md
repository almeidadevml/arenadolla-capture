# Arena Dolla — Serviço de Captura de Replays

Serviço que roda ao lado da câmera da quadra. Ele grava o jogo o tempo todo e, quando alguém aperta o botão "Salvar Replay", transforma os últimos 30 segundos num vídeo e envia automaticamente para a [API do Arena Dolla](https://github.com/almeidadevml/arenadolla-backend).

## Arquitetura

```mermaid
flowchart LR
    A[Câmera] --> B[ffmpeg - buffer de 5s]
    B --> C[Botão Salvar Replay]
    C --> D[Clipe de 30s]
    D --> E[API Arena Dolla - Render]
    E --> F[(PostgreSQL - Supabase)]
    E --> G[Site - em desenvolvimento]
```

Este repositório cuida da parte da quadra (câmera, buffer e botão). A API fica no repositório [arenadolla-backend](https://github.com/almeidadevml/arenadolla-backend).

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

## Pré-requisitos

- **Python 3.10** ou mais recente
- **Git**, para clonar o repositório
- **ffmpeg**, instalado e disponível no PATH (no Windows 11: `winget install ffmpeg`)
- **[arenadolla-backend](https://github.com/almeidadevml/arenadolla-backend)** rodando, para que os replays sejam enviados (sem ele, os clipes continuam sendo salvos na pasta `clips/`)

## Estrutura do projeto

```
arenadolla-capture/
├── main.py              # API: página do botão, salvar replay e envio para o backend
├── buffer_manager.py    # Gravação contínua com ffmpeg, limpeza e junção dos segmentos
├── static/
│   └── trigger.html     # Página com o botão "Salvar Replay"
├── requirements.txt     # Bibliotecas Python do projeto
└── .gitignore           # Arquivos que não vão para o GitHub
```

Pastas criadas automaticamente ao rodar (não vão para o GitHub):

- `buffer/` — segmentos de 5 segundos da gravação contínua
- `clips/` — replays prontos de 30 segundos

## Variáveis de ambiente

| Variável | Padrão | Para que serve |
|---|---|---|
| `CAMERA_SOURCE` | `test_video.mp4` | Vídeo de teste ou endereço RTSP da câmera real |
| `LOOP_SOURCE` | `1` | `1` repete o vídeo de teste em loop; `0` para câmera real |
| `REPLAY_SECONDS` | `30` | Duração de cada replay, em segundos |
| `BACKEND_URL` | `http://localhost:8001/api/replays` | Endereço da API que recebe os replays |

Exemplo no PowerShell, para usar uma câmera real e a API na nuvem:

```powershell
$env:CAMERA_SOURCE = "rtsp://usuario:senha@IP-DA-CAMERA/stream"
$env:LOOP_SOURCE = "0"
$env:BACKEND_URL = "https://arenadolla-backend.onrender.com/api/replays"
uvicorn main:app --host 0.0.0.0 --port 8000
```
 
## Como rodar localmente

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

## Status do projeto

- [x] Gravação contínua em buffer com ffmpeg
- [x] Limpeza automática dos segmentos antigos
- [x] Botão que salva os últimos 30 segundos como replay
- [x] Proteção contra cliques duplos e vídeos corrompidos
- [x] Envio automático do replay para a API
- [ ] Teste com câmera real (RTSP)

## Próximas melhorias

- Fila de reenvio: tentar de novo os replays que não foram enviados
- Prints do sistema funcionando, junto com o site
- Rodar como serviço no mini-PC da quadra, ligando sozinho

## Autor

Feito por **Lucas Almeida** — [github.com/almeidadevml](https://github.com/almeidadevml)