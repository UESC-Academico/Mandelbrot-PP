#ifndef IO_H
#define IO_H

// Função que salva a matriz de pixels em um arquivo binário
void save_binary(const char *filename, int *matrix, int width, int height);

// Função que salva a matriz de pixels em um arquivo PPM
void save_image(const char *filename, int *matrix, int width, int height, int max_iter);

#endif
