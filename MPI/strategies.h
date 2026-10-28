#ifndef STRATEGIES_H
#define STRATEGIES_H

#include "../Common/mandelbrot.h"

#define TAG_WORK   1
#define TAG_RESULT 2
#define TAG_DONE   3

#define STRAT_BLOCK   0
#define STRAT_CYCLIC  1
#define STRAT_DYNAMIC 2

typedef struct
{
    long long pixels;
    long long iters;
    double comp_time;
    double comm_time;
} ProcessMetrics;

// Função que lê a variável de ambiente MPI_SCHEDULE (ex: "dynamic,8")
void get_mpi_schedule(int height, int size, int *strategy, int *chunk);

// Estratégia 1: Decomposição estática por blocos contíguos
void run_block(int rank, 
               int size, 
               const MandelbrotParams *params, 
               int *matrix, 
               ProcessMetrics *metrics);

// Estratégia 2: Distribuição estática cíclica de linhas
void run_cyclic(int rank, 
                int size, 
                int chunk, 
                const MandelbrotParams *params, 
                int *matrix, 
                ProcessMetrics *metrics);

// Estratégia 3: Esquema mestre-trabalhador dinâmico
void run_dynamic(int rank, 
                 int size, 
                 int chunk, 
                 const MandelbrotParams *params, 
                 int *matrix, 
                 ProcessMetrics *metrics);

#endif
