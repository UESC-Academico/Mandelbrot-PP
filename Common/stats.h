#ifndef STATS_H
#define STATS_H

typedef struct
{
    double max;
    double min;
    double media;
    double fbc;
} Statistics;

// Função que calcula as estatísticas de máximo, mínimo, média e FBC dos vetores de métricas
void get_all_statistics(int n, 
                        const long long *pixels, 
                        const long long *iters, 
                        const double *times,
                        Statistics *s_pixels, 
                        Statistics *s_iters, 
                        Statistics *s_times);

#endif
