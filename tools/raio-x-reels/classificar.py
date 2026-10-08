"""Etapa 3: classifica cada transcrição com a Laya (alternativa open source ao Jev) e monta a planilha final.

Campos do Prompt 1. "formato_recorrente" não sai daqui: a Laya só escolhe entre opções fixas,
então os formatos são nomeados na etapa 4 (Claude), lendo transcrições e legendas.

Uso:
    python classificar.py planilha.csv [--modelo multilingual]
Gera saida/planilha_final.csv
"""

import argparse
import re

import pandas as pd

from comum import SAIDA, ler_jsonl, ler_planilha

GANCHOS = {
    "problema": "describes a problem or pain the viewer has",
    "resultado com número": "states a result or achievement with a number",
    "pergunta": "asks the viewer a question",
    "contraste": "contrasts two things or contradicts a common belief",
    "novidade": "announces something new or a piece of news",
    "história pessoal": "starts telling a personal story",
    "provocação": "a provocative, polemic or shocking statement",
    "apresentação/introdução": "greets the audience or introduces the speaker or topic before getting to the point",
}
ESTRUTURAS = {
    "problema-solução": "presents a problem, then a solution",
    "lista": "a list of items, tips or reasons",
    "tutorial passo a passo": "step by step instructions",
    "história": "tells a story",
    "opinião": "gives an opinion or argument",
    "notícia": "reports news",
    "comparação": "compares options",
}
# Score de 5 níveis -> percentual aproximado (ponto médio da faixa).
PROPORCAO_PCT = [5, 20, 40, 60, 85]

PERGUNTAS = {
    "tipo_gancho": {"type": "choice", "instructions": "Which kind of hook opens the video in `gancho`?", "criteria": GANCHOS},
    "tem_introducao": {"type": "noul", "instructions": "In `gancho`, does the speaker greet the audience, say their own name or announce what the video is about instead of starting with the content itself?"},
    "estrutura": {"type": "choice", "instructions": "What is the structure of the video in `transcricao`?", "criteria": ESTRUTURAS},
    "proporcao_problema": {
        "type": "score",
        "instructions": "How much of `transcricao` is spent describing the problem before the solution?",
        "criteria": ["almost none (0-10%)", "a little (10-30%)", "a good part (30-50%)", "most (50-70%)", "almost all (70%+)"],
    },
    # O "tipo_final" como escolha única teve baixa acurácia nos testes; perguntas sim/não separadas acertam mais.
    "pede_comentario": {"type": "noul", "instructions": "Does `final` ask the viewer to comment a word or keyword?"},
    "pede_seguir": {"type": "noul", "instructions": "Does `final` ask the viewer to follow the account?"},
    "pede_salvar": {"type": "noul", "instructions": "Does `final` ask the viewer to save or share the video?"},
    "venda": {"type": "noul", "instructions": "Does `final` sell a product or send the viewer to a link, bio, course or offer?"},
    "frase_efeito": {"type": "noul", "instructions": "Does `final` end with a memorable punchline, quote or strong closing sentence?"},
}
FINAIS_PEDIDO = [
    ("pede_comentario", "palavra-chave para comentar"),
    ("pede_seguir", "pedido de seguir"),
    ("pede_salvar", "pedido de salvar ou compartilhar"),
    ("venda", "venda direta"),
]

NUMERO = re.compile(
    # "um/uma/one" ficam de fora: na maioria das vezes são artigo, não número.
    r"\d|\b(dois|duas|três|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|vinte|trinta|cem|cento|mil|milhão|milhões|"
    r"two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|hundred|thousand|million|billion)\b",
    re.IGNORECASE,
)


def respostas_para_campos(a: dict, gancho: str) -> dict:
    p = lambda k: a[k]["noul"]
    pedidos = [(p(k), rotulo) for k, rotulo in FINAIS_PEDIDO]
    prob, rotulo = max(pedidos)
    if prob < 0.5:
        rotulo = "frase de efeito" if p("frase_efeito") >= 0.5 else "sem pedido"
    prop = a["proporcao_problema"]["probabilities"]
    return {
        "tipo_gancho": a["tipo_gancho"]["choice"],
        "conf_gancho": round(a["tipo_gancho"]["answer_confidence"], 2),
        # Número no gancho é verificado por regex: mais confiável que o modelo para isso.
        "tem_numero_no_gancho": "sim" if NUMERO.search(gancho) else "não",
        "tem_introducao": "sim" if p("tem_introducao") >= 0.5 else "não",
        "estrutura": a["estrutura"]["choice"],
        "conf_estrutura": round(a["estrutura"]["answer_confidence"], 2),
        "proporcao_problema": round(sum(PROPORCAO_PCT[int(k)] * v for k, v in prop.items())),
        "tipo_final": rotulo,
    }


def classificar(registros: list, modelo: str = "multilingual", device: str | None = None) -> list:
    from laya import Router

    router = Router(device=device)
    reqs = [
        {"state": {"gancho": r["gancho"], "transcricao": r["texto"], "final": r["final"]}, "questions": PERGUNTAS, "model": modelo}
        for r in registros
    ]
    saidas = router.predict_batch(reqs, batch_size=8)
    return [respostas_para_campos(s["answers"], r["gancho"]) for s, r in zip(saidas, registros)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("planilha")
    ap.add_argument("--modelo", default="multilingual", help="multilingual (padrão, mesmo modelo para PT e EN), english ou typed-decisions")
    args = ap.parse_args()

    df = ler_planilha(args.planilha)
    # Última transcrição bem-sucedida de cada link.
    trans = {r["url"]: r for r in ler_jsonl(SAIDA / "transcricoes.jsonl") if r.get("texto")}
    regs = [trans[u] for u in df["url"] if u in trans]
    print(f"Classificando {len(regs)} transcrições ({len(df) - len(regs)} sem transcrição)...", flush=True)

    campos = pd.DataFrame(classificar(regs, args.modelo))
    campos.insert(0, "url", [r["url"] for r in regs])
    campos["idioma"] = [r["idioma"] for r in regs]
    campos["gancho_texto"] = [r["gancho"] for r in regs]
    campos["transcricao"] = [r["texto"] for r in regs]
    if "duracao_s" not in df:
        df["duracao_s"] = df["url"].map({r["url"]: r["duracao_audio_s"] for r in regs})
    # Legenda e contagens exatas que o yt-dlp trouxe têm prioridade sobre a planilha (que costuma arredondar).
    for col in ("legenda", "curtidas", "comentarios"):
        do_post = df["url"].map({r["url"]: (r.get("meta") or {}).get(col) for r in regs})
        df[col] = do_post.fillna(df[col]) if col in df else do_post

    final = df.merge(campos, on="url", how="left")
    final["formato_recorrente"] = ""
    final.to_csv(SAIDA / "planilha_final.csv", index=False)
    print(f"Pronto: {SAIDA / 'planilha_final.csv'}")


if __name__ == "__main__":
    main()
