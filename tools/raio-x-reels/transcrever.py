"""Etapa 2: baixa o áudio de cada Reel e transcreve com faster-whisper (gratuito, roda local).

Retomável: links já transcritos em saida/transcricoes.jsonl são pulados.

Uso:
    python transcrever.py planilha.csv [--modelo large-v3-turbo] [--cookies cookies.txt]
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from comum import SAIDA, ler_jsonl, ler_planilha

SEGUNDOS_GANCHO = 5
SEGUNDOS_FINAL = 8


def baixar_audio(linha, destino: Path, cookies: str | None) -> None:
    """Extrai áudio mono 16 kHz. Tenta o link direto do vídeo; se falhar, usa yt-dlp no link do post."""
    video_url = linha.get("video_url")
    if isinstance(video_url, str) and video_url.startswith("http"):
        r = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-i", video_url, "-vn", "-ac", "1", "-ar", "16000", str(destino)],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode == 0 and destino.exists():
            return

    bruto = destino.with_suffix(".src")
    cmd = [sys.executable, "-m", "yt_dlp", "-q", "--no-warnings", "-f", "ba/b", "-o", str(bruto), linha["url"]]
    if cookies:
        cmd[3:3] = ["--cookies", cookies]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "yt-dlp falhou")
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(bruto), "-vn", "-ac", "1", "-ar", "16000", str(destino)],
        check=True, timeout=300,
    )


def transcrever(modelo: WhisperModel, audio: Path) -> dict:
    segs, info = modelo.transcribe(str(audio), vad_filter=True, beam_size=1, condition_on_previous_text=False)
    segs = [{"inicio": round(s.start, 2), "fim": round(s.end, 2), "texto": s.text.strip()} for s in segs]
    dur = info.duration
    gancho = [s for s in segs if s["inicio"] < SEGUNDOS_GANCHO] or segs[:1]
    final = [s for s in segs if s["fim"] > dur - SEGUNDOS_FINAL] or segs[-1:]
    return {
        "idioma": info.language,
        "duracao_audio_s": round(dur, 1),
        "texto": " ".join(s["texto"] for s in segs),
        "gancho": " ".join(s["texto"] for s in gancho),
        "final": " ".join(s["texto"] for s in final),
        "segmentos": segs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("planilha")
    ap.add_argument("--modelo", default="large-v3-turbo", help="tiny, base, small, medium, large-v3-turbo...")
    ap.add_argument("--cookies", help="cookies.txt do Instagram (formato Netscape) para o yt-dlp")
    ap.add_argument("--threads", type=int, default=0, help="threads de CPU (0 = automático)")
    ap.add_argument("--limite", type=int, default=0, help="transcreve só N vídeos novos (teste)")
    args = ap.parse_args()

    df = ler_planilha(args.planilha)
    SAIDA.mkdir(exist_ok=True)
    arq = SAIDA / "transcricoes.jsonl"
    feitos = {r["url"] for r in ler_jsonl(arq) if "texto" in r}
    pendentes = [l for l in df.to_dict("records") if l["url"] not in feitos]
    if args.limite:
        pendentes = pendentes[: args.limite]
    print(f"{len(df)} Reels na planilha, {len(feitos)} já transcritos, {len(pendentes)} a fazer.", flush=True)

    modelo = WhisperModel(args.modelo, device="auto", compute_type="int8", cpu_threads=args.threads)
    with tempfile.TemporaryDirectory() as tmp, arq.open("a", encoding="utf-8") as out:
        for i, linha in enumerate(pendentes, 1):
            audio = Path(tmp) / "audio.wav"
            try:
                baixar_audio(linha, audio, args.cookies)
                reg = {"url": linha["url"], **transcrever(modelo, audio)}
                print(f"[{i}/{len(pendentes)}] ok  {linha['url']}", flush=True)
            except Exception as e:  # segue para o próximo; o erro fica registrado
                reg = {"url": linha["url"], "erro": str(e)[:300]}
                print(f"[{i}/{len(pendentes)}] ERRO {linha['url']}: {reg['erro']}", flush=True)
            out.write(json.dumps(reg, ensure_ascii=False) + "\n")
            out.flush()
            for f in Path(tmp).iterdir():
                f.unlink()


if __name__ == "__main__":
    main()
