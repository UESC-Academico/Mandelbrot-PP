#ifndef STATS_H
#define STATS_H

typedef struct
{
    double max;
    double min;
    double media;
} Statistics;

// Função que calcula as estatísticas de máximo, mínimo e média dos vetores de métricas
void get_all_statistics(int n, 
                        const long long *pixels, 
                        const long long *iters, 
                        const double *times,
                        Statistics *s_pixels, 
                        Statistics *s_iters, 
                        Statistics *s_times);

// Função que salva o relatório de estatísticas em um arquivo de texto
void save_statistics(const char *filename, 
                     const char *schedule_name, 
                     int chunk, 
                     int nthreads, 
                     int width, 
                     int height, 
                     double total_time,
                     long long *pixels_per_thr, 
                     long long *iter_per_thr, 
                     double *time_per_thr,
                     Statistics pixels_stats, 
                     Statistics iter_stats, 
                     Statistics time_stats);

#endif
