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
    MandelbrotParams params;
    init_params(argc, argv, &params);

    int *matrix = (int *)malloc((size_t)params.width * params.height * sizeof(int));
    if (!matrix) 
    {
        printf("Erro de alocacao de memoria.\n");
        return 1;
    }

    double start_t = get_time();

    for (int y = 0; y < params.height; y++) 
    {
        for (int x = 0; x < params.width; x++) 
        {
            matrix[y * params.width + x] = mandelbrot(x, y, &params);
        }
    }

    double end_t = get_time();

    printf("Tempo de execucao: %f segundos\n", end_t - start_t);

    save_binary("mandelbrot_matriz.bin", matrix, params.width, params.height);
    save_image("mandelbrot.ppm", matrix, params.width, params.height, params.max_iter);

    free(matrix);

    return 0;
}
