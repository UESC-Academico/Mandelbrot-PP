#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <omp.h>

typedef struct
{
    double max;
    double min;
    double media;
} Statistics;

// Função que calcula as estatísticas de máximo, mínimo e média dos vetores de métricas (pixels, iterações e tempo) por thread
static void get_all_statistics(int n, 
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

// Função que calcula o número de iterações para o conjunto de Mandelbrot
int mandelbrot(int x, 
               int y, 
               int width, 
               int height, 
               int max_iter, 
               double re_min, 
               double re_max, 
               double im_min, 
               double im_max)
{
    double cReal = re_min + ((re_max - re_min) * x) / (width - 1.0);
    double cImaginary = im_min + ((im_max - im_min) * y) / (height - 1.0);

    double zReal = 0.0, zImaginary = 0.0;
    double zReal2 = 0.0, zImaginary2 = 0.0;
    int n = 0;

    while ((zReal2 + zImaginary2 <= 4.0) && (n < max_iter)) 
    {
        zImaginary = 2.0 * zReal * zImaginary + cImaginary;
        zReal = zReal2 - zImaginary2 + cReal;
        zReal2 = zReal * zReal;
        zImaginary2 = zImaginary * zImaginary;
        n++;
    }
    return n;
}

// Função que salva a matriz de pixels em um arquivo binário
void save_binary(const char *filename, int *matrix, int width, int height)
{
    FILE *f = fopen(filename, "wb");
    if (!f) 
    {
        printf("Erro ao abrir o arquivo para escrita: %s\n", filename);
        return;
    }

    fwrite(matrix, sizeof(int), (size_t)width * height, f);
    fclose(f);
    printf("Matriz de pixels salva em: %s\n", filename);
}

// Função que salva a matriz de pixels em um arquivo PPM
void save_image(const char *filename, int *matrix, int width, int height, int max_iter)
{
    FILE *f = fopen(filename, "w");
    if (!f) 
    {
        printf("Erro ao abrir o arquivo para escrita: %s\n", filename);
        return;
    }

    fprintf(f, "P3\n%d %d\n255\n", width, height);
    for (int i = 0; i < width * height; i++) 
    {
        int n = matrix[i];
        int r = (n * 2) % 256;
        int g = (n * 4) % 256;
        int b = (n * 13) % 256;

        if (n == max_iter) 
        { 
            r = g = b = 0; 
        }

        fprintf(f, "%d %d %d ", r, g, b);
    }
    fclose(f);
    printf("Imagem salva em: %s\n", filename);
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
    
    fprintf(ftxt, "%-28s %14.4f %16.4f %14.4f\n", "Fator Desbal. (max/media)", 
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

int main(int argc, char *argv[])
{
    // Parâmetros do conjunto de Mandelbrot
    int width = 4096;
    int height = 4096;
    int max_iter = 1000;
    double re_min = -2.0, re_max = 1.0;
    double im_min = -1.5, im_max = 1.5;

    if (argc > 1)
    {
        width = atoi(argv[1]);
        height = width;
    }

    if (argc > 2 && strcmp(argv[2], "desbalanceamento") == 0)
    {
        max_iter = 5000;
        re_min = -0.745143887;
        re_max = -0.742143887;
        im_min = 0.130325904;
        im_max = 0.133325904;
    }

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