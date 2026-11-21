#!/usr/bin/env python3
"""
Algoritmo A (força bruta) para a mochila 0/1 - experimento de desempenho em Python.

Uso:
  python3 forca_bruta.py --testar    # testes de corretude (imprime a "assinatura")
  python3 forca_bruta.py --rapido    # execução curta, só para conferir se tudo funciona
  python3 forca_bruta.py             # experimento completo -> CSV + arquivo de ambiente

Opções: --reps N (15 a 30, padrão 20)  --saida PREFIXO  --limite-s 60  --orcamento 300

Saídas: <PREFIXO>.csv (uma linha por tamanho) e <PREFIXO>_ambiente.txt.
Só o tempo da função forca_bruta() é medido; geração de entrada, CSV e
impressão ficam fora da medição.
"""
import argparse
import csv
import gc
import os
import platform
import statistics
import subprocess
import sys
import time

LINGUAGEM = "python"
ALGORITMO = "forca_bruta"
SEMENTE_BASE = 20261120
MASCARA64 = (1 << 64) - 1
CENARIOS = ("aleatorio", "todos_pesados", "todos_cabem")
FNV_BASE = 14695981039346656037
FNV_PRIMO = 1099511628211
CABECALHO = ["linguagem", "algoritmo", "sweep", "cenario", "n", "W", "fase", "reps",
             "media_ms", "desvio_ms", "min_ms", "mediana_ms", "valor",
             "assinatura_entrada", "f_teorica", "ns_por_unidade_f"]


# ----------------------------------------------------------------------------
# Algoritmo A: força bruta, O(2^n * n)
# ----------------------------------------------------------------------------
def forca_bruta(w, v, W):
    n = len(w)
    melhor = 0
    for combinacao in range(2 ** n):
        peso_total = 0
        valor_total = 0
        for i in range(n):
            if (combinacao >> i) & 1:
                peso_total += w[i]
                valor_total += v[i]
        if peso_total <= W and valor_total > melhor:
            melhor = valor_total
    return melhor


def f_teorica(n, W):
    return n * 2 ** n


# ----------------------------------------------------------------------------
# Gerador de entradas (idêntico nos 4 arquivos: LCG de 64 bits + semente fixa)
# ----------------------------------------------------------------------------
class Gerador:
    def __init__(self, semente):
        self.estado = semente & MASCARA64

    def sortear(self, lo, hi):
        self.estado = (self.estado * 6364136223846793005 + 1442695040888963407) & MASCARA64
        return lo + (self.estado >> 33) % (hi - lo + 1)


def gerar_entrada(cenario, n, W):
    """cenario: aleatorio (caso médio), todos_pesados (nenhum item cabe) ou todos_cabem."""
    g = Gerador(SEMENTE_BASE + n * 1000003 + W * 10007 + CENARIOS.index(cenario) * 101)
    limite = max(1, (W // n) if cenario == "todos_cabem" else (2 * W // n))
    w, v = [], []
    for _ in range(n):
        w.append(W + 1 + g.sortear(0, 50) if cenario == "todos_pesados" else g.sortear(1, limite))
        v.append(g.sortear(1, 100))
    return w, v


def fnv(h, x):
    return ((h ^ (x & MASCARA64)) * FNV_PRIMO) & MASCARA64


def assinatura_entrada(w, v):
    h = FNV_BASE
    for x in w:
        h = fnv(h, x)
    for x in v:
        h = fnv(h, x)
    return f"{h:016x}"


# ----------------------------------------------------------------------------
# Testes de corretude
# ----------------------------------------------------------------------------
def referencia(w, v, W):
    """Implementação independente (PD com vetor unidimensional), usada só nos testes."""
    dp = [0] * (W + 1)
    for wi, vi in zip(w, v):
        for j in range(W, wi - 1, -1):
            dp[j] = max(dp[j], dp[j - wi] + vi)
    return dp[W]


def testar():
    h = FNV_BASE
    total = 0
    for n in range(1, 13):
        for W in (0, 5, 20, 60, 150):
            for cenario in CENARIOS:
                w, v = gerar_entrada(cenario, n, W)
                obtido = forca_bruta(w, v, W)
                esperado = referencia(w, v, W)
                if obtido != esperado:
                    print(f"FALHA: {cenario} n={n} W={W}: obtido={obtido} esperado={esperado}")
                    return 1
                h = fnv(h, obtido)
                total += 1
    print(f"TESTES OK: {total} instancias conferidas com a implementação de referência")
    print(f"assinatura={h:016x}   (as 4 implementações devem imprimir a mesma assinatura)")
    return 0


# ----------------------------------------------------------------------------
# Ambiente (CPU, RAM, SO, interpretador)
# ----------------------------------------------------------------------------
def _cpu():
    try:
        with open("/proc/cpuinfo") as f:
            for linha in f:
                if linha.lower().startswith("model name"):
                    return linha.split(":", 1)[1].strip()
    except OSError:
        pass
    try:
        return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        pass
    return os.environ.get("PROCESSOR_IDENTIFIER") or platform.processor() or "desconhecida"


def _ram():
    try:
        with open("/proc/meminfo") as f:
            for linha in f:
                if linha.startswith("MemTotal"):
                    return f"{int(linha.split()[1]) / 1024 / 1024:.1f} GB"
    except OSError:
        pass
    try:
        total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True,
                                            stderr=subprocess.DEVNULL))
        return f"{total / 1024 ** 3:.1f} GB"
    except Exception:
        pass
    try:
        import ctypes

        class MemStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32),
                        ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                        ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                        ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                        ("ullAvailExtendedVirtual", ctypes.c_uint64)]
        m = MemStatus()
        m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return f"{m.ullTotalPhys / 1024 ** 3:.1f} GB"
    except Exception:
        return "desconhecida"


