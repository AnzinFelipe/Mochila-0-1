/*
 * Algoritmo B (programação dinâmica) para a mochila 0/1 - experimento de desempenho em C.
 *
 * Compilar:  gcc -O2 -o programacao_dinamica_c programacao_dinamica.c -lm
 * Uso:
 *   ./programacao_dinamica_c --testar        testes de corretude (imprime a "assinatura")
 *   ./programacao_dinamica_c --rapido        execução curta, só para conferir se tudo funciona
 *   ./programacao_dinamica_c --flags "-O2"   experimento completo (registra as flags no relatório)
 *
 * Opções: --reps N (15 a 30, padrão 20)  --saida PREFIXO  --orcamento 300
 *         --n-max 800  --w-max 12800
 * Saídas: <PREFIXO>.csv (uma linha por tamanho) e <PREFIXO>_ambiente.txt.
 * Só o tempo de pd_preencher() é medido (a reconstrução dos itens é opcional e fica fora da
 * medição); geração de entrada, CSV e impressão ficam fora da medição.
 */
#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <strings.h>
#include <sys/utsname.h>
#include <unistd.h>
#endif

#define LINGUAGEM "c"
#define ALGORITMO "programacao_dinamica"
#define SEMENTE_BASE 20261120ULL
#define FNV_BASE 14695981039346656037ULL
#define FNV_PRIMO 1099511628211ULL
#define MAX_N 1024

enum { ALEATORIO = 0, TODOS_PESADOS = 1, TODOS_CABEM = 2 };
static const char *NOME_CENARIO[] = {"aleatorio", "todos_pesados", "todos_cabem"};

static volatile long long sumidouro; /* impede o compilador de descartar resultados */

/* ------------------------------------------------------------------------ */
/* Algoritmo B: programação dinâmica, O(n * W)                              */
/* ------------------------------------------------------------------------ */
/* Devolve a tabela (vetor contíguo de (n+1) x (W+1)); quem chama libera com free.
 * dp[i][j] = maior valor usando os i primeiros itens com capacidade j; ótimo em dp[n][W]. */
static int *pd_preencher(const int *w, const int *v, int n, int W) {
    size_t cols = (size_t)W + 1;
    int *dp = calloc((size_t)(n + 1) * cols, sizeof(int));
    if (!dp) {
        fprintf(stderr, "memória insuficiente (n=%d, W=%d)\n", n, W);
        exit(1);
    }
    for (int i = 1; i <= n; i++) {
        const int *anterior = dp + (size_t)(i - 1) * cols;
        int *atual = dp + (size_t)i * cols;
        int wi = w[i - 1], vi = v[i - 1];
        for (int j = 0; j <= W; j++) {
            if (wi <= j) {
                int naoLevando = anterior[j];
                int levando = anterior[j - wi] + vi;
                atual[j] = levando > naoLevando ? levando : naoLevando;
            } else {
                atual[j] = anterior[j];
            }
        }
    }
    return dp;
}

/* OPCIONAL (fora da medição): índices (1..n) dos itens da solução. Devolve a quantidade. */
static int pd_reconstruir(const int *dp, const int *w, int n, int W, int *escolhidos) {
    size_t cols = (size_t)W + 1;
    int j = W, qtd = 0;
    for (int i = n; i >= 1; i--) {
        if (dp[(size_t)i * cols + j] != dp[(size_t)(i - 1) * cols + j]) {
            escolhidos[qtd++] = i;
            j -= w[i - 1];
        }
    }
    return qtd;
}

static double f_teorica(int n, int W) { return (double)n * (double)W; }

/* ------------------------------------------------------------------------ */
/* Gerador de entradas (idêntico nos 4 arquivos: LCG de 64 bits + semente)  */
/* ------------------------------------------------------------------------ */
static uint64_t estado;

static int sortear(int lo, int hi) {
    estado = estado * 6364136223846793005ULL + 1442695040888963407ULL;
    return lo + (int)((estado >> 33) % (uint64_t)(hi - lo + 1));
}

