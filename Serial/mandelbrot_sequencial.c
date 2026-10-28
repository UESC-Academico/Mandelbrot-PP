#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include "../Common/mandelbrot.h"
#include "../Common/io.h"

// Função que mede o tempo em segundos
double get_time()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}

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

    // Início do cronômetro 
    double t_inicio = get_time();

    // Cálculo do conjunto de Mandelbrot
    for (int y = 0; y < height; y++) 
    {
        for (int x = 0; x < width; x++) 
        {
            matriz[y * width + x] = mandelbrot(x, y, width, height, max_iter, re_min, re_max, im_min, im_max);
        }
    }

    // Fim do cronômetro
    double t_fim = get_time();

    printf("Tempo de execucao: %f segundos\n", t_fim - t_inicio);

    save_binary("mandelbrot_matriz.bin", matriz, width, height);
    save_image("mandelbrot.ppm", matriz, width, height, max_iter);

    free(matriz);

    return 0;
}
