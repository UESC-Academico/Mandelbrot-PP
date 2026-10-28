#include <stdlib.h>
#include <string.h>
#include "mandelbrot.h"

// Função que inicializa os parâmetros do conjunto de Mandelbrot
void init_params(int argc, char *argv[], MandelbrotParams *params)
{
    params->width    = 4096;
    params->height   = 4096;
    params->max_iter = 1000;
    params->re_min   = -2.0;
    params->re_max   = 1.0;
    params->im_min   = -1.5;
    params->im_max   = 1.5;

    if (argc > 1)
    {
        params->width  = atoi(argv[1]);
        params->height = params->width;
    }

    if (argc > 2 && strcmp(argv[2], "desbalanceamento") == 0)
    {
        params->max_iter = 5000;
        params->re_min   = -0.745143887;
        params->re_max   = -0.742143887;
        params->im_min   = 0.130325904;
        params->im_max   = 0.133325904;
    }
}

// Função que calcula o número de iterações para o conjunto de Mandelbrot
int mandelbrot(int x, int y, const MandelbrotParams *params)
{
    double cReal = params->re_min + ((params->re_max - params->re_min) * x) / (params->width - 1.0);
    double cImaginary = params->im_min + ((params->im_max - params->im_min) * y) / (params->height - 1.0);

    double zReal = 0.0, zImaginary = 0.0;
    double zReal2 = 0.0, zImaginary2 = 0.0;
    int n = 0;

    while ((zReal2 + zImaginary2 <= 4.0) && (n < params->max_iter)) 
    {
        zImaginary = 2.0 * zReal * zImaginary + cImaginary;
        zReal = zReal2 - zImaginary2 + cReal;
        zReal2 = zReal * zReal;
        zImaginary2 = zImaginary * zImaginary;
        n++;
    }
    return n;
}
