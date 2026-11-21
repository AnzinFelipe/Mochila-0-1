#!/usr/bin/env python3
"""
Medição de uso de memória (bônus do projeto) - mochila 0/1.

Mede a memória ADICIONAL que o algoritmo usa (sem contar a entrada) e compara com a
complexidade de espaço teórica:
    força bruta                  O(1) de memória extra  (a entrada ocupa O(n))
    PD (tabela completa)         O(n.W)  - é o que os arquivos programacao_dinamica.* fazem
    PD (vetor único), opcional   O(W)    - comparação extra, só com --vetor-unico

Cada medição roda em um PROCESSO NOVO (e separada dos experimentos de tempo, que não são
afetados). Dois métodos:
    pico_so      pico de memória residente do processo antes/depois do algoritmo
                 (C e Python; Linux: VmHWM, Windows: PeakWorkingSetSize, macOS: ru_maxrss)
    tracemalloc  pico das alocações do Python durante o algoritmo (só Python)

Uso:
    python3 memoria.py                         # tamanhos padrão, 3 repetições
    python3 memoria.py --n-max 1600 --vetor-unico
    python3 memoria.py --saida resultados/memoria.csv

Saída: CSV (padrão resultados/memoria.csv) lido por graficos.py (figura 8 e tabela_memoria.md).
Requer gcc (ou clang/cc) para o lado C; sem compilador, mede só o Python.
"""
import argparse
import csv
import gc
import importlib
import os
import shutil
import statistics
import subprocess
import sys
import tracemalloc

AQUI = os.path.dirname(os.path.abspath(__file__))
EXE = ".exe" if os.name == "nt" else ""
SEMENTE_NOTA = "mesmas entradas do experimento de tempo (gerar_entrada, cenário aleatório, W = 10n)"

ALGS = ("forca_bruta", "programacao_dinamica", "pd_vetor_unico")
N_FORCA_BRUTA = (10, 14, 18)


