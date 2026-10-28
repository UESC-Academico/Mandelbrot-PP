#include "stats.h"

// Função que calcula as estatísticas de máximo, mínimo, média e FBC dos vetores de métricas
void get_all_statistics(int n, 
                        const long long *pixels, 
                        const long long *iters, 
                        const double *times,
                        Statistics *s_pixels, 
                        Statistics *s_iters, 
                        Statistics *s_times)
{
    s_pixels->max = (double)pixels[0]; 
    s_pixels->min = (double)pixels[0]; 
    s_pixels->media = 0.0;

    s_iters->max  = (double)iters[0];  
    s_iters->min  = (double)iters[0];  
    s_iters->media  = 0.0;

    s_times->max  = times[0];          
    s_times->min  = times[0];          
    s_times->media  = 0.0;

    for (int i = 0; i < n; i++)
    {
        double p = (double)pixels[i];
        double it = (double)iters[i];
        double t = times[i];

        if (p > s_pixels->max) s_pixels->max = p;
        if (p < s_pixels->min) s_pixels->min = p;
        s_pixels->media += p;

        if (it > s_iters->max) s_iters->max = it;
        if (it < s_iters->min) s_iters->min = it;
        s_iters->media += it;

        if (t > s_times->max) s_times->max = t;
        if (t < s_times->min) s_times->min = t;
        s_times->media += t;
    }

    s_pixels->media /= n;
    s_iters->media /= n;
    s_times->media /= n;

    s_pixels->fbc = s_pixels->max > 0.0 ? (s_pixels->max - s_pixels->min) / s_pixels->max : 0.0;
    s_iters->fbc  = s_iters->max > 0.0 ? (s_iters->max - s_iters->min) / s_iters->max : 0.0;
    s_times->fbc  = s_times->max > 0.0 ? (s_times->max - s_times->min) / s_times->max : 0.0;
}
