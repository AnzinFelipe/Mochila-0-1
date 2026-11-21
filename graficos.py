#!/usr/bin/env python3
"""
Gráficos e tabelas do relatório - mochila 0/1 (força bruta x PD, C x Python).

Lê os 4 CSVs gerados pelos experimentos:
    resultados_forca_bruta_c.csv        resultados_forca_bruta_python.csv
    resultados_programacao_dinamica_c.csv  resultados_programacao_dinamica_python.csv

Gera (em --saida, padrão "graficos"):
    fig1_fb_tempo_vs_teorico.png      tempo medido x O(n.2^n), com o maior n viável em 60 s
    fig2_pd_escala_n.png              PD variando n (W = 10n): log-log x O(n.W)
    fig3_pd_escala_w.png              PD variando W (n fixo): log-log x O(n.W)
    fig4_razao_T_sobre_f.png          T(n)/f(n): deve tender a uma constante
    fig5_algoritmo_vs_algoritmo.png   força bruta x PD nas mesmas entradas
    fig6_linguagem_vs_linguagem.png   razão de tempo Python / C
    fig7_cenarios.png                 casos forçados (aleatório, todos pesados, todos cabem)
    tabela_resultados.csv / .md       todas as linhas, com média ± desvio
    tabela_limite.md                  maior n viável em 60 s da força bruta, por linguagem
    fig8_memoria.png, tabela_memoria.md   (bônus) só se existir memoria.csv na pasta --dir,
                                      gerado por memoria.py

Uso:
    python3 graficos.py                                  # CSVs na pasta atual
    python3 graficos.py --dir resultados --saida graficos
    python3 graficos.py --dir resultados --estat mediana   # plota a mediana (robusta a outliers)
Dependências: pandas, numpy, matplotlib.
"""
import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

ALGS = {"forca_bruta": "Força bruta", "programacao_dinamica": "Prog. dinâmica"}
LANGS = {"c": "C", "python": "Python"}
COR_LANG = {"c": "#1f77b4", "python": "#d95f02"}
MARCA_ALG = {"forca_bruta": "o", "programacao_dinamica": "s"}
LIMITE_MS = 60_000.0
TEMPO = "tempo médio"  # vira "tempo mediano" com --estat mediana

plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})


# ----------------------------------------------------------------------------
# Carga dos dados
# ----------------------------------------------------------------------------
def carregar(pasta):
    dados = {}
    for alg in ALGS:
        for lang in LANGS:
            caminho = os.path.join(pasta, f"resultados_{alg}_{lang}.csv")
            if os.path.exists(caminho):
                dados[(alg, lang)] = pd.read_csv(caminho)
            else:
                print(f"aviso: {caminho} não encontrado; gráficos que dependem dele serão parciais")
    return dados


def aplicar_estat(dados, estat):
    """Com estat="mediana", os gráficos passam a usar a mediana no lugar da média.
    O desvio-padrão deixa de ser desenhado (não é a barra de erro certa para a mediana)."""
    if estat == "media":
        return dados
    saida = {}
    for chave, df in dados.items():
        d = df.copy()
        d["media_ms"] = d["mediana_ms"]
        d["desvio_ms"] = np.nan
        d["ns_por_unidade_f"] = d["mediana_ms"] * 1e6 / d["f_teorica"]
        saida[chave] = d
    return saida


def serie(dados, alg, lang, sweeps, cenario="aleatorio"):
    df = dados.get((alg, lang))
    if df is None:
        return None
    s = df[df["sweep"].isin(sweeps) & (df["cenario"] == cenario)]
    s = s.sort_values(["n", "W"]).drop_duplicates(["n", "W"])
    return s if len(s) else None


def constante_ajuste(s):
    """Média geométrica de T/f: fixa o fator constante da curva teórica c.f(n)."""
    r = (s["media_ms"] / s["f_teorica"]).to_numpy()
    r = r[r > 0]
    return float(np.exp(np.log(r).mean()))


def eixo_log_x(ax, valores):
    """Eixo x logarítmico com rótulos legíveis (só os valores medidos, sem notação 10^k)."""
    ax.set_xscale("log")
    vals = sorted(set(int(v) for v in valores))
    ax.set_xticks(vals)
    ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.tick_params(axis="x", labelsize=7, labelrotation=45)


