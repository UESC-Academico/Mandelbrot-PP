#include <stdlib.h>
#include <string.h>
#include "mandelbrot.h"

// Função que inicializa os parâmetros do conjunto de Mandelbrot
void init_params(int argc, 
                 char *argv[], 
                 int *width, 
                 int *height, 
                 int *max_iter, 
                 double *re_min, 
                 double *re_max, 
                 double *im_min, 
                 double *im_max)
{
    *width = 4096;
    *height = 4096;
    *max_iter = 1000;
    *re_min = -2.0;
    *re_max = 1.0;
    *im_min = -1.5;
    *im_max = 1.5;

    if (argc > 1)
    {
        *width = atoi(argv[1]);
        *height = *width;
    }

    if (argc > 2 && strcmp(argv[2], "desbalanceamento") == 0)
    {
        *max_iter = 5000;
        *re_min = -0.745143887;
        *re_max = -0.742143887;
        *im_min = 0.130325904;
        *im_max = 0.133325904;
    }
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
