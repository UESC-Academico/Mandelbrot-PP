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
    return 0;
}