def salvar(fig, pasta, nome, rect=None):
    caminho = os.path.join(pasta, nome)
    fig.tight_layout(rect=rect) if rect else fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    plt.close(fig)
    print("gerado:", caminho)


# ----------------------------------------------------------------------------
# Figuras
# ----------------------------------------------------------------------------
def fig1_forca_bruta(dados, pasta):
    fig, ax = plt.subplots(figsize=(7.5, 5))
    desenhou = False
    for lang in LANGS:
        s = serie(dados, "forca_bruta", lang, ["comparacao", "limite"])
        if s is None:
            continue
        desenhou = True
        ax.errorbar(s["n"], s["media_ms"], yerr=s["desvio_ms"], fmt="o-", ms=4, capsize=2,
                    color=COR_LANG[lang], label=f"{LANGS[lang]} (medido)")
        c = constante_ajuste(s)
        nn = np.linspace(s["n"].min(), s["n"].max() + 2, 100)
        ax.plot(nn, c * nn * 2.0 ** nn, "--", color=COR_LANG[lang], alpha=0.6,
                label=f"{LANGS[lang]}: c·n·2ⁿ ajustado")
        viavel = s[s["media_ms"] <= LIMITE_MS]["n"].max()
        ax.annotate(f"maior n viável\n({LANGS[lang]}): {int(viavel)}",
                    xy=(viavel, s[s["n"] == viavel]["media_ms"].iloc[0]),
                    xytext=(-60, 25), textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color=COR_LANG[lang]), color=COR_LANG[lang])
    if not desenhou:
        plt.close(fig)
        return
    ax.axhline(LIMITE_MS, color="red", lw=1, ls=":")
    ax.text(0.01, LIMITE_MS * 1.25, "limite de 60 s", color="red", fontsize=8, ha="left",
            transform=ax.get_yaxis_transform())
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.set_yscale("log")
    ax.set_xlabel("n (número de itens)")
    ax.set_ylabel(f"{TEMPO} (ms, escala log)")
    ax.set_title("Força bruta: tempo medido × complexidade teórica O(n·2ⁿ)")
    ax.legend(fontsize=8)
    salvar(fig, pasta, "fig1_fb_tempo_vs_teorico.png")


def _fig_pd_loglog(dados, pasta, sweep, xcol, xlabel, teoria, nome, titulo):
    fig, ax = plt.subplots(figsize=(7, 5))
    desenhou = False
    xs_usados = []
    for lang in LANGS:
        s = serie(dados, "programacao_dinamica", lang, [sweep])
        if s is None or len(s) < 2:
            continue
        desenhou = True
        xs_usados += list(s[xcol])
        x, y = s[xcol].to_numpy(float), s["media_ms"].to_numpy(float)
        incl = np.polyfit(np.log(x), np.log(y), 1)[0]
        ax.errorbar(x, y, yerr=s["desvio_ms"], fmt="o-", ms=4, capsize=2, color=COR_LANG[lang],
                    label=f"{LANGS[lang]} (inclinação medida = {incl:.2f})")
        c = constante_ajuste(s)
        ax.plot(x, c * s["f_teorica"], "--", color=COR_LANG[lang], alpha=0.6,
                label=f"{LANGS[lang]}: c·n·W ajustado")
    if not desenhou:
        plt.close(fig)
        return
    eixo_log_x(ax, xs_usados)
    ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"{TEMPO} (ms)")
    ax.set_title(titulo + f"\ninclinação teórica = {teoria}")
    ax.legend(fontsize=8)
    salvar(fig, pasta, nome)


def fig2_pd_n(dados, pasta):
    _fig_pd_loglog(dados, pasta, "escala_n", "n", "n (W = 10n), escala log", 2,
                   "fig2_pd_escala_n.png", "PD variando n, com W = 10n: O(n·W) = O(n²)")


def fig3_pd_w(dados, pasta):
    _fig_pd_loglog(dados, pasta, "escala_w", "W", "W (n = 100), escala log", 1,
                   "fig3_pd_escala_w.png", "PD variando W, com n fixo: O(n·W) = O(W)")


