import glob        # serve pra "buscar arquivos por padrão de nome".
import os          # funções do sistema operacional — criar pastas, apagar arquivos, pegar data de modificação de um arquivo, etc.
import subprocess  # é como o Python "chama" outros programas do computador.
import threading   # permite rodar várias coisas "ao mesmo tempo" dentro do mesmo programa.
import time        # funções de tempo — pegar o horário atual, pausar a execução por X segundos, etc.
from datetime import datetime  # ferramenta para formatar datas/horas de um jeito legível.


class BufferManager:
    def __init__(
        self,
        camera_source: str,
        buffer_dir: str,
        segment_seconds: int = 5,
        buffer_minutes: int = 12,
        loop_source: bool = False,
    ):
        """
        camera_source: URL RTSP da câmera real
                       (ex: rtsp://user:senha@ip/stream)
                       OU caminho de um arquivo de vídeo local,
                       se loop_source=True.

        buffer_dir: pasta onde os segmentos ficam guardados temporariamente.

        segment_seconds: duração de cada segmento gravado.

        buffer_minutes: quanto tempo de vídeo mantemos no buffer antes de apagar.

        loop_source: True = está usando um vídeo local repetido para simular
                     uma câmera (útil para testar sem hardware).
        """

        self.camera_source = camera_source
        self.buffer_dir = buffer_dir
        self.segment_seconds = segment_seconds
        self.buffer_minutes = buffer_minutes
        self.loop_source = loop_source

        self.process = None
        self._stop_cleanup = threading.Event()
        self._replay_lock = threading.Lock()

        os.makedirs(self.buffer_dir, exist_ok=True)

    def _build_ffmpeg_cmd(self):

        segment_pattern = os.path.join(
            self.buffer_dir,
            "seg_%Y%m%d_%H%M%S.mp4"
        )

        cmd = ["ffmpeg", "-y"]

        if self.loop_source:
            # Simula uma câmera ao vivo repetindo um arquivo de vídeo em loop
            cmd += [
                "-stream_loop", "-1",
                "-re",
                "-i", self.camera_source
            ]
        else:
            # Conecta na câmera RTSP
            cmd += [
                "-rtsp_transport", "tcp",
                "-i", self.camera_source
            ]

        cmd += [
            "-c", "copy",
            "-f", "segment",
            "-segment_time", str(self.segment_seconds),
            "-reset_timestamps", "1",
            "-strftime", "1",
            segment_pattern,
        ]

        return cmd

    def start(self):
        cmd = self._build_ffmpeg_cmd()

        print("[BufferManager] Iniciando ffmpeg:")
        print(" ", " ".join(cmd))

        try:
                self.process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg não foi encontrado. Verifique se ele está "
                "instalado e disponível no PATH."
            )

        threading.Thread(target=self._cleanup_loop, daemon=True).start()

    def stop(self):

        self._stop_cleanup.set()

        if self.process:
            self.process.terminate()

    def _cleanup_loop(self):

        max_age = self.buffer_minutes * 60

        while not self._stop_cleanup.is_set():

            now = time.time()

            for f in glob.glob(
                os.path.join(self.buffer_dir, "seg_*.mp4")
            ):
                try:
                    if now - os.path.getmtime(f) > max_age:
                        os.remove(f)

                except FileNotFoundError:
                    pass

            time.sleep(10)

    def get_segments_last_n_seconds(self, seconds: int):
        """
        Retorna os arquivos de segmento que cobrem os últimos N segundos,
        em ordem cronológica.
        """

        now = time.time()

        files = sorted(
            glob.glob(
                os.path.join(self.buffer_dir, "seg_*.mp4")
            )
        )

        selected = [
            f
            for f in files
            if now - os.path.getmtime(f)
            <= seconds + self.segment_seconds
        ]

        return selected


def concat_segments(segments, output_path):
    """Junta uma lista de arquivos .mp4 num único arquivo, sem recodificar."""
    if not segments:
        raise ValueError("Nenhum segmento disponível no buffer ainda.")

    list_file = output_path + ".txt"
    temp_output = output_path + ".tmp.mp4"

    with open(list_file, "w") as f:
        for seg in segments:
            f.write(f"file '{os.path.abspath(seg)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        temp_output,
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg falhou ao concatenar: {result.stderr.decode()}")

        if not os.path.isfile(temp_output) or os.path.getsize(temp_output) == 0:
            raise RuntimeError("ffmpeg terminou mas o vídeo gerado está vazio ou não existe.")

        os.replace(temp_output, output_path)

    finally:
        if os.path.exists(list_file):
            os.remove(list_file)
        if os.path.exists(temp_output):
            os.remove(temp_output)

    return output_path

