"""Leitura da planilha de Reels (export do Apify ou similar) com nomes de coluna flexíveis."""

import json
from pathlib import Path

import pandas as pd

# Nome canônico -> nomes aceitos na planilha (primeiro que existir vence).
COLUNAS = {
    "url": ["url", "link", "inputUrl", "postUrl", "permalink"],
    "perfil": ["perfil", "ownerUsername", "username", "owner.username", "profile"],
    "data": ["data", "timestamp", "date", "takenAt", "taken_at"],
    "duracao_s": ["duracao_s", "videoDuration", "duration", "duracao", "video_duration"],
    "visualizacoes": ["visualizacoes", "videoPlayCount", "videoViewCount", "playCount", "views", "viewCount"],
    "curtidas": ["curtidas", "likesCount", "likes", "likeCount"],
    "comentarios": ["comentarios", "commentsCount", "comments", "commentCount"],
    "video_url": ["video_url", "videoUrl", "video", "downloadUrl"],
    "legenda": ["legenda", "caption", "text", "description"],
}

SAIDA = Path(__file__).parent / "saida"


def ler_planilha(caminho: str) -> pd.DataFrame:
    """Lê CSV/XLSX/JSON e devolve um DataFrame com as colunas canônicas que existirem."""
    p = Path(caminho)
    if p.suffix.lower() in (".xlsx", ".xls"):
        try:
            df = pd.read_excel(p)
        except ValueError:  # CSV salvo com extensão .xlsx
            df = pd.read_csv(p)
    elif p.suffix.lower() == ".json":
        df = pd.json_normalize(json.loads(p.read_text(encoding="utf-8")))
    else:
        df = pd.read_csv(p)

    out = pd.DataFrame()
    for canon, nomes in COLUNAS.items():
        achada = next((n for n in nomes if n in df.columns), None)
        if achada is not None:
            out[canon] = df[achada]
    if "url" not in out:
        raise SystemExit(f"Planilha sem coluna de link. Colunas encontradas: {list(df.columns)}")
    out = out.dropna(subset=["url"]).drop_duplicates(subset=["url"]).reset_index(drop=True)
    if "data" in out:
        out["data"] = pd.to_datetime(out["data"], errors="coerce", utc=True)
    return out


def ler_jsonl(caminho: Path) -> list:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]