def fig4_razao(dados, pasta):
    paineis = [("forca_bruta", ["comparacao", "limite"], "n", "Força bruta: T / (n·2ⁿ)", False),
               ("programacao_dinamica", ["escala_n"], "n", "PD (W = 10n): T / (n·W)", True),
               ("programacao_dinamica", ["escala_w"], "W", "PD (n = 100): T / (n·W)", True)]
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.2))
    for ax, (alg, sweeps, xcol, titulo, logx) in zip(axs, paineis):
        xs = []
        for lang in LANGS:
            s = serie(dados, alg, lang, sweeps)
            if s is None:
                continue
            xs += list(s[xcol])
            ax.plot(s[xcol], s["ns_por_unidade_f"], "o-", ms=4, color=COR_LANG[lang],
                    label=LANGS[lang])
        ax.set_title(titulo, fontsize=10)
        ax.set_xlabel(xcol)
        ax.set_ylabel("ns por unidade de f")
        ax.set_yscale("log")  # C e Python diferem em ordens de grandeza: log mostra os dois
        if logx and xs:
            eixo_log_x(ax, xs)
        else:
            ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.legend(fontsize=8)
    fig.suptitle("Razão T(n)/f(n) (escala log em y): curva horizontal ⇒ f é a complexidade correta")
    salvar(fig, pasta, "fig4_razao_T_sobre_f.png", rect=[0, 0, 1, 0.95])


def fig5_alg_vs_alg(dados, pasta):
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    desenhou = False
    for ax, lang in zip(axs, LANGS):
        for alg in ALGS:
            s = serie(dados, alg, lang, ["comparacao"])
            if s is None:
                continue
            desenhou = True
            ax.errorbar(s["n"], s["media_ms"], yerr=s["desvio_ms"], fmt=MARCA_ALG[alg] + "-",
                        ms=4, capsize=2, label=ALGS[alg])
        ax.set_yscale("log")
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.set_title(f"{LANGS[lang]}: mesmas entradas (W = 10n)")
        ax.set_xlabel("n")
        ax.legend(fontsize=8)
    axs[0].set_ylabel(f"{TEMPO} (ms, escala log)")
    if desenhou:
        salvar(fig, pasta, "fig5_algoritmo_vs_algoritmo.png")
    else:
        plt.close(fig)


def fig6_lang_vs_lang(dados, pasta):
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    desenhou = False
    for alg, sweeps in (("forca_bruta", ["comparacao"]),
                        ("programacao_dinamica", ["comparacao", "escala_n"])):
        c, p = serie(dados, alg, "c", sweeps), serie(dados, alg, "python", sweeps)
        if c is None or p is None:
            continue
        m = c.merge(p, on=["n", "W"], suffixes=("_c", "_py"))
        if m.empty:
            continue
        desenhou = True
        ax.plot(m["n"], m["media_ms_py"] / m["media_ms_c"], MARCA_ALG[alg] + "-", ms=4,
                label=ALGS[alg])
    if not desenhou:
        plt.close(fig)
        return
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("n")
    ax.set_ylabel("tempo Python / tempo C (×)")
    ax.set_title("Quantas vezes o Python é mais lento que o C (mesmas entradas)")
    ax.legend(fontsize=8)
    salvar(fig, pasta, "fig6_linguagem_vs_linguagem.png")


def fig7_cenarios(dados, pasta):
    nomes = ["aleatorio", "todos_pesados", "todos_cabem"]
    rotulos = ["aleatório\n(médio)", "todos pesados\n(nenhum cabe)", "todos cabem"]
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, sweep, titulo, algs, log in (
            (axs[0], "cenarios", "n = 18, W = 180", list(ALGS), True),
            (axs[1], "cenarios_grande", "PD com entrada grande", ["programacao_dinamica"], False)):
        grupos = [(a, l) for a in algs for l in LANGS if (a, l) in dados]
        larg = 0.8 / max(1, len(grupos))
        for k, (alg, lang) in enumerate(grupos):
            df = dados[(alg, lang)]
            df = df[df["sweep"] == sweep].set_index("cenario").reindex(nomes)
            xs = np.arange(len(nomes)) + k * larg
            ax.bar(xs, df["media_ms"], larg, yerr=df["desvio_ms"], capsize=2,
                   label=f"{ALGS[alg]} ({LANGS[lang]})")
        ax.set_xticks(np.arange(len(nomes)) + 0.4 - larg / 2)
        ax.set_xticklabels(rotulos, fontsize=8)
        if log:  # tempos de ordens de grandeza diferentes; barras em log só onde é necessário
            ax.set_yscale("log")
        ax.set_title(titulo)
        ax.set_ylabel(f"{TEMPO} (ms, escala log)" if log else f"{TEMPO} (ms)")
        ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    salvar(fig, pasta, "fig7_cenarios.png")



