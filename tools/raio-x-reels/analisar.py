"""Etapa 4 (números): calcula as comparações do Prompt 2 a partir de saida/planilha_final.csv.

Usa mediana. A métrica de alcance é `visualizacoes`; sem ela, usa `curtidas`.
Os achados em texto são escritos no Claude a partir desta saída.

Uso: python analisar.py [--meu-perfil usuario]
"""

import argparse

import pandas as pd

from comum import SAIDA

CATEGORICAS = ["tipo_gancho", "tem_numero_no_gancho", "tem_introducao", "estrutura", "tipo_final", "formato_recorrente"]
AMOSTRA_MINIMA = 10


def pct(serie: pd.Series) -> str:
    c = serie.value_counts(normalize=True).mul(100).round().astype(int)
    return ", ".join(f"{k} {v}%" for k, v in c.items())


def resumo(df: pd.DataFrame, metrica: str) -> list:
    linhas = [
        f"- n = {len(df)}" + ("  (amostra pequena: pista, não conclusão)" if len(df) < AMOSTRA_MINIMA else ""),
        f"- {metrica}: mediana {df[metrica].median():.0f}",
        f"- duração (s): média {df['duracao_s'].mean():.0f}, mediana {df['duracao_s'].median():.0f}",
        f"- proporção no problema (%): mediana {df['proporcao_problema'].median():.0f}",
    ]
    linhas += [f"- {c}: {pct(df[c])}" for c in CATEGORICAS if c in df and df[c].notna().any()]
    return linhas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meu-perfil", help="usuário do seu perfil (para os passos 2 a 4)")
    args = ap.parse_args()

    df = pd.read_csv(SAIDA / "planilha_final.csv", parse_dates=["data"])
    df = df.dropna(subset=["tipo_gancho"])
    metrica = "visualizacoes" if "visualizacoes" in df and df["visualizacoes"].notna().any() else "curtidas"
    out = [f"# Números do Raio-X (métrica de alcance: {metrica})", ""]

    out.append("## 1. Perfis")
    for perfil, g in df.groupby("perfil"):
        out += [f"### {perfil}", *resumo(g, metrica), ""]

    meu = df[df["perfil"] == args.meu_perfil] if args.meu_perfil else df
    corte = max(1, round(len(meu) * 0.2))
    ordenado = meu.sort_values(metrica, ascending=False)
    out.append(f"## 2. Top 20% vs 20% de baixo ({args.meu_perfil or 'todos'}, {corte} vídeos cada)")
    out += ["### Top 20%", *resumo(ordenado.head(corte), metrica), "", "### 20% de baixo", *resumo(ordenado.tail(corte), metrica), ""]

    if "formato_recorrente" in meu and meu["formato_recorrente"].notna().any():
        out.append("## 3 e 4. Formatos por mês (mediana do formato vs resto do perfil no mesmo mês)")
        meu = meu.assign(mes=meu["data"].dt.strftime("%Y-%m"))
        for fmt, g in meu[meu["formato_recorrente"] != "nenhum"].groupby("formato_recorrente"):
            out.append(f"### {fmt} (n = {len(g)})")
            for mes, gm in g.groupby("mes"):
                resto = meu[(meu["mes"] == mes) & (meu["formato_recorrente"] != fmt)]
                out.append(
                    f"- {mes}: formato {gm[metrica].median():.0f} (n={len(gm)}) | resto {resto[metrica].median():.0f} (n={len(resto)})"
                )
            out.append("")

    texto = "\n".join(out)
    (SAIDA / "numeros.md").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
