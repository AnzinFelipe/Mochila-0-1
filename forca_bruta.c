/*
 * Algoritmo A (força bruta) para a mochila 0/1 - experimento de desempenho em C.
 *
 * Compilar:  gcc -O2 -o forca_bruta_c forca_bruta.c -lm
 * Uso:
 *   ./forca_bruta_c --testar                 testes de corretude (imprime a "assinatura")
 *   ./forca_bruta_c --rapido                 execução curta, só para conferir se tudo funciona
 *   ./forca_bruta_c --flags "-O2"            experimento completo (registra as flags no relatório)
 *
 * Opções: --reps N (15 a 30, padrão 20)  --saida PREFIXO  --limite-s 60  --orcamento 300
 * Saídas: <PREFIXO>.csv (uma linha por tamanho) e <PREFIXO>_ambiente.txt.
 * Só o tempo de forca_bruta() é medido; geração de entrada, CSV e impressão ficam fora.
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
#define ALGORITMO "forca_bruta"
#define SEMENTE_BASE 20261120ULL
#define FNV_BASE 14695981039346656037ULL
#define FNV_PRIMO 1099511628211ULL
#define MAX_N 64

enum { ALEATORIO = 0, TODOS_PESADOS = 1, TODOS_CABEM = 2 };
static const char *NOME_CENARIO[] = {"aleatorio", "todos_pesados", "todos_cabem"};

static volatile long long sumidouro; /* impede o compilador de descartar resultados */

/* ------------------------------------------------------------------------ */
/* Algoritmo A: força bruta, O(2^n * n)                                     */
/* ------------------------------------------------------------------------ */
static long long forca_bruta(const int *w, const int *v, int n, int W) {
    long long melhor = 0;
    for (uint64_t combinacao = 0; combinacao < (1ULL << n); combinacao++) {
        long long pesoTotal = 0, valorTotal = 0;
        for (int i = 0; i < n; i++) {
            if ((combinacao >> i) & 1ULL) {
                pesoTotal += w[i];
                valorTotal += v[i];
            }
        }
        if (pesoTotal <= W && valorTotal > melhor) melhor = valorTotal;
    }
    return melhor;
}

static double f_teorica(int n, int W) {
    (void)W;
    return (double)n * (double)(1ULL << n);
}

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
/* Implementação independente (PD com vetor unidimensional), usada só nos testes. */
static long long referencia(const int *w, const int *v, int n, int W) {
    long long *dp = calloc((size_t)W + 1, sizeof(long long));
    for (int i = 0; i < n; i++)
        for (int j = W; j >= w[i]; j--)
            if (dp[j - w[i]] + v[i] > dp[j]) dp[j] = dp[j - w[i]] + v[i];
    long long r = dp[W];
    free(dp);
    return r;
}

