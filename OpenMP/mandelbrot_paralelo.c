#include <stdio.h>
#include <stdlib.h>
#include <omp.h>
#include "../Common/mandelbrot.h"
#include "../Common/io.h"
#include "../Common/stats.h"

int main(int argc, char *argv[])
{
    // Parâmetros do conjunto de Mandelbrot
    int width, height, max_iter;
    double re_min, re_max, im_min, im_max;

    init_params(argc, argv, &width, &height, &max_iter, &re_min, &re_max, &im_min, &im_max);

    // Alocação de memória para a matriz de pixels
    int *matriz = (int *)malloc((size_t)width * height * sizeof(int));
    if (!matriz) 
    {
        printf("Erro de alocacao de memoria.\n");
        return 1;
    }

    int max_threads = omp_get_max_threads();

    // Alocação de vetores para métricas de cada thread
    long long *pixels_per_thr = (long long *)calloc(max_threads, sizeof(long long));
    long long *iter_per_thr = (long long *)calloc(max_threads, sizeof(long long));
    double *time_per_thr = (double *)calloc(max_threads, sizeof(double));

    if (!pixels_per_thr || !iter_per_thr || !time_per_thr)
    {
        printf("Erro de alocacao das metricas.\n");
        free(matriz);
        return 1;
    }

    int nthreads = 1;

    // Início do cronômetro com o timer do OpenMP 
    double start_t = omp_get_wtime();

    // Cálculo do conjunto de Mandelbrot em paralelo
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
        for (int y = 0; y < height; y++) 
        {
            double t0 = omp_get_wtime();
            for (int x = 0; x < width; x++) 
            {
                int n = mandelbrot(x, y, width, height, max_iter, re_min, re_max, im_min, im_max);
                matriz[y * width + x] = n;

                p_thread++;
                i_thread += n;
            }
            t_thread += omp_get_wtime() - t0;
        }

        pixels_per_thr[tid] = p_thread;
        iter_per_thr[tid] = i_thread;
        time_per_thr[tid] = t_thread;
    }

    // Fim do cronômetro
    double end_t = omp_get_wtime();
    double total_time = end_t - start_t;
    printf("Tempo de execucao: %f segundos\n", total_time);

    // Cálculo das estatísticas de máximo, mínimo e média para pixels, iterações e tempo por thread
    Statistics pixels_stats, iter_stats, time_stats;
    get_all_statistics(nthreads, pixels_per_thr, iter_per_thr, time_per_thr, 
                       &pixels_stats, &iter_stats, &time_stats);

    omp_sched_t kind; 
    int chunk;
    omp_get_schedule(&kind, &chunk); // Obtém o tipo de escalonamento e o tamanho do chunk atual
    
    const char *nomes[] = { "desconhecido", "static", "dynamic", "guided", "auto" };
    int k = (int)kind & 0xFF; // Máscara para obter apenas os bits relevantes
    if (k < 1 || k > 4) 
    {
        k = 0; // Se não for um valor válido, define como "desconhecido"
    }

    // Nome do arquivo de estatísticas baseado no tipo de escalonamento, tamanho do chunk e número de threads
    char filename_stats[100];
    snprintf(filename_stats, sizeof(filename_stats), "estatisticas_%s_%d_threads_%d.txt", nomes[k], chunk, nthreads);

    save_statistics(filename_stats, nomes[k], chunk, nthreads, width, height, total_time,
                    pixels_per_thr, iter_per_thr, time_per_thr,
                    pixels_stats, iter_stats, time_stats);
    
    save_binary("mandelbrot_paralelo_matriz.bin", matriz, width, height);
    save_image("mandelbrot.ppm", matriz, width, height, max_iter);

    free(matriz);
    free(pixels_per_thr);
    free(iter_per_thr);
    free(time_per_thr);

    return 0;
}