# ----------------------------------------------------------------------------
# Lado "worker": roda UMA medição em um processo novo e imprime o resultado
# ----------------------------------------------------------------------------
def pico_so_bytes():
    """Pico de memória residente do processo, em bytes; None se a plataforma não suportar."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC),
                                                    wintypes.DWORD]
            k32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
            c = PMC()
            c.cb = ctypes.sizeof(c)
            if k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
                return int(c.PeakWorkingSetSize)
            return None
        if sys.platform.startswith("linux"):
            # VmHWM é o pico DESTE processo. ru_maxrss herdaria o pico do processo pai
            # como piso (quirk do Linux após fork/exec) e falsearia as medições pequenas.
            with open("/proc/self/status") as f:
                for linha in f:
                    if linha.startswith("VmHWM:"):
                        return int(linha.split()[1]) * 1024
        import resource
        kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(kb if sys.platform == "darwin" else kb * 1024)
    except Exception:
        return None


def pd_vetor_unico(w, v, W):
    """Extra: PD com vetor único, O(W) de memória."""
    dp = [0] * (W + 1)
    for wi, vi in zip(w, v):
        for j in range(W, wi - 1, -1):
            if dp[j - wi] + vi > dp[j]:
                dp[j] = dp[j - wi] + vi
    return dp[W]


def worker(alg, metodo, n, W, pasta):
    sys.path.insert(0, pasta)
    if alg == "forca_bruta":
        mod = importlib.import_module("forca_bruta")
        w, v = mod.gerar_entrada("aleatorio", n, W)
        executar = lambda: mod.forca_bruta(w, v, W)
        valor_de = lambda r: r
    elif alg == "programacao_dinamica":
        mod = importlib.import_module("programacao_dinamica")
        w, v = mod.gerar_entrada("aleatorio", n, W)
        executar = lambda: mod.pd_preencher(w, v, W)
        valor_de = lambda r: r[n][W]
    else:
        mod = importlib.import_module("programacao_dinamica")
        w, v = mod.gerar_entrada("aleatorio", n, W)
        executar = lambda: pd_vetor_unico(w, v, W)
        valor_de = lambda r: r

    gc.collect()
    if metodo == "tracemalloc":
        tracemalloc.start()
        resultado = executar()
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(pico, valor_de(resultado))
    else:
        pico_so_bytes()  # aquecimento: a 1a leitura carrega páginas e não pode entrar na conta
        antes = pico_so_bytes()
        resultado = executar()
        depois = pico_so_bytes()
        if antes is None or depois is None:
            print("NA", valor_de(resultado))
        else:
            print(max(0, depois - antes), valor_de(resultado))
    return 0


# ----------------------------------------------------------------------------
# Lado "orquestrador": compila o C, roda as medições e grava o CSV
# ----------------------------------------------------------------------------
def compilar_drivers(pasta, algs):
    cc = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    if cc is None:
        print("aviso: nenhum compilador C encontrado; o lado C será ignorado")
        return {}
    build = os.path.join(pasta, "build")
    os.makedirs(build, exist_ok=True)
    marcador = {"forca_bruta": "ALG_FB", "programacao_dinamica": "ALG_PD", "pd_vetor_unico": "ALG_PD1D"}
    exes = {}
    for alg in algs:
        exe = os.path.join(build, f"mem_{alg}_c{EXE}")
        cmd = [cc, "-O2", f"-D{marcador[alg]}", "-o", exe, os.path.join(pasta, "memoria_c.c"), "-lm"]
        if os.name == "nt":
            cmd.append("-lpsapi")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"aviso: falha ao compilar o driver C de {alg}:\n{r.stderr}")
            continue
        exes[alg] = exe
    return exes


def f_teorica(alg, n, W):
    if alg == "forca_bruta":
        return 1                      # O(1) de memória adicional
    if alg == "programacao_dinamica":
        return (n + 1) * (W + 1)      # células da tabela
    return W + 1                      # vetor único


def uma_medicao(cmd, lado_c):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    campos = r.stdout.split()
    if lado_c:
        return int(campos[1]) - int(campos[0]), int(campos[2])
    if campos[0] == "NA":
        return None, int(campos[1])
    return int(campos[0]), int(campos[1])


def geometrica(inicio, fim):
    x, saida = inicio, []
    while x <= fim:
        saida.append(x)
        x *= 2
    return saida


def main():
    ap = argparse.ArgumentParser(description="Medição de memória - mochila 0/1")
    ap.add_argument("--pasta", default=AQUI, help="pasta com os arquivos de código")
    ap.add_argument("--saida", default=os.path.join("resultados", "memoria.csv"))
    ap.add_argument("--reps", type=int, default=3, help="repetições por ponto (mediana)")
    ap.add_argument("--n-max", type=int, default=800, help="maior n da PD (parte de 25, dobrando)")
    ap.add_argument("--vetor-unico", action="store_true", help="inclui a PD de vetor único (extra)")
    ap.add_argument("--worker", nargs=5, metavar=("ALG", "METODO", "N", "W", "PASTA"),
                    help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.worker:
        alg, metodo, n, W, pasta = args.worker
        return worker(alg, metodo, int(n), int(W), pasta)

    pasta = os.path.abspath(args.pasta)
    algs = ["forca_bruta", "programacao_dinamica"] + (["pd_vetor_unico"] if args.vetor_unico else [])
    exes = compilar_drivers(pasta, algs)

    tamanhos = {"forca_bruta": list(N_FORCA_BRUTA),
                "programacao_dinamica": geometrica(25, args.n_max),
                "pd_vetor_unico": geometrica(25, args.n_max)}

    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    print(f"Medindo memória adicional do algoritmo ({SEMENTE_NOTA}); {args.reps} repetições por ponto\n")
    with open(args.saida, "w", newline="", encoding="utf-8") as arq:
        esc = csv.writer(arq)
        esc.writerow(["algoritmo", "linguagem", "metodo", "n", "W", "reps", "bytes_mediana",
                      "bytes_min", "bytes_max", "f_teorica", "bytes_por_unidade_f", "valor"])
        for alg in algs:
            for n in tamanhos[alg]:
                W = 10 * n
                combinacoes = [("python", "pico_so"), ("python", "tracemalloc")]
                if alg in exes:
                    combinacoes.insert(0, ("c", "pico_so"))
                for lang, metodo in combinacoes:
                    if lang == "c":
                        cmd, lado_c = [exes[alg], str(n), str(W)], True
                    else:
                        cmd = [sys.executable, os.path.abspath(__file__), "--worker", alg, metodo,
                               str(n), str(W), pasta]
                        lado_c = False
                    medidas, valor = [], None
                    try:
                        for _ in range(args.reps):
                            b, valor = uma_medicao(cmd, lado_c)
                            if b is not None:
                                medidas.append(b)
                    except (RuntimeError, subprocess.TimeoutExpired) as e:
                        print(f"  {alg:<22} {lang:<7} {metodo:<12} n={n:<5} FALHOU: {e}")
                        continue
                    if not medidas:
                        print(f"  {alg:<22} {lang:<7} {metodo:<12} n={n:<5} indisponível nesta plataforma")
                        continue
                    med = int(statistics.median(medidas))
                    f = f_teorica(alg, n, W)
                    esc.writerow([alg, lang, metodo, n, W, len(medidas), med, min(medidas),
                                  max(medidas), f, f"{med / f:.6f}", valor])
                    arq.flush()
                    print(f"  {alg:<22} {lang:<7} {metodo:<12} n={n:<5} W={W:<6} "
                          f"memória = {med / 1e6:10.3f} MB  ({med / f:8.2f} bytes por unidade de f)")
    print(f"\nResultados em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())