static void gerar_entrada(int cenario, int n, int W, int *w, int *v) {
    estado = SEMENTE_BASE + (uint64_t)n * 1000003ULL + (uint64_t)W * 10007ULL +
             (uint64_t)cenario * 101ULL;
    int limite = (cenario == TODOS_CABEM) ? W / n : 2 * W / n;
    if (limite < 1) limite = 1;
    for (int i = 0; i < n; i++) {
        w[i] = (cenario == TODOS_PESADOS) ? W + 1 + sortear(0, 50) : sortear(1, limite);
        v[i] = sortear(1, 100);
    }
}

static uint64_t fnv(uint64_t h, uint64_t x) { return (h ^ x) * FNV_PRIMO; }

static void assinatura_entrada(const int *w, const int *v, int n, char *saida) {
    uint64_t h = FNV_BASE;
    for (int i = 0; i < n; i++) h = fnv(h, (uint64_t)w[i]);
    for (int i = 0; i < n; i++) h = fnv(h, (uint64_t)v[i]);
    sprintf(saida, "%016llx", (unsigned long long)h);
}

/* ------------------------------------------------------------------------ */
/* Testes de corretude                                                      */
/* ------------------------------------------------------------------------ */
/* Implementação independente (recursão exaustiva), usada só nos testes. */
static long long referencia(const int *w, const int *v, int n, int i, int cap) {
    if (i == n) return 0;
    long long melhor = referencia(w, v, n, i + 1, cap);
    if (w[i] <= cap) {
        long long com = v[i] + referencia(w, v, n, i + 1, cap - w[i]);
        if (com > melhor) melhor = com;
    }
    return melhor;
}

static int testar(void) {
    static const int Ws[] = {0, 5, 20, 60, 150};
    uint64_t h = FNV_BASE;
    int total = 0, w[MAX_N], v[MAX_N], escolhidos[MAX_N];
    for (int n = 1; n <= 12; n++)
        for (int a = 0; a < 5; a++)
            for (int c = 0; c < 3; c++) {
                int W = Ws[a];
                gerar_entrada(c, n, W, w, v);
                int *dp = pd_preencher(w, v, n, W);
                long long obtido = dp[(size_t)n * ((size_t)W + 1) + W];
                long long esperado = referencia(w, v, n, 0, W);
                int qtd = pd_reconstruir(dp, w, n, W, escolhidos);
                long long pt = 0, vt = 0;
                for (int q = 0; q < qtd; q++) {
                    pt += w[escolhidos[q] - 1];
                    vt += v[escolhidos[q] - 1];
                }
                int ok_itens = (pt <= W && vt == obtido);
                free(dp);
                if (obtido != esperado || !ok_itens) {
                    printf("FALHA: %s n=%d W=%d: obtido=%lld esperado=%lld itens_ok=%d\n",
                           NOME_CENARIO[c], n, W, obtido, esperado, ok_itens);
                    return 1;
                }
                h = fnv(h, (uint64_t)obtido);
                total++;
            }
    printf("TESTES OK: %d instancias conferidas com a implementação de referência\n", total);
    printf("assinatura=%016llx   (as 4 implementações devem imprimir a mesma assinatura)\n",
           (unsigned long long)h);
    return 0;
}

