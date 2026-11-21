/*
 * Driver de medição de memória (C) - mochila 0/1.
 *
 * Reaproveita, SEM alterá-los, forca_bruta.c e programacao_dinamica.c: o main original é
 * renomeado e o arquivo é incluído, de modo que a função medida é exatamente a mesma do
 * experimento de tempo. Quem chama este programa é o memoria.py (não precisa rodar na mão).
 *
 * Compilar (o memoria.py já faz isso):
 *   gcc -O2 -DALG_FB   -o mem_fb_c   memoria_c.c -lm            força bruta
 *   gcc -O2 -DALG_PD   -o mem_pd_c   memoria_c.c -lm            PD (tabela completa)
 *   gcc -O2 -DALG_PD1D -o mem_pd1d_c memoria_c.c -lm            PD (vetor único, extra)
 *   (no Windows acrescente -lpsapi)
 *
 * Uso:  ./mem_pd_c n W
 * Saída (uma linha):  <pico_antes_bytes> <pico_depois_bytes> <valor_otimo>
 * A memória do algoritmo é depois - antes (o "antes" já inclui o processo e a entrada).
 */
#define main experimento_main_original
#if defined(ALG_PD) || defined(ALG_PD1D)
#include "programacao_dinamica.c"
#else
#include "forca_bruta.c"
#endif
#undef main

#ifdef _WIN32
#include <psapi.h>
#else
#include <sys/resource.h>
#endif

/* Pico de memória residente do processo até agora, em bytes (só cresce).
 * Windows: PeakWorkingSetSize. Linux: VmHWM. Outros: ru_maxrss. */
static unsigned long long pico_bytes(void) {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof pmc))
        return (unsigned long long)pmc.PeakWorkingSetSize;
    return 0ULL;
#else
#ifdef __linux__
    /* VmHWM (pico residente DESTE processo). getrusage/ru_maxrss herdaria, no Linux, o pico
     * do processo pai como piso, o que falseia a medição quando o memoria.py inicia o programa. */
    FILE *f = fopen("/proc/self/status", "r");
    if (f) {
        char linha[256];
        long long kb;
        while (fgets(linha, sizeof linha, f)) {
            if (sscanf(linha, "VmHWM: %lld kB", &kb) == 1) {
                fclose(f);
                return (unsigned long long)kb * 1024ULL;
            }
        }
        fclose(f);
    }
#endif
    struct rusage u;
    getrusage(RUSAGE_SELF, &u);
#ifdef __APPLE__
    return (unsigned long long)u.ru_maxrss;          /* macOS: bytes */
#else
    return (unsigned long long)u.ru_maxrss * 1024ULL; /* Linux: KB */
#endif
#endif
}

#ifdef ALG_PD1D
/* Extra: PD com vetor único, O(W) de memória (não reconstrói os itens). */
static long long pd_vetor_unico(const int *w, const int *v, int n, int W) {
    int *dp = calloc((size_t)W + 1, sizeof(int));
    if (!dp) {
        fprintf(stderr, "memória insuficiente\n");
        exit(1);
    }
    for (int i = 0; i < n; i++)
        for (int j = W; j >= w[i]; j--)
            if (dp[j - w[i]] + v[i] > dp[j]) dp[j] = dp[j - w[i]] + v[i];
    long long r = dp[W];
    free(dp);
    return r;
}
#endif

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "uso: %s n W\n", argv[0]);
        return 1;
    }
    int n = atoi(argv[1]), W = atoi(argv[2]);
    int *w = malloc((size_t)n * sizeof(int)), *v = malloc((size_t)n * sizeof(int));
    gerar_entrada(ALEATORIO, n, W, w, v);

    (void)pico_bytes(); /* aquecimento: a 1a leitura carrega páginas da libc e não pode entrar na conta */
    unsigned long long antes = pico_bytes(), depois;
    long long valor;
#if defined(ALG_PD)
    int *dp = pd_preencher(w, v, n, W);
    valor = dp[(size_t)n * ((size_t)W + 1) + W];
    depois = pico_bytes(); /* tabela ainda alocada */
    free(dp);
#elif defined(ALG_PD1D)
    valor = pd_vetor_unico(w, v, n, W);
    depois = pico_bytes(); /* o pico não diminui depois do free */
#else
    valor = forca_bruta(w, v, n, W);
    depois = pico_bytes();
#endif
    printf("%llu %llu %lld\n", antes, depois, valor);
    free(w);
    free(v);
    return 0;
}