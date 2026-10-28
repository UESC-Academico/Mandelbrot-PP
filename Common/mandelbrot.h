#ifndef MANDELBROT_H
#define MANDELBROT_H

typedef struct
{
    int width;
    int height;
    int max_iter;
    double re_min;
    double re_max;
    double im_min;
    double im_max;
} MandelbrotParams;

// Função que inicializa os parâmetros do conjunto de Mandelbrot
void init_params(int argc, char *argv[], MandelbrotParams *params);

// Função que calcula o número de iterações para o conjunto de Mandelbrot
int mandelbrot(int x, int y, const MandelbrotParams *params);

#endif