def ambiente(reps, orcamento, limite):
    return "\n".join([
        f"data: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"algoritmo/linguagem: {ALGORITMO} / {LINGUAGEM}",
        f"CPU: {_cpu()}",
        f"nucleos logicos: {os.cpu_count()}",
        f"RAM: {_ram()}",
        f"sistema operacional: {platform.platform()}",
        f"interpretador: {platform.python_implementation()} {platform.python_version()} "
        f"({platform.python_compiler()})",
        "flags de compilação: não se aplica (interpretado)",
        f"semente base: {SEMENTE_BASE} (gerador LCG de 64 bits, igual nas 4 implementações)",
        f"repetições por tamanho: {reps} (+1 execução de aquecimento descartada)",
        f"orçamento por tamanho: {orcamento} s; limite de viabilidade: {limite} s",
        "relógio: time.perf_counter_ns (coleta de lixo desligada durante a medição)",
    ])


# ----------------------------------------------------------------------------
# Medição
# ----------------------------------------------------------------------------
def medir(w, v, W, reps, orcamento_s):
    """Devolve (tempos_ms, valor), ou None se reps x (1ª execução) passar do orçamento."""
    t0 = time.perf_counter_ns()
    valor = forca_bruta(w, v, W)  # aquecimento: descartado, serve também para estimar o custo
    aquecimento_s = (time.perf_counter_ns() - t0) / 1e9
    if aquecimento_s * reps > orcamento_s:
        return None
    tempos = []
    gc.collect()
    gc.disable()
    try:
        for _ in range(reps):
            t0 = time.perf_counter_ns()
            valor = forca_bruta(w, v, W)
            tempos.append((time.perf_counter_ns() - t0) / 1e6)
    finally:
        gc.enable()
    return tempos, valor


def linha_csv(sweep, cenario, n, W, fase, tempos, valor, entrada):
    f = f_teorica(n, W)
    media = statistics.fmean(tempos)
    desvio = statistics.stdev(tempos) if len(tempos) > 1 else 0.0
    return [LINGUAGEM, ALGORITMO, sweep, cenario, n, W, fase, len(tempos),
            f"{media:.6f}", f"{desvio:.6f}", f"{min(tempos):.6f}",
            f"{statistics.median(tempos):.6f}", valor, entrada, f,
            f"{media * 1e6 / f:.6f}"]


