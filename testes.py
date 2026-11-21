#!/usr/bin/env python3
"""
Testes automatizados de corretude - mochila 0/1 (força bruta e PD, em C e Python).

O que este script verifica:
  1. As 4 implementações passam nos seus próprios testes (--testar) e imprimem
     a MESMA assinatura (hash dos resultados de 180 instâncias).
  2. Casos de resposta conhecida (capacidade zero, nenhum item cabe, todos cabem,
     exemplo clássico, empate de capacidade) nas duas implementações em Python.
  3. Força bruta x PD em Python, em instâncias geradas pelo gerador do projeto.
  4. (Opcional, com --resultados DIR) Nos CSVs dos experimentos, as 4 implementações
     usaram as mesmas entradas (assinatura_entrada) e acharam o mesmo valor ótimo.

Uso:
  python3 testes.py                          # passos 1 a 3
  python3 testes.py --resultados resultados  # passos 1 a 4

Código de saída: 0 se tudo passou, 1 se algo falhou.
Requer gcc (ou clang/cc) no PATH para compilar os arquivos em C.
"""
import argparse
import glob
import importlib
import os
import re
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
EXE = ".exe" if os.name == "nt" else ""

falhas = []


def ok(msg):
    print(f"  [OK]    {msg}")


def falha(msg):
    print(f"  [FALHA] {msg}")
    falhas.append(msg)


