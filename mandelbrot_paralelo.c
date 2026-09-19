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

// Função que calcula o máximo, mínimo e média de um vetor de doubles
static Statistics get_statistics(const double *v, int n)
{
    Statistics s = {
        v[0],
        v[0],
        0.0
    };

    for (int i = 0; i < n; i++)
    {
        if (v[i] > s.max)
            s.max = v[i];

        if (v[i] < s.min)
            s.min = v[i];

        s.media += v[i];
    }
    s.media /= n;
    return s;
}

// Função que calcula o número de iterações para o conjunto de Mandelbrot
int mandelbrot(int x, int y, int width, int height, int max_iter, double re_min, double re_max, double im_min, double im_max)
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

    // Paralelização do loop externo
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

    double *iter_per_thr_double = (double *)malloc(nthreads * sizeof(double));
    double *pixels_per_thr_double = (double *)malloc(nthreads * sizeof(double));
    for (int i = 0; i < nthreads; i++) 
    {
        iter_per_thr_double[i] = (double)iter_per_thr[i];
        pixels_per_thr_double[i] = (double)pixels_per_thr[i];
    }

    Statistics iter_stats = get_statistics(iter_per_thr_double, nthreads);
    Statistics pixels_stats = get_statistics(pixels_per_thr_double, nthreads);
    Statistics time_stats = get_statistics(time_per_thr, nthreads);


    // Salvar Arquivo Binário
    FILE *fbin = fopen("mandelbrot_matriz.bin", "wb");
    if (fbin) 
    {
        fwrite(matriz, sizeof(int), (size_t)width * height, fbin);
        fclose(fbin);
    }

    // Salvar imagem no formato PPM
    FILE *fppm = fopen("mandelbrot.ppm", "w");
    if (fppm) 
    {
        fprintf(fppm, "P3\n%d %d\n255\n", width, height);
        for (int i = 0; i < width * height; i++) 
        {
            int n = matriz[i];
            int r = (n * 2) % 256;
            int g = (n * 4) % 256;
            int b = (n * 13) % 256;

            if (n == max_iter) 
            { 
                r = g = b = 0; 
            }

            fprintf(fppm, "%d %d %d ", r, g, b);
        }
        fclose(fppm);
    }

    free(matriz);

    return 0;
}