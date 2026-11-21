CC = gcc
CFLAGS = -O2
LDFLAGS = -lm

BUILD_DIR = build
RESULTADOS_DIR = resultados
GRAFICOS_DIR = graficos

EXEC_FB = $(BUILD_DIR)/forca_bruta_c
EXEC_PD = $(BUILD_DIR)/programacao_dinamica_c
EXEC_MEM = $(BUILD_DIR)/memoria_c

.PHONY: all dirs compilar testar resultados memoria graficos clean

all: compilar testar resultados memoria graficos

dirs:
	@mkdir -p $(BUILD_DIR) $(RESULTADOS_DIR) $(GRAFICOS_DIR)

compilar: dirs $(EXEC_FB) $(EXEC_PD)

$(EXEC_FB): forca_bruta.c
	$(CC) $(CFLAGS) -o $(EXEC_FB) forca_bruta.c $(LDFLAGS)

$(EXEC_PD): programacao_dinamica.c
	$(CC) $(CFLAGS) -o $(EXEC_PD) programacao_dinamica.c $(LDFLAGS)

testar: compilar
	py testes.py

resultados: dirs compilar
	./$(EXEC_FB) --flags "-O2" --saida $(RESULTADOS_DIR)/resultados_forca_bruta_c
	./$(EXEC_PD) --flags "-O2" --saida $(RESULTADOS_DIR)/resultados_programacao_dinamica_c
	py forca_bruta.py --saida $(RESULTADOS_DIR)/resultados_forca_bruta_python
	py programacao_dinamica.py --saida $(RESULTADOS_DIR)/resultados_programacao_dinamica_python

memoria:
	py memoria.py

graficos: dirs
	py graficos.py --dir $(RESULTADOS_DIR) --saida $(GRAFICOS_DIR)
	py testes.py --resultados $(RESULTADOS_DIR)

clean:
	rm -rf $(BUILD_DIR)/ $(RESULTADOS_DIR)/ $(GRAFICOS_DIR)/
	rm -rf __pycache__/