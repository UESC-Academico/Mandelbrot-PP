CC = gcc
CFLAGS = -O3 -Wall -ICommon
OMPFLAGS = -fopenmp

COMMON_SRC = Common/mandelbrot.c Common/io.c Common/stats.c
SERIAL_SRC = Serial/mandelbrot_sequencial.c
OPENMP_SRC = OpenMP/mandelbrot_paralelo.c

SERIAL_BIN = mandelbrot_sequencial
OPENMP_BIN = mandelbrot_paralelo

all: serial openmp

serial: $(SERIAL_SRC) Common/mandelbrot.c Common/io.c
	$(CC) $(CFLAGS) $(SERIAL_SRC) Common/mandelbrot.c Common/io.c -o $(SERIAL_BIN)

openmp: $(OPENMP_SRC) $(COMMON_SRC)
	$(CC) $(CFLAGS) $(OMPFLAGS) $(OPENMP_SRC) $(COMMON_SRC) -o $(OPENMP_BIN)

clean:
	rm -f $(SERIAL_BIN) $(OPENMP_BIN) *.exe *.bin *.ppm *.txt *.csv Results/*.csv

.PHONY: all serial openmp clean
