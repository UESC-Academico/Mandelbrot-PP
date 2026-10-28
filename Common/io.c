#include <stdio.h>
#include <stdlib.h>
#include "io.h"

// Função que salva a matriz de pixels em um arquivo binário
void save_binary(const char *filename, int *matrix, int width, int height)
{
    if (getenv("SKIP_IO"))
    {
        return;
    }

    FILE *f = fopen(filename, "wb");
    if (!f) 
    {
        printf("Erro ao abrir o arquivo para escrita: %s\n", filename);
        return;
    }

    fwrite(matrix, sizeof(int), (size_t)width * height, f);
    fclose(f);
    printf("Matriz de pixels salva em: %s\n", filename);
}

// Função que salva a matriz de pixels em um arquivo PPM
void save_image(const char *filename, int *matrix, int width, int height, int max_iter)
{
    if (getenv("SKIP_IO") || getenv("SKIP_PPM"))
    {
        return;
    }

    FILE *f = fopen(filename, "w");
    if (!f) 
    {
        printf("Erro ao abrir o arquivo para escrita: %s\n", filename);
        return;
    }

    setvbuf(f, NULL, _IOFBF, 4 * 1024 * 1024);

    fprintf(f, "P3\n%d %d\n255\n", width, height);
    for (int i = 0; i < width * height; i++) 
    {
        int n = matrix[i];
        int r = (n * 2) % 256;
        int g = (n * 4) % 256;
        int b = (n * 13) % 256;

        if (n == max_iter) 
        { 
            r = g = b = 0; 
        }

        fprintf(f, "%d %d %d ", r, g, b);
    }
    fclose(f);
    printf("Imagem salva em: %s\n", filename);
}
