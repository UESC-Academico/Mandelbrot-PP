#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <omp.h>

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

    // Início do cronômetro com o timer do OpenMP (mais preciso para threads)
    double t_inicio = omp_get_wtime();

    // Paralelização do loop externo
    // collapse(1) ou padrão paralela as linhas (y)
    #pragma omp parallel for schedule(runtime)
    for (int y = 0; y < height; y++) 
    {
        for (int x = 0; x < width; x++) 
        {
            matriz[y * width + x] = mandelbrot(x, y, width, height, max_iter, re_min, re_max, im_min, im_max);
        }
    }

    // Fim do cronômetro
    double t_fim = omp_get_wtime();
    printf("Tempo de execucao: %f segundos\n", t_fim - t_inicio);

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