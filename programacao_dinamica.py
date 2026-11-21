#!/usr/bin/env python3
"""
Algoritmo B (programação dinâmica) para a mochila 0/1 - experimento de desempenho em Python.

Uso:
  python3 programacao_dinamica.py --testar    # testes de corretude (imprime a "assinatura")
  python3 programacao_dinamica.py --rapido    # execução curta, só para conferir se tudo funciona
  python3 programacao_dinamica.py             # experimento completo -> CSV + arquivo de ambiente

Opções: --reps N (15 a 30, padrão 20)  --saida PREFIXO  --orcamento 300
        --n-max 800  --w-max 12800

Saídas: <PREFIXO>.csv (uma linha por tamanho) e <PREFIXO>_ambiente.txt.
Só o tempo de pd_preencher() é medido (a reconstrução dos itens é opcional e fica
fora da medição); geração de entrada, CSV e impressão ficam fora da medição.
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
ALGORITMO = "programacao_dinamica"
SEMENTE_BASE = 20261120
MASCARA64 = (1 << 64) - 1
CENARIOS = ("aleatorio", "todos_pesados", "todos_cabem")
FNV_BASE = 14695981039346656037
FNV_PRIMO = 1099511628211
CABECALHO = ["linguagem", "algoritmo", "sweep", "cenario", "n", "W", "fase", "reps",
             "media_ms", "desvio_ms", "min_ms", "mediana_ms", "valor",
             "assinatura_entrada", "f_teorica", "ns_por_unidade_f"]


# ----------------------------------------------------------------------------
# Algoritmo B: programação dinâmica, O(n * W)
# ----------------------------------------------------------------------------
def pd_preencher(w, v, W):
    """Devolve a tabela dp; o valor ótimo está em dp[n][W].

    dp[i][j] = maior valor usando os i primeiros itens com capacidade j.
    """
    n = len(w)
    dp = [[0] * (W + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        anterior, atual = dp[i - 1], dp[i]
        wi, vi = w[i - 1], v[i - 1]
        for j in range(W + 1):
            if wi <= j:
                nao_levando = anterior[j]
                levando = anterior[j - wi] + vi
                atual[j] = levando if levando > nao_levando else nao_levando
            else:
                atual[j] = anterior[j]
    return dp


def pd_reconstruir(dp, w, W):
    """OPCIONAL (fora da medição): índices (1..n) dos itens da solução."""
    escolhidos = []
    j = W
    for i in range(len(w), 0, -1):
        if dp[i][j] != dp[i - 1][j]:
            escolhidos.append(i)
            j -= w[i - 1]
    escolhidos.reverse()
    return escolhidos


def f_teorica(n, W):
    return n * W


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
    """Implementação independente (recursão exaustiva), usada só nos testes."""
    def rec(i, cap):
        if i == len(w):
            return 0
        melhor = rec(i + 1, cap)
        if w[i] <= cap:
            melhor = max(melhor, v[i] + rec(i + 1, cap - w[i]))
        return melhor
    return rec(0, W)


def testar():
    h = FNV_BASE
    total = 0
    for n in range(1, 13):
        for W in (0, 5, 20, 60, 150):
            for cenario in CENARIOS:
                w, v = gerar_entrada(cenario, n, W)
                dp = pd_preencher(w, v, W)
                obtido = dp[n][W]
                esperado = referencia(w, v, W)
                itens = pd_reconstruir(dp, w, W)
                ok_itens = (sum(w[i - 1] for i in itens) <= W
                            and sum(v[i - 1] for i in itens) == obtido)
                if obtido != esperado or not ok_itens:
                    print(f"FALHA: {cenario} n={n} W={W}: obtido={obtido} esperado={esperado} "
                          f"itens_ok={ok_itens}")
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


def ambiente(reps, orcamento):
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
        f"orçamento por tamanho: {orcamento} s",
        "relógio: time.perf_counter_ns (coleta de lixo desligada durante a medição)",
    ])


# ----------------------------------------------------------------------------
# Medição
# ----------------------------------------------------------------------------
def medir(w, v, W, reps, orcamento_s):
    """Devolve (tempos_ms, valor), ou None se reps x (1ª execução) passar do orçamento."""
    n = len(w)
    t0 = time.perf_counter_ns()
    dp = pd_preencher(w, v, W)  # aquecimento: descartado, serve também para estimar o custo
    aquecimento_s = (time.perf_counter_ns() - t0) / 1e9
    valor = dp[n][W]
    del dp
    if aquecimento_s * reps > orcamento_s:
        return None
    tempos = []
    gc.collect()
    gc.disable()
    try:
        for _ in range(reps):
            t0 = time.perf_counter_ns()
            dp = pd_preencher(w, v, W)
            tempos.append((time.perf_counter_ns() - t0) / 1e6)
            valor = dp[n][W]
            del dp
    finally:
        gc.enable()
    return tempos, valor


def registrar(esc, sweep, cenario, n, W, tempos, valor, entrada):
    f = f_teorica(n, W)
    media = statistics.fmean(tempos)
    desvio = statistics.stdev(tempos) if len(tempos) > 1 else 0.0
    esc.writerow([LINGUAGEM, ALGORITMO, sweep, cenario, n, W, "principal", len(tempos),
                  f"{media:.6f}", f"{desvio:.6f}", f"{min(tempos):.6f}",
                  f"{statistics.median(tempos):.6f}", valor, entrada, f,
                  f"{media * 1e6 / f:.6f}"])
    print(f"{sweep:<16} {cenario:<14} n={n:<5} W={W:<7} media={media:12.3f} ms  "
          f"desvio={desvio:10.3f} ms  valor={valor}", flush=True)


def executar(esc, sweep, cenario, n, W, reps, orcamento):
    w, v = gerar_entrada(cenario, n, W)
    r = medir(w, v, W, reps, orcamento)
    if r is None:
        print(f"{sweep:<16} n={n} W={W}: custo estimado acima do orçamento; pulado", flush=True)
        return
    tempos, valor = r
    registrar(esc, sweep, cenario, n, W, tempos, valor, assinatura_entrada(w, v))


def geometrica(inicio, fim):
    x, saida = inicio, []
    while x <= fim:
        saida.append(x)
        x *= 2
    return saida


def main():
    ap = argparse.ArgumentParser(description="Programação dinâmica (mochila 0/1) - experimento")
    ap.add_argument("--testar", action="store_true", help="roda os testes de corretude")
    ap.add_argument("--rapido", action="store_true", help="execução curta (não vale para o relatório)")
    ap.add_argument("--reps", type=int, default=None, help="repetições por tamanho (15 a 30)")
    ap.add_argument("--saida", default=f"resultados_{ALGORITMO}_{LINGUAGEM}", help="prefixo dos arquivos")
    ap.add_argument("--orcamento", type=float, default=None,
                    help="custo máximo estimado (reps x 1ª execução) por tamanho (s)")
    ap.add_argument("--n-max", type=int, default=None, help="maior n da escala em n (padrão 800)")
    ap.add_argument("--w-max", type=int, default=None, help="maior W da escala em W (padrão 12800)")
    args = ap.parse_args()
    if args.testar:
        return testar()

    reps = args.reps or (5 if args.rapido else 20)
    orcamento = args.orcamento or (3.0 if args.rapido else 300.0)
    n_max = args.n_max or (100 if args.rapido else 800)
    w_max = args.w_max or (800 if args.rapido else 12800)
    if not args.rapido and not 15 <= reps <= 30:
        ap.error("--reps deve ficar entre 15 e 30")

    texto_ambiente = ambiente(reps, orcamento)
    print(texto_ambiente + "\n", flush=True)

    comparacao = list(range(10, 21 if args.rapido else 31, 2))
    n_cenarios = (100, 1000) if args.rapido else (400, 4000)
    with open(args.saida + ".csv", "w", newline="", encoding="utf-8") as arq:
        esc = csv.writer(arq)
        esc.writerow(CABECALHO)

        # 1) mesmas entradas da força bruta (n pequeno, W = 10n): comparar os dois algoritmos
        for n in comparacao:
            executar(esc, "comparacao", "aleatorio", n, 10 * n, reps, orcamento)
            arq.flush()
        # 2) escala em n (geométrica), W = 10n: esperado O(n^2) nesta configuração
        for n in geometrica(25, n_max):
            executar(esc, "escala_n", "aleatorio", n, 10 * n, reps, orcamento)
            arq.flush()
        # 3) escala em W (geométrica), n fixo: esperado O(W)
        for W in geometrica(100, w_max):
            executar(esc, "escala_w", "aleatorio", 100, W, reps, orcamento)
            arq.flush()
        # 4) casos forçados: mesmo n e W (inclui o tamanho comparável com a força bruta)
        for cenario in CENARIOS:
            executar(esc, "cenarios", cenario, 18, 180, reps, orcamento)
            arq.flush()
        for cenario in CENARIOS:
            executar(esc, "cenarios_grande", cenario, n_cenarios[0], n_cenarios[1], reps, orcamento)
            arq.flush()

    with open(args.saida + "_ambiente.txt", "w", encoding="utf-8") as f:
        f.write(texto_ambiente + "\n")
    print(f"\nResultados em {args.saida}.csv e {args.saida}_ambiente.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