static int testar(void) {
    static const int Ws[] = {0, 5, 20, 60, 150};
    uint64_t h = FNV_BASE;
    int total = 0, w[MAX_N], v[MAX_N];
    for (int n = 1; n <= 12; n++)
        for (int a = 0; a < 5; a++)
            for (int c = 0; c < 3; c++) {
                int W = Ws[a];
                gerar_entrada(c, n, W, w, v);
                long long obtido = forca_bruta(w, v, n, W), esperado = referencia(w, v, n, W);
                if (obtido != esperado) {
                    printf("FALHA: %s n=%d W=%d: obtido=%lld esperado=%lld\n", NOME_CENARIO[c], n,
                           W, obtido, esperado);
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

static void montar_ambiente(char *buf, size_t t, const char *flags, int reps, double orcamento,
                            double limite) {
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
             "orçamento por tamanho: %.0f s; limite de viabilidade: %.0f s\n"
             "relógio: clock_gettime(CLOCK_MONOTONIC) / QueryPerformanceCounter\n",
             data, cpu, ram, so, comp, flags ? flags : "(não informado; use --flags \"-O2\")", otim,
             (unsigned long long)SEMENTE_BASE, reps, orcamento, limite);
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

/* Grava uma linha do CSV (mesmas colunas dos outros 3 arquivos) e imprime no terminal. */
static double registrar(FILE *csv, const char *sweep, int cenario, int n, int W, const char *fase,
                        const double *tempos, int reps, long long valor, const char *sig) {
    Estat e = estatisticas(tempos, reps);
    double f = f_teorica(n, W);
    fprintf(csv, "%s,%s,%s,%s,%d,%d,%s,%d,%.6f,%.6f,%.6f,%.6f,%lld,%s,%.0f,%.6f\n", LINGUAGEM,
            ALGORITMO, sweep, NOME_CENARIO[cenario], n, W, fase, reps, e.media, e.desvio, e.min,
            e.mediana, valor, sig, f, e.media * 1e6 / f);
    printf("%-12s %-14s n=%-4d W=%-7d fase=%-9s media=%12.3f ms  desvio=%10.3f ms  valor=%lld\n",
           sweep, NOME_CENARIO[cenario], n, W, fase, e.media, e.desvio, valor);
    fflush(stdout);
    return e.media;
}

/* Devolve a média em ms, ou -1 se (reps x 1ª execução) passar do orçamento. */
static double executar(FILE *csv, const char *sweep, int cenario, int n, int W, int reps,
                       double orcamento) {
    int w[MAX_N], v[MAX_N];
    char sig[32];
    double tempos[64];
    gerar_entrada(cenario, n, W, w, v);
    assinatura_entrada(w, v, n, sig);

    uint64_t t0 = agora_ns();
    long long valor = forca_bruta(w, v, n, W); /* aquecimento: descartado */
    double aquecimento_s = (double)(agora_ns() - t0) / 1e9;
    sumidouro += valor;
    if (aquecimento_s * reps > orcamento) {
        printf("%-12s n=%d: custo estimado acima do orçamento; fim desta fase\n", sweep, n);
        return -1.0;
    }
    for (int r = 0; r < reps; r++) {
        t0 = agora_ns();
        valor = forca_bruta(w, v, n, W);
        uint64_t t1 = agora_ns();
        sumidouro += valor;
        tempos[r] = (double)(t1 - t0) / 1e6;
    }
    return registrar(csv, sweep, cenario, n, W, "principal", tempos, reps, valor, sig);
}

int main(int argc, char **argv) {
    int testar_flag = 0, rapido = 0, reps = 0;
    double limite = 0, orcamento = 0;
    const char *flags = NULL;
    char prefixo[256];
    snprintf(prefixo, sizeof prefixo, "resultados_%s_%s", ALGORITMO, LINGUAGEM);

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--testar")) testar_flag = 1;
        else if (!strcmp(argv[i], "--rapido")) rapido = 1;
        else if (!strcmp(argv[i], "--reps") && i + 1 < argc) reps = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--saida") && i + 1 < argc) snprintf(prefixo, sizeof prefixo, "%s", argv[++i]);
        else if (!strcmp(argv[i], "--limite-s") && i + 1 < argc) limite = atof(argv[++i]);
        else if (!strcmp(argv[i], "--orcamento") && i + 1 < argc) orcamento = atof(argv[++i]);
        else if (!strcmp(argv[i], "--flags") && i + 1 < argc) flags = argv[++i];
        else {
            fprintf(stderr,
                    "uso: %s [--testar] [--rapido] [--reps N] [--saida PREFIXO] [--limite-s S] "
                    "[--orcamento S] [--flags \"-O2\"]\n", argv[0]);
            return 1;
        }
    }
    if (testar_flag) return testar();

    if (!reps) reps = rapido ? 5 : 20;
    if (orcamento <= 0) orcamento = rapido ? 3.0 : 300.0;
    if (limite <= 0) limite = rapido ? 2.0 : 60.0;
    if (!rapido && (reps < 15 || reps > 30)) {
        fprintf(stderr, "--reps deve ficar entre 15 e 30\n");
        return 1;
    }

    char amb[4096], caminho[300];
    montar_ambiente(amb, sizeof amb, flags, reps, orcamento, limite);
    printf("%s\n", amb);

    snprintf(caminho, sizeof caminho, "%s.csv", prefixo);
    FILE *csv = fopen(caminho, "w");
    if (!csv) {
        perror(caminho);
        return 1;
    }
    fprintf(csv, "linguagem,algoritmo,sweep,cenario,n,W,fase,reps,media_ms,desvio_ms,min_ms,"
                 "mediana_ms,valor,assinatura_entrada,f_teorica,ns_por_unidade_f\n");

    /* Fase principal: n crescendo, W = 10n, caso médio (mesmas entradas dos outros 3 arquivos) */
    int ultimo_n = 10;
    double ultimo_t = 0;
    for (int n = 10; n <= 40; n += 2) {
        double media = executar(csv, "comparacao", ALEATORIO, n, 10 * n, reps, orcamento);
        if (media < 0) break;
        fflush(csv);
        ultimo_n = n;
        ultimo_t = media / 1000.0;
    }

    /* Casos forçados: mesmo n e W, entradas diferentes */
    int n_c = ultimo_n < 18 ? ultimo_n : 18;
    for (int c = 0; c < 3; c++) {
        executar(csv, "cenarios", c, n_c, 10 * n_c, reps, orcamento);
        fflush(csv);
    }

    /* Fase de limite: uma execução por n, até passar do limite de viabilidade */
    int viavel = ultimo_n;
    for (int n = ultimo_n + 1; n < MAX_N - 1 && n <= 62; n++) {
        double previsto = ultimo_t * 2.0 * n / (n - 1);
        if (previsto > 1.5 * limite) {
            printf("limite       n=%d: previsto ~%.0f s (> %.0f s); parando\n", n, previsto, limite);
            break;
        }
        int W = 10 * n, w[MAX_N], v[MAX_N];
        char sig[32];
        gerar_entrada(ALEATORIO, n, W, w, v);
        assinatura_entrada(w, v, n, sig);
        uint64_t t0 = agora_ns();
        long long valor = forca_bruta(w, v, n, W);
        double t_s = (double)(agora_ns() - t0) / 1e9;
        sumidouro += valor;
        double t_ms = t_s * 1000.0;
        registrar(csv, "limite", ALEATORIO, n, W, "limite", &t_ms, 1, valor, sig);
        fflush(csv);
        if (t_s > limite) break;
        viavel = n;
        ultimo_t = t_s;
    }
    fclose(csv);

    char resumo[128];
    snprintf(resumo, sizeof resumo, "maior n viável em até %.0f s (uma execução): %d", limite, viavel);
    printf("\n%s\n", resumo);
    snprintf(caminho, sizeof caminho, "%s_ambiente.txt", prefixo);
    FILE *fa = fopen(caminho, "w");
    if (fa) {
        fprintf(fa, "%s%s\n", amb, resumo);
        fclose(fa);
    }
    printf("Resultados em %s.csv e %s\n", prefixo, caminho);
    return 0;
}