/* ------------------------------------------------------------------------ */
/* Ambiente (CPU, RAM, SO, compilador, flags)                               */
/* ------------------------------------------------------------------------ */
static void cpu_nome(char *s, size_t t) {
#ifdef _WIN32
    const char *e = getenv("PROCESSOR_IDENTIFIER");
    snprintf(s, t, "%s", e ? e : "desconhecida");
#else
    FILE *f = fopen("/proc/cpuinfo", "r");
    if (f) {
        char l[512];
        while (fgets(l, sizeof l, f)) {
            if (strncasecmp(l, "model name", 10) == 0) {
                char *p = strchr(l, ':');
                if (p) {
                    p++;
                    while (*p == ' ') p++;
                    p[strcspn(p, "\n")] = 0;
                    snprintf(s, t, "%s", p);
                    fclose(f);
                    return;
                }
            }
        }
        fclose(f);
    }
    f = popen("sysctl -n machdep.cpu.brand_string 2>/dev/null", "r");
    if (f) {
        if (fgets(s, (int)t, f)) {
            s[strcspn(s, "\n")] = 0;
            pclose(f);
            if (s[0]) return;
        } else {
            pclose(f);
        }
    }
    snprintf(s, t, "desconhecida");
#endif
}

static void ram_total(char *s, size_t t) {
#ifdef _WIN32
    MEMORYSTATUSEX m;
    m.dwLength = sizeof m;
    GlobalMemoryStatusEx(&m);
    snprintf(s, t, "%.1f GB", (double)m.ullTotalPhys / (1024.0 * 1024.0 * 1024.0));
#else
    FILE *f = fopen("/proc/meminfo", "r");
    if (f) {
        char l[256];
        while (fgets(l, sizeof l, f)) {
            long long kb;
            if (sscanf(l, "MemTotal: %lld kB", &kb) == 1) {
                snprintf(s, t, "%.1f GB", (double)kb / 1024.0 / 1024.0);
                fclose(f);
                return;
            }
        }
        fclose(f);
    }
    f = popen("sysctl -n hw.memsize 2>/dev/null", "r");
    if (f) {
        long long b;
        if (fscanf(f, "%lld", &b) == 1) {
            snprintf(s, t, "%.1f GB", (double)b / (1024.0 * 1024.0 * 1024.0));
            pclose(f);
            return;
        }
        pclose(f);
    }
    snprintf(s, t, "desconhecida");
#endif
}

static void so_nome(char *s, size_t t) {
#ifdef _WIN32
    const char *e = getenv("OS");
    snprintf(s, t, "Windows (%s)", e ? e : "?");
#else
    struct utsname u;
    if (uname(&u) == 0) snprintf(s, t, "%s %s %s", u.sysname, u.release, u.machine);
    else snprintf(s, t, "desconhecido");
#endif
}

static void compilador_nome(char *s, size_t t) {
#if defined(__clang__)
    snprintf(s, t, "clang %s", __clang_version__);
#elif defined(__GNUC__)
    snprintf(s, t, "gcc %s", __VERSION__);
#elif defined(_MSC_VER)
    snprintf(s, t, "msvc %d", _MSC_VER);
#else
    snprintf(s, t, "desconhecido");
#endif
}

static void montar_ambiente(char *buf, size_t t, const char *flags, int reps, double orcamento) {
    char cpu[256], ram[64], so[256], comp[256], data[64];
    time_t agora = time(NULL);
    strftime(data, sizeof data, "%Y-%m-%d %H:%M:%S", localtime(&agora));
    cpu_nome(cpu, sizeof cpu);
    ram_total(ram, sizeof ram);
    so_nome(so, sizeof so);
    compilador_nome(comp, sizeof comp);
#ifdef __OPTIMIZE__
    const char *otim = "otimização ativa (-O1 ou superior)";
#else
    const char *otim = "SEM otimização (compile com -O2)";
#endif
    snprintf(buf, t,
             "data: %s\n"
             "algoritmo/linguagem: " ALGORITMO " / " LINGUAGEM "\n"
             "CPU: %s\n"
             "RAM: %s\n"
             "sistema operacional: %s\n"
             "compilador: %s\n"
             "flags de compilação: %s [%s]\n"
             "semente base: %llu (gerador LCG de 64 bits, igual nas 4 implementações)\n"
             "repetições por tamanho: %d (+1 execução de aquecimento descartada)\n"
             "orçamento por tamanho: %.0f s\n"
             "relógio: clock_gettime(CLOCK_MONOTONIC) / QueryPerformanceCounter\n",
             data, cpu, ram, so, comp, flags ? flags : "(não informado; use --flags \"-O2\")", otim,
             (unsigned long long)SEMENTE_BASE, reps, orcamento);
}

