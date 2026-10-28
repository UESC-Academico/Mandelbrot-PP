#ifndef MANDELBROT_H
#define MANDELBROT_H

// Função que inicializa os parâmetros do conjunto de Mandelbrot
void init_params(int argc, 
                 char *argv[], 
                 int *width, 
                 int *height, 
                 int *max_iter, 
                 double *re_min, 
                 double *re_max, 
                 double *im_min, 
                 double *im_max);

// Função que calcula o número de iterações para o conjunto de Mandelbrot
int mandelbrot(int x, 
               int y, 
               int width, 
               int height, 
               int max_iter, 
               double re_min, 
               double re_max, 
               double im_min, 
               double im_max);

#endif
