# Raio-X de Reels

Pipeline gratuito para comparar Reels de dois perfis: transcrição com faster-whisper e classificação com a [Laya](https://github.com/NandhaKishorM/laya), alternativa open source ao Jev. A análise final (Prompt 2) é feita no Claude.

## Instalação

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Uso

A planilha de entrada pode ser o CSV, XLSX ou JSON exportado do Apify. As colunas são reconhecidas pelos nomes do Apify (`url`, `ownerUsername`, `timestamp`, `videoDuration`, `videoPlayCount`, `likesCount`, `commentsCount`, `videoUrl`, `caption`) ou pelos nomes em português de `comum.py`.

```bash
.venv/bin/python transcrever.py reels.csv        # gera saida/transcricoes.jsonl (retomável)
.venv/bin/python classificar.py reels.csv        # gera saida/planilha_final.csv
```

- `transcrever.py` baixa o áudio pelo `videoUrl` (link direto do vídeo). Sem ele, tenta o `yt-dlp` no link do post; use `--cookies cookies.txt` se o Instagram bloquear.
- Os links `videoUrl` do Apify expiram depois de alguns dias. Exporte de novo antes de transcrever.
- Na CPU, o modelo padrão (`large-v3-turbo`) leva cerca de 1 minuto por minuto de vídeo. Com GPU, é bem mais rápido.
- `formato_recorrente` fica em branco: é nomeado na etapa de análise, lendo transcrições e legendas.

## Acurácia da Laya

`avaliar.py` mede a classificação em 14 transcrições rotuladas à mão (PT e EN). Resultado com a Laya 0.4.0, sem ajuste fino:

| Campo | multilingual | english |
|---|---|---|
| tipo_gancho | 7/13 | 7/13 |
| tem_introducao | 7/14 | 12/14 |
| estrutura | 7/12 | 7/12 |
| tipo_final | 3/14 | 6/14 |

Com essa acurácia, os rótulos da Laya não servem para tirar conclusões. Até haver um modelo melhor, classifique as transcrições no Claude com o Prompt 1.
