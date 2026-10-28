#include <stdio.h>
#include <stdlib.h>
#include <omp.h>
#include "../Common/mandelbrot.h"
#include "../Common/io.h"
#include "../Common/stats.h"

// Função que salva o relatório de estatísticas em formato CSV
void save_statistics(const char *filename, 
                     const char *schedule_name, 
                     int chunk, 
                     int nthreads, 
                     int width, 
                     int height, 
                     double total_time,
                     Statistics pixels_stats, 
                     Statistics iter_stats, 
                     Statistics time_stats)
{
    FILE *fcsv = fopen(filename, "w");
    if (!fcsv)
    {
        printf("Erro ao abrir o arquivo para escrita: %s\n", filename);
        return;
    }

    double pixels_bal = pixels_stats.avg > 0.0 ? pixels_stats.max / pixels_stats.avg : 0.0;
    double iter_bal   = iter_stats.avg > 0.0 ? iter_stats.max / iter_stats.avg : 0.0;
    double time_bal   = time_stats.avg > 0.0 ? time_stats.max / time_stats.avg : 0.0;

    double pixels_ratio = pixels_stats.min > 0.0 ? pixels_stats.max / pixels_stats.min : -1.0;
    double iter_ratio   = iter_stats.min > 0.0 ? iter_stats.max / iter_stats.min : -1.0;
    double time_ratio   = time_stats.min > 0.0 ? time_stats.max / time_stats.min : -1.0;

    fprintf(fcsv,
            "width,height,threads,schedule,chunk,total_time,"
            "time_min,time_avg,time_max,time_fbc,time_max_avg,time_max_min,"
            "pixels_min,pixels_avg,pixels_max,pixels_fbc,pixels_max_avg,pixels_max_min,"
            "iter_min,iter_avg,iter_max,iter_fbc,iter_max_avg,iter_max_min\n");

    fprintf(fcsv,
            "%d,%d,%d,%s,%d,%.6f,"
            "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,"
            "%.0f,%.2f,%.0f,%.6f,%.6f,%.6f,"
            "%.0f,%.2f,%.0f,%.6f,%.6f,%.6f\n",
            width, height, nthreads, schedule_name, chunk, total_time,
            time_stats.min, time_stats.avg, time_stats.max, time_stats.fbc, time_bal, time_ratio,
            pixels_stats.min, pixels_stats.avg, pixels_stats.max, pixels_stats.fbc, pixels_bal, pixels_ratio,
            iter_stats.min, iter_stats.avg, iter_stats.max, iter_stats.fbc, iter_bal, iter_ratio);
            
    fclose(fcsv);
    printf("Estatisticas salvas em: %s\n", filename);
}

int main(int argc, char *argv[])
{
    MandelbrotParams params;
    init_params(argc, argv, &params);

    int *matrix = (int *)malloc((size_t)params.width * params.height * sizeof(int));
    if (!matrix) 
    {
        printf("Erro de alocacao de memoria.\n");
        return 1;
    }

    int max_threads = omp_get_max_threads();

    long long *pixels_per_thr = (long long *)calloc(max_threads, sizeof(long long));
    long long *iter_per_thr   = (long long *)calloc(max_threads, sizeof(long long));
    double *time_per_thr      = (double *)calloc(max_threads, sizeof(double));

    if (!pixels_per_thr || !iter_per_thr || !time_per_thr)
    {
        printf("Erro de alocacao das metricas.\n");
        free(matrix);
        return 1;
    }

    int nthreads = 1;
    double start_t = omp_get_wtime();

    #pragma omp parallel
    {
        int tid = omp_get_thread_num();

        #pragma omp single
        {
            nthreads = omp_get_num_threads();
        }

        long long p_thread = 0;
        long long i_thread = 0;
        double t_thread = 0.0;

        #pragma omp for schedule(runtime)
        for (int y = 0; y < params.height; y++) 
        {
            double t0 = omp_get_wtime();
            for (int x = 0; x < params.width; x++) 
            {
                int n = mandelbrot(x, y, &params);
                matrix[y * params.width + x] = n;

                p_thread++;
                i_thread += n;
            }
            t_thread += omp_get_wtime() - t0;
        }

        pixels_per_thr[tid] = p_thread;
        iter_per_thr[tid]   = i_thread;
        time_per_thr[tid]   = t_thread;
    }

    double end_t = omp_get_wtime();
    double total_time = end_t - start_t;
    printf("Tempo de execucao: %f segundos\n", total_time);

    Statistics pixels_stats, iter_stats, time_stats;
    get_all_statistics(nthreads, pixels_per_thr, iter_per_thr, time_per_thr, 
                       &pixels_stats, &iter_stats, &time_stats);

    omp_sched_t kind; 
    int chunk;
    omp_get_schedule(&kind, &chunk);
    
    const char *schedule_names[] = { "unknown", "static", "dynamic", "guided", "auto" };
    int k = (int)kind & 0xFF;
    if (k < 1 || k > 4) 
    {
        k = 0;
    }

    char filename_stats[120];
    snprintf(filename_stats, sizeof(filename_stats),
             "Results/OpenMP/CSV/estatisticas_%s_%d_threads_%d.csv",
             schedule_names[k], chunk, nthreads);

    save_statistics(filename_stats, schedule_names[k], chunk, nthreads,
                    params.width, params.height, total_time,
                    pixels_stats, iter_stats, time_stats);
    
    save_binary("mandelbrot_paralelo_matriz.bin", matrix, params.width, params.height);
    save_image("mandelbrot.ppm", matrix, params.width, params.height, params.max_iter);

    free(matrix);
    free(pixels_per_thr);
    free(iter_per_thr);
    free(time_per_thr);

    return 0;
}
