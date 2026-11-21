# Mochila-0/1

Projeto acadêmico para realizar uma análise detalhada da complexidade de tempo, teórica e experimental do problema Mochila 0/1 implementado por 2 algoritmos: Força Bruta e Programação Dinâmica, em duas linguagens de programação diferentes: C e Python.

### Descrição do Problema:
Dados n itens, cada um com peso wi e valor vi, e uma capacidade W, escolher os itens que maximizem o valor total, sem que o peso total exceda a capacidade W. Cada item pode entrar no máximo uma vez ou não entrar (0 ou 1).

### 1º Algoritmo: Força bruta — O(2ⁿ·n):
consiste simplesmente em testar cada um dos O(2ⁿ) subconjuntos, calculando o peso e valor de cada combinação possível de itens, procurando encontrar a combinação com maior valor possível, contanto que o peso não exceda a capacidade W.

### 2º Algoritmo: Programação dinâmica — O(n·W):
A programação dinâmica inicia com zero itens disponíveis e, a cada etapa, acrescenta um novo item ao conjunto considerado. Para cada capacidade, armazena-se na tabela o maior valor possível, comparando o valor de não levar o item com o valor de levá-lo somado ao melhor resultado já calculado para a capacidade restante. Ao final, o valor ótimo está na última célula, e os itens que compõem a solução são identificados percorrendo-se a tabela de trás para frente.

## Requisitos para rodar:
- GCC
- Python3
- Bibliotecas Python: Pandas, Matplotlib e Numpy

Para instalar as bibliotecas:

```
pip install pandas matplotlib numpy
```

## Como executar:
Rode no terminal para executar todas as etapas:
```
make clean
make
```
Caso queira acompanhar cada etapa individualmente rode:
```
make clean
make compilar
make testar
make resultados
make memoria
make graficos
```

## Caminho dos resultados
- /resultados: Tabelas CSV
- /graficos: Gráficos de comparação