# ----------------------------------------------------------------------------
# Memória (bônus): lê memoria.csv, gerado por memoria.py
# ----------------------------------------------------------------------------
NOMES_MEM = {"forca_bruta": "Força bruta", "programacao_dinamica": "PD (tabela completa)",
             "pd_vetor_unico": "PD (vetor único, extra)"}
METODOS_MEM = {"pico_so": "pico do processo", "tracemalloc": "tracemalloc"}
RESOLUCAO_B = 1e5  # abaixo disso (~100 KB) a medição pelo SO é limitada pelo tamanho de página


def fmt_bytes(b):
    b = float(b)
    for unidade, f in (("MB", 1e6), ("KB", 1e3)):
        if b >= f:
            return f"{b / f:.1f} {unidade}"
    return f"{int(b)} B"


def fig8_memoria(pasta_dir, saida):
    caminho = os.path.join(pasta_dir, "memoria.csv")
    if not os.path.exists(caminho):
        print("aviso: memoria.csv não encontrado; figura de memória não gerada (rode memoria.py)")
        return
    m = pd.read_csv(caminho)

    # tabela (todas as linhas, inclusive força bruta)
    t = pd.DataFrame({
        "algoritmo": m["algoritmo"].map(NOMES_MEM), "linguagem": m["linguagem"].map(
            {"c": "C", "python": "Python"}),
        "método": m["metodo"].map(METODOS_MEM), "n": m["n"], "W": m["W"],
        "memória adicional": m["bytes_mediana"].map(fmt_bytes),
        "bytes por unidade de f": m["bytes_por_unidade_f"].map(lambda x: f"{x:.2f}")})
    with open(os.path.join(saida, "tabela_memoria.md"), "w", encoding="utf-8") as f:
        f.write(md_tabela(t))
    print("gerado:", os.path.join(saida, "tabela_memoria.md"))

    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    xs_usados = []
    for (alg, lang, metodo), g in m[m["algoritmo"] != "forca_bruta"].groupby(
            ["algoritmo", "linguagem", "metodo"]):
        g = g.sort_values("n")
        g = g[g["bytes_mediana"] > 0]
        if g.empty:
            continue
        estilo = dict(color=COR_LANG[lang], ls="-" if alg == "programacao_dinamica" else "--",
                      marker="o" if metodo == "pico_so" else "x", ms=5)
        rotulo = f"{NOMES_MEM[alg]} - {'C' if lang == 'c' else 'Python'} ({METODOS_MEM[metodo]})"
        grande = g[g["bytes_mediana"] >= RESOLUCAO_B]
        if len(grande) >= 3:
            incl = np.polyfit(np.log(grande["n"]), np.log(grande["bytes_mediana"]), 1)[0]
            rotulo += f", inclinação {incl:.2f}"
        axs[0].plot(g["n"], g["bytes_mediana"], label=rotulo, **estilo)
        axs[1].plot(g["n"], g["bytes_por_unidade_f"], label=rotulo, **estilo)
        xs_usados += list(g["n"])
        if alg == "programacao_dinamica" and metodo == "pico_so" and len(grande) >= 1:
            c = float((grande["bytes_mediana"] / grande["f_teorica"]).median())
            axs[0].plot(g["n"], c * g["f_teorica"], ":", color=COR_LANG[lang], alpha=0.7)
    if not xs_usados:
        plt.close(fig)
        return
    axs[0].set_title("Memória adicional × n  (W = 10n)\n"
                     "inclinação teórica: 2 (tabela completa, O(n·W)), 1 (vetor único, O(W))\n"
                     "pontilhado: c·f(n) ajustado", fontsize=9)
    axs[0].set_ylabel("memória adicional (bytes, escala log)")
    axs[1].set_title("Bytes por unidade de f(n)\nconstante ⇒ o espaço teórico está correto", fontsize=9)
    axs[1].set_ylabel("bytes por unidade de f (escala log)")
    for ax in axs:
        ax.set_yscale("log")
        eixo_log_x(ax, xs_usados)
        ax.set_xlabel("n (W = 10n)")
        ax.legend(fontsize=6.5)
    salvar(fig, saida, "fig8_memoria.png")