def registrar(esc, sweep, cenario, n, W, fase, tempos, valor, entrada):
    esc.writerow(linha_csv(sweep, cenario, n, W, fase, tempos, valor, entrada))
    media = statistics.fmean(tempos)
    desvio = statistics.stdev(tempos) if len(tempos) > 1 else 0.0
    print(f"{sweep:<12} {cenario:<14} n={n:<4} W={W:<7} fase={fase:<9} "
          f"media={media:12.3f} ms  desvio={desvio:10.3f} ms  valor={valor}", flush=True)
    return media


def executar(esc, sweep, cenario, n, W, reps, orcamento):
    w, v = gerar_entrada(cenario, n, W)
    r = medir(w, v, W, reps, orcamento)
    if r is None:
        print(f"{sweep:<12} n={n}: custo estimado acima do orçamento; fim desta fase", flush=True)
        return None
    tempos, valor = r
    return registrar(esc, sweep, cenario, n, W, "principal", tempos, valor, assinatura_entrada(w, v))


def main():
    ap = argparse.ArgumentParser(description="Força bruta (mochila 0/1) - experimento")
    ap.add_argument("--testar", action="store_true", help="roda os testes de corretude")
    ap.add_argument("--rapido", action="store_true", help="execução curta (não vale para o relatório)")
    ap.add_argument("--reps", type=int, default=None, help="repetições por tamanho (15 a 30)")
    ap.add_argument("--saida", default=f"resultados_{ALGORITMO}_{LINGUAGEM}", help="prefixo dos arquivos")
    ap.add_argument("--limite-s", type=float, default=None, help="limite de viabilidade (s)")
    ap.add_argument("--orcamento", type=float, default=None,
                    help="custo máximo estimado (reps x 1ª execução) por tamanho (s)")
    args = ap.parse_args()
    if args.testar:
        return testar()

    reps = args.reps or (5 if args.rapido else 20)
    orcamento = args.orcamento or (3.0 if args.rapido else 300.0)
    limite = args.limite_s or (2.0 if args.rapido else 60.0)
    if not args.rapido and not 15 <= reps <= 30:
        ap.error("--reps deve ficar entre 15 e 30")

    texto_ambiente = ambiente(reps, orcamento, limite)
    print(texto_ambiente + "\n", flush=True)

    candidatos = list(range(10, 41, 2))
    ultimo_n, ultimo_t = None, 0.0
    with open(args.saida + ".csv", "w", newline="", encoding="utf-8") as arq:
        esc = csv.writer(arq)
        esc.writerow(CABECALHO)

        # Fase principal: n crescendo, W = 10n, caso médio (mesmas entradas dos outros 3 arquivos)
        for n in candidatos:
            media = executar(esc, "comparacao", "aleatorio", n, 10 * n, reps, orcamento)
            if media is None:
                break
            arq.flush()
            ultimo_n, ultimo_t = n, media / 1000.0

        # Casos forçados: mesmo n e W, entradas diferentes
        n_c = min(18, ultimo_n)
        for cenario in CENARIOS:
            executar(esc, "cenarios", cenario, n_c, 10 * n_c, reps, orcamento)
            arq.flush()

        # Fase de limite: uma execução por n, até passar do limite de viabilidade
        viavel = ultimo_n
        n = ultimo_n + 1
        while True:
            previsto = ultimo_t * 2 * n / (n - 1)
            if previsto > 1.5 * limite:
                print(f"limite       n={n}: previsto ~{previsto:.0f} s (> {limite:.0f} s); parando", flush=True)
                break
            W = 10 * n
            w, v = gerar_entrada("aleatorio", n, W)
            t0 = time.perf_counter_ns()
            valor = forca_bruta(w, v, W)
            t_s = (time.perf_counter_ns() - t0) / 1e9
            registrar(esc, "limite", "aleatorio", n, W, "limite", [t_s * 1000.0], valor,
                      assinatura_entrada(w, v))
            arq.flush()
            if t_s > limite:
                break
            viavel, ultimo_t = n, t_s
            n += 1

    resumo = f"maior n viável em até {limite:.0f} s (uma execução): {viavel}"
    print("\n" + resumo)
    with open(args.saida + "_ambiente.txt", "w", encoding="utf-8") as f:
        f.write(texto_ambiente + "\n" + resumo + "\n")
    print(f"Resultados em {args.saida}.csv e {args.saida}_ambiente.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
