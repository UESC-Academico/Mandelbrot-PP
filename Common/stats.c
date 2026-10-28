#include <stdio.h>
#include "stats.h"

// Função que calcula as estatísticas de máximo, mínimo e média dos vetores de métricas
void get_all_statistics(int n, 
                        const long long *pixels, 
                        const long long *iters, 
                        const double *times,
                        Statistics *s_pixels, 
                        Statistics *s_iters, 
                        Statistics *s_times)
{
    s_pixels->max = (double)pixels[0]; 
    s_pixels->min = (double)pixels[0]; 
    s_pixels->media = 0.0;

    s_iters->max  = (double)iters[0];  
    s_iters->min  = (double)iters[0];  
    s_iters->media  = 0.0;

    s_times->max  = times[0];          
    s_times->min  = times[0];          
    s_times->media  = 0.0;

    for (int i = 0; i < n; i++)
    {
        double p = (double)pixels[i];
        double it = (double)iters[i];
        double t = times[i];

        if (p > s_pixels->max) s_pixels->max = p;
        if (p < s_pixels->min) s_pixels->min = p;
        s_pixels->media += p;

        if (it > s_iters->max) s_iters->max = it;
        if (it < s_iters->min) s_iters->min = it;
        s_iters->media += it;

        if (t > s_times->max) s_times->max = t;
        if (t < s_times->min) s_times->min = t;
        s_times->media += t;
    }

    s_pixels->media /= n;
    s_iters->media /= n;
    s_times->media /= n;
}

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
                     Statistics time_stats)
{
    FILE *ftxt = fopen(filename, "w");
    if (!ftxt)
    {
        printf("Erro ao abrir o arquivo para escrita: %s\n", filename);
        return;
    }

    fprintf(ftxt, "--- Balanceamento de Carga ---\n");
    fprintf(ftxt, "Threads: %d | Schedule: %s | Chunk: %d | Resolucao: %dx%d\n", 
            nthreads, schedule_name, chunk, width, height);
    fprintf(ftxt, "Tempo total de execucao: %f segundos\n\n", total_time);
    
    fprintf(ftxt, "%-8s %14s %16s %14s\n", "Thread", "Pixels Process.", "Iteracoes", "Tempo (s)");
    for (int i = 0; i < nthreads; i++)
    {
        fprintf(ftxt, "%-8d %14lld %16lld %14.6f\n", 
                i, pixels_per_thr[i], iter_per_thr[i], time_per_thr[i]);
    }

    fprintf(ftxt, "\n%-28s %14s %16s %14s\n", "METRICA", "Pixels", "Iteracoes", "Tempo");
    
    fprintf(ftxt, "%-28s %14.0f %16.0f %14.6f\n", "Maximo", 
            pixels_stats.max, iter_stats.max, time_stats.max);
            
    fprintf(ftxt, "%-28s %14.0f %16.0f %14.6f\n", "Minimo", 
            pixels_stats.min, iter_stats.min, time_stats.min);
            
    fprintf(ftxt, "%-28s %14.2f %16.2f %14.6f\n", "Media", 
            pixels_stats.media, iter_stats.media, time_stats.media);

    fprintf(ftxt, "%-28s %14.4f %16.4f %14.4f\n", "Fator de Balanceamento (max/media)", 
            pixels_stats.max / pixels_stats.media, 
            iter_stats.max / iter_stats.media, 
            time_stats.max / time_stats.media);
            
    fprintf(ftxt, "%-28s %14.4f %16.4f %14.4f\n", "Razao (max/min)", 
            pixels_stats.min > 0 ? pixels_stats.max / pixels_stats.min : -1.0, 
            iter_stats.min > 0 ? iter_stats.max / iter_stats.min : -1.0, 
            time_stats.min > 0 ? time_stats.max / time_stats.min : -1.0);

    // CSV formatado
    fprintf(ftxt, "\nCSV,%d,%s,%d,%.6f,%.4f,%.4f,%.4f\n", 
            nthreads, schedule_name, chunk, total_time, 
            pixels_stats.max / pixels_stats.media, 
            iter_stats.max / iter_stats.media, 
            time_stats.max / time_stats.media);
            
    fclose(ftxt);
    printf("Estatisticas salvas em: %s\n", filename);
}