/* ------------------------------------------------------------------------ */
/* Medição                                                                  */
/* ------------------------------------------------------------------------ */
static uint64_t agora_ns(void) {
#ifdef _WIN32
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&c);
    return (uint64_t)((double)c.QuadPart * 1e9 / (double)f.QuadPart);
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
#endif
}

typedef struct {
    double media, desvio, min, mediana;
} Estat;

static int cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static Estat estatisticas(const double *t, int r) {
    Estat e;
    double *c = malloc((size_t)r * sizeof(double)), soma = 0, var = 0;
    memcpy(c, t, (size_t)r * sizeof(double));
    qsort(c, (size_t)r, sizeof(double), cmp_d);
    e.min = c[0];
    e.mediana = (r % 2) ? c[r / 2] : (c[r / 2 - 1] + c[r / 2]) / 2.0;
    for (int i = 0; i < r; i++) soma += c[i];
    e.media = soma / r;
    for (int i = 0; i < r; i++) var += (c[i] - e.media) * (c[i] - e.media);
    e.desvio = r > 1 ? sqrt(var / (r - 1)) : 0.0; /* desvio-padrão amostral */
    free(c);
    return e;
}

static void registrar(FILE *csv, const char *sweep, int cenario, int n, int W, const double *tempos,
                      int reps, long long valor, const char *sig) {
    Estat e = estatisticas(tempos, reps);
    double f = f_teorica(n, W);
    fprintf(csv, "%s,%s,%s,%s,%d,%d,principal,%d,%.6f,%.6f,%.6f,%.6f,%lld,%s,%.0f,%.6f\n",
            LINGUAGEM, ALGORITMO, sweep, NOME_CENARIO[cenario], n, W, reps, e.media, e.desvio, e.min,
            e.mediana, valor, sig, f, e.media * 1e6 / f);
    printf("%-16s %-14s n=%-5d W=%-7d media=%12.3f ms  desvio=%10.3f ms  valor=%lld\n", sweep,
           NOME_CENARIO[cenario], n, W, e.media, e.desvio, valor);
    fflush(stdout);
}

static void executar(FILE *csv, const char *sweep, int cenario, int n, int W, int reps,
                     double orcamento) {
    int *w = malloc((size_t)n * sizeof(int)), *v = malloc((size_t)n * sizeof(int));
    char sig[32];
    double tempos[64];
    gerar_entrada(cenario, n, W, w, v);
    assinatura_entrada(w, v, n, sig);
    size_t cols = (size_t)W + 1;

    uint64_t t0 = agora_ns();
    int *dp = pd_preencher(w, v, n, W); /* aquecimento: descartado */
    double aquecimento_s = (double)(agora_ns() - t0) / 1e9;
    long long valor = dp[(size_t)n * cols + W];
    free(dp);
    if (aquecimento_s * reps > orcamento) {
        printf("%-16s n=%d W=%d: custo estimado acima do orçamento; pulado\n", sweep, n, W);
        free(w);
        free(v);
        return;
    }
    for (int r = 0; r < reps; r++) {
        t0 = agora_ns();
        dp = pd_preencher(w, v, n, W);
        uint64_t t1 = agora_ns();
        tempos[r] = (double)(t1 - t0) / 1e6;
        valor = dp[(size_t)n * cols + W];
        sumidouro += valor;
        free(dp);
    }
    registrar(csv, sweep, cenario, n, W, tempos, reps, valor, sig);
    free(w);
    free(v);
}