# ----------------------------------------------------------------------------
# Tabelas
# ----------------------------------------------------------------------------
def md_tabela(df):
    cab = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    linhas = ["| " + " | ".join(str(x) for x in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([cab, sep] + linhas) + "\n"


def tabelas(dados, pasta):
    partes = []
    for (alg, lang), df in dados.items():
        d = df.copy()
        d.insert(0, "alg", ALGS[alg])
        d.insert(1, "lang", LANGS[lang])
        partes.append(d)
    if not partes:
        return
    todos = pd.concat(partes, ignore_index=True)
    todos.to_csv(os.path.join(pasta, "tabela_resultados.csv"), index=False)

    t = pd.DataFrame({
        "algoritmo": todos["alg"], "linguagem": todos["lang"], "teste": todos["sweep"],
        "cenário": todos["cenario"], "n": todos["n"], "W": todos["W"], "reps": todos["reps"],
        "média ± desvio (ms)": [f"{m:.4f} ± {d:.4f}" for m, d in zip(todos["media_ms"], todos["desvio_ms"])],
        "mediana (ms)": todos["mediana_ms"].map(lambda x: f"{x:.4f}"),
        "T/f (ns)": todos["ns_por_unidade_f"].map(lambda x: f"{x:.3f}"),
    })
    with open(os.path.join(pasta, "tabela_resultados.md"), "w", encoding="utf-8") as f:
        f.write(md_tabela(t))
    print("gerado:", os.path.join(pasta, "tabela_resultados.md"))

    linhas = []
    for lang in LANGS:
        s = serie(dados, "forca_bruta", lang, ["comparacao", "limite"])
        if s is None:
            continue
        ok = s[s["media_ms"] <= LIMITE_MS]
        linhas.append([LANGS[lang], int(ok["n"].max()), f"{ok['media_ms'].max() / 1000:.2f} s"])
    if linhas:
        lim = pd.DataFrame(linhas, columns=["linguagem", "maior n viável (≤ 60 s)", "tempo nesse n"])
        with open(os.path.join(pasta, "tabela_limite.md"), "w", encoding="utf-8") as f:
            f.write(md_tabela(lim))
        print("gerado:", os.path.join(pasta, "tabela_limite.md"))


def main():
    ap = argparse.ArgumentParser(description="Gráficos e tabelas - mochila 0/1")
    ap.add_argument("--dir", default=".", help="pasta com os 4 CSVs de resultados")
    ap.add_argument("--saida", default="graficos", help="pasta de saída")
    ap.add_argument("--estat", choices=["media", "mediana"], default="media",
                    help="estatística plotada nos gráficos (tabelas sempre trazem as duas)")
    args = ap.parse_args()

    dados_brutos = carregar(args.dir)
    if not dados_brutos:
        print("nenhum CSV encontrado em", os.path.abspath(args.dir))
        return 1
    os.makedirs(args.saida, exist_ok=True)
    global TEMPO
    TEMPO = "tempo mediano" if args.estat == "mediana" else "tempo médio"
    dados = aplicar_estat(dados_brutos, args.estat)

    fig1_forca_bruta(dados, args.saida)
    fig2_pd_n(dados, args.saida)
    fig3_pd_w(dados, args.saida)
    fig4_razao(dados, args.saida)
    fig5_alg_vs_alg(dados, args.saida)
    fig6_lang_vs_lang(dados, args.saida)
    fig7_cenarios(dados, args.saida)
    fig8_memoria(args.dir, args.saida)
    tabelas(dados_brutos, args.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())