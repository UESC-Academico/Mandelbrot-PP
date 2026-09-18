#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <omp.h>

//Função que mede o tempo em segundos
double get_time()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}

int mandelbrot(int x, int y, int width, int height, int max_iter, double re_min, double re_max, double im_min, double im_max)
{
    
}

int main(int argc, char *argv[])
{
    // Parâmetros do conjunto de Mandelbrot
    int width = 4096;
    int height = 4096;
    int max_iter = 1000;
    double re_min = -2.0, re_max = 1.0;
    double im_min = -1.5, im_max = 1.5;

    // Alocação de memória para a matriz de pixels
    int *matriz = (int *)malloc((size_t)width * height * sizeof(int));
    if (!matriz) {
        printf("Erro de alocacao de memoria.\n");
        return 1;
    }

    // Início do cronômetro 
    double t_inicio = get_time();

    // Cálculo do conjunto de Mandelbrot
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            matriz[y * width + x] = mandelbrot(x, y, width, height, max_iter, re_min, re_max, im_min, im_max);
        }
    }

    // Fim do cronômetro
    double t_fim = get_time();
    printf("Tempo de calculo: %.4f segundos\n", t_fim - t_inicio);

    // Salvar Arquivo Binário
    FILE *fbin = fopen("mandelbrot_matriz.bin", "wb");
    if (fbin) {
        fwrite(matriz, sizeof(int), (size_t)width * height, fbin);
        fclose(fbin);
    }

    return 0;
}