# ----------------------------------------------------------------------------
# 1. Auto-testes das 4 implementações + assinatura idêntica
# ----------------------------------------------------------------------------
def compilar(fonte, destino):
    cc = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    if cc is None:
        return "nenhum compilador C encontrado (gcc/clang/cc)"
    r = subprocess.run([cc, "-O2", "-o", destino, fonte, "-lm"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return r.stderr.strip()
    return None


def passo_autotestes(pasta):
    print("\n[1] Auto-testes (--testar) das 4 implementações")
    build = os.path.join(pasta, "build")
    os.makedirs(build, exist_ok=True)

    comandos = {}
    for nome in ("forca_bruta", "programacao_dinamica"):
        exe = os.path.join(build, f"{nome}_c{EXE}")
        erro = compilar(os.path.join(pasta, f"{nome}.c"), exe)
        if erro:
            falha(f"{nome}.c não compilou: {erro}")
        else:
            comandos[f"{nome} (C)"] = [exe, "--testar"]
        comandos[f"{nome} (Python)"] = [sys.executable, os.path.join(pasta, f"{nome}.py"), "--testar"]

    # No Windows, um Python com saída redirecionada escreve em cp1252 e não em UTF-8.
    # Forçamos UTF-8 nos processos filhos e toleramos bytes inesperados na leitura.
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    assinaturas = {}
    for rotulo, cmd in comandos.items():
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=env)
        saida = r.stdout
        m = re.search(r"assinatura=([0-9a-f]{16})", saida)
        if r.returncode != 0 or "TESTES OK" not in saida or not m:
            falha(f"{rotulo}: falhou nos próprios testes\n{saida}{r.stderr}")
            continue
        assinaturas[rotulo] = m.group(1)
        ok(f"{rotulo}: testes internos passaram, assinatura {m.group(1)}")

    if len(set(assinaturas.values())) == 1 and len(assinaturas) == 4:
        ok("as 4 implementações imprimiram a mesma assinatura")
    elif assinaturas:
        falha(f"assinaturas diferentes entre as implementações: {assinaturas}")


# ----------------------------------------------------------------------------
# 2 e 3. Casos conhecidos e comparação FB x PD (Python)
# ----------------------------------------------------------------------------
def carregar_modulos(pasta):
    sys.path.insert(0, pasta)
    fb = importlib.import_module("forca_bruta")
    pd = importlib.import_module("programacao_dinamica")
    return fb, pd


def passo_casos_conhecidos(fb, pd):
    print("\n[2] Casos de resposta conhecida (Python)")
    casos = [
        # (descrição, pesos, valores, W, esperado)
        ("capacidade zero", [1, 2, 3], [10, 20, 30], 0, 0),
        ("nenhum item cabe", [6, 7, 8], [10, 20, 30], 5, 0),
        ("todos os itens cabem", [1, 2, 3], [10, 20, 30], 100, 60),
        ("exemplo clássico", [1, 3, 4, 5], [1, 4, 5, 7], 7, 9),
        ("peso exatamente igual a W", [5], [10], 5, 10),
        ("dois pequenos valem mais que um grande", [10, 5, 5], [10, 6, 6], 10, 12),
        ("guloso por razão valor/peso erra", [10, 20, 30], [60, 100, 120], 50, 220),
        ("um único item que cabe", [3], [7], 10, 7),
    ]
    for desc, w, v, W, esperado in casos:
        a = fb.forca_bruta(w, v, W)
        b = pd.pd_preencher(w, v, W)[len(w)][W]
        if a == esperado and b == esperado:
            ok(f"{desc}: {esperado}")
        else:
            falha(f"{desc}: esperado {esperado}, força bruta={a}, PD={b}")


def passo_fb_vs_pd(fb, pd):
    print("\n[3] Força bruta x PD em instâncias do gerador do projeto (Python)")
    total = 0
    for n in range(1, 15):
        for W in (0, 1, 7, 30, 100, 250):
            for cenario in fb.CENARIOS:
                w, v = fb.gerar_entrada(cenario, n, W)
                w2, v2 = pd.gerar_entrada(cenario, n, W)
                if (w, v) != (w2, v2):
                    falha(f"geradores diferentes: {cenario} n={n} W={W}")
                    return
                a = fb.forca_bruta(w, v, W)
                tab = pd.pd_preencher(w, v, W)
                b = tab[n][W]
                itens = pd.pd_reconstruir(tab, w, W)
                peso = sum(w[i - 1] for i in itens)
                valor = sum(v[i - 1] for i in itens)
                if a != b or peso > W or valor != b:
                    falha(f"{cenario} n={n} W={W}: FB={a} PD={b} itens_peso={peso} itens_valor={valor}")
                    return
                total += 1
    ok(f"{total} instâncias: mesmo valor ótimo, e os itens reconstruídos pela PD são válidos")


# ----------------------------------------------------------------------------
# 4. Consistência dos CSVs dos experimentos
# ----------------------------------------------------------------------------
def passo_csvs(pasta_resultados):
    print(f"\n[4] Consistência entre os CSVs de {pasta_resultados}")
    import pandas as pd_

    arquivos = sorted(glob.glob(os.path.join(pasta_resultados, "resultados_*.csv")))
    if len(arquivos) < 4:
        falha(f"esperados 4 CSVs resultados_*.csv, encontrados {len(arquivos)}")
        return
    chave = ["cenario", "n", "W"]
    juntos = None
    for arq in arquivos:
        df = pd_.read_csv(arq)
        nome = os.path.basename(arq)[len("resultados_"):-len(".csv")]
        # só linhas comparáveis: as que existem nas duas famílias de algoritmos
        df = df[chave + ["valor", "assinatura_entrada"]].drop_duplicates(chave)
        df = df.rename(columns={"valor": f"valor_{nome}", "assinatura_entrada": f"sig_{nome}"})
        juntos = df if juntos is None else juntos.merge(df, on=chave, how="inner")
    if juntos.empty:
        falha("nenhuma instância (cenario, n, W) comum às 4 implementações")
        return
    cols_valor = [c for c in juntos.columns if c.startswith("valor_")]
    cols_sig = [c for c in juntos.columns if c.startswith("sig_")]
    if (juntos[cols_sig].nunique(axis=1) == 1).all():
        ok(f"entradas idênticas nas 4 implementações ({len(juntos)} instâncias em comum)")
    else:
        falha("assinatura_entrada difere entre implementações em alguma instância")
    if (juntos[cols_valor].nunique(axis=1) == 1).all():
        ok("valor ótimo idêntico nas 4 implementações em todas as instâncias em comum")
    else:
        ruins = juntos[juntos[cols_valor].nunique(axis=1) > 1]
        falha(f"valor ótimo difere em {len(ruins)} instância(s):\n{ruins.to_string()}")


def main():
    ap = argparse.ArgumentParser(description="Testes de corretude - mochila 0/1")
    ap.add_argument("--pasta", default=AQUI, help="pasta com os 4 arquivos de código")
    ap.add_argument("--resultados", default=None,
                    help="pasta com os 4 CSVs dos experimentos (ativa o passo 4)")
    args = ap.parse_args()
    pasta = os.path.abspath(args.pasta)

    passo_autotestes(pasta)
    fb, pd = carregar_modulos(pasta)
    passo_casos_conhecidos(fb, pd)
    passo_fb_vs_pd(fb, pd)
    if args.resultados:
        passo_csvs(args.resultados)

    print()
    if falhas:
        print(f"RESULTADO: {len(falhas)} falha(s).")
        return 1
    print("RESULTADO: todos os testes passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())