int main(int argc, char **argv) {
    int testar_flag = 0, rapido = 0, reps = 0, n_max = 0, w_max = 0;
    double orcamento = 0;
    const char *flags = NULL;
    char prefixo[256];
    snprintf(prefixo, sizeof prefixo, "resultados_%s_%s", ALGORITMO, LINGUAGEM);

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--testar")) testar_flag = 1;
        else if (!strcmp(argv[i], "--rapido")) rapido = 1;
        else if (!strcmp(argv[i], "--reps") && i + 1 < argc) reps = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--saida") && i + 1 < argc) snprintf(prefixo, sizeof prefixo, "%s", argv[++i]);
        else if (!strcmp(argv[i], "--orcamento") && i + 1 < argc) orcamento = atof(argv[++i]);
        else if (!strcmp(argv[i], "--n-max") && i + 1 < argc) n_max = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--w-max") && i + 1 < argc) w_max = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--flags") && i + 1 < argc) flags = argv[++i];
        else {
            fprintf(stderr,
                    "uso: %s [--testar] [--rapido] [--reps N] [--saida PREFIXO] [--orcamento S] "
                    "[--n-max N] [--w-max W] [--flags \"-O2\"]\n", argv[0]);
            return 1;
        }
    }
    if (testar_flag) return testar();

    if (!reps) reps = rapido ? 5 : 20;
    if (orcamento <= 0) orcamento = rapido ? 3.0 : 300.0;
    if (!n_max) n_max = rapido ? 100 : 800;
    if (!w_max) w_max = rapido ? 800 : 12800;
    if (!rapido && (reps < 15 || reps > 30)) {
        fprintf(stderr, "--reps deve ficar entre 15 e 30\n");
        return 1;
    }
    if (n_max > MAX_N * 64) n_max = MAX_N * 64;

    char amb[4096], caminho[300];
    montar_ambiente(amb, sizeof amb, flags, reps, orcamento);
    printf("%s\n", amb);

    snprintf(caminho, sizeof caminho, "%s.csv", prefixo);
    FILE *csv = fopen(caminho, "w");
    if (!csv) {
        perror(caminho);
        return 1;
    }
    fprintf(csv, "linguagem,algoritmo,sweep,cenario,n,W,fase,reps,media_ms,desvio_ms,min_ms,"
                 "mediana_ms,valor,assinatura_entrada,f_teorica,ns_por_unidade_f\n");

    /* 1) mesmas entradas da força bruta (n pequeno, W = 10n): comparar os dois algoritmos */
    for (int n = 10; n <= (rapido ? 20 : 30); n += 2) {
        executar(csv, "comparacao", ALEATORIO, n, 10 * n, reps, orcamento);
        fflush(csv);
    }
    /* 2) escala em n (geométrica), W = 10n: esperado O(n^2) nesta configuração */
    for (int n = 25; n <= n_max; n *= 2) {
        executar(csv, "escala_n", ALEATORIO, n, 10 * n, reps, orcamento);
        fflush(csv);
    }
    /* 3) escala em W (geométrica), n fixo: esperado O(W) */
    for (int W = 100; W <= w_max; W *= 2) {
        executar(csv, "escala_w", ALEATORIO, 100, W, reps, orcamento);
        fflush(csv);
    }
    /* 4) casos forçados: mesmo n e W (inclui o tamanho comparável com a força bruta) */
    for (int c = 0; c < 3; c++) {
        executar(csv, "cenarios", c, 18, 180, reps, orcamento);
        fflush(csv);
    }
    int n_g = rapido ? 100 : 400, W_g = rapido ? 1000 : 4000;
    for (int c = 0; c < 3; c++) {
        executar(csv, "cenarios_grande", c, n_g, W_g, reps, orcamento);
        fflush(csv);
    }
    fclose(csv);

    snprintf(caminho, sizeof caminho, "%s_ambiente.txt", prefixo);
    FILE *fa = fopen(caminho, "w");
    if (fa) {
        fputs(amb, fa);
        fclose(fa);
    }
    printf("\nResultados em %s.csv e %s\n", prefixo, caminho);
    return 0;
}
