CC = gcc
MPICC = mpicc
CFLAGS = -O3 -Wall -ICommon
OMPFLAGS = -fopenmp

COMMON_SRC = Common/mandelbrot.c Common/io.c Common/stats.c
SERIAL_SRC = Serial/mandelbrot_sequencial.c
OPENMP_SRC = OpenMP/mandelbrot_openmp.c
MPI_SRC = MPI/mandelbrot_mpi.c MPI/strategies.c

SERIAL_BIN = mandelbrot_sequencial
OPENMP_BIN = mandelbrot_openmp
MPI_BIN = mandelbrot_mpi

all: serial openmp mpi

serial: $(SERIAL_SRC) Common/mandelbrot.c Common/io.c
	$(CC) $(CFLAGS) $(SERIAL_SRC) Common/mandelbrot.c Common/io.c -o $(SERIAL_BIN)

openmp: $(OPENMP_SRC) $(COMMON_SRC)
	$(CC) $(CFLAGS) $(OMPFLAGS) $(OPENMP_SRC) $(COMMON_SRC) -o $(OPENMP_BIN)

mpi: $(MPI_SRC) $(COMMON_SRC)
	$(MPICC) $(CFLAGS) $(MPI_SRC) $(COMMON_SRC) -o $(MPI_BIN)

clean:
	rm -f $(SERIAL_BIN) $(OPENMP_BIN) $(MPI_BIN) *.exe *.bin *.ppm *.txt *.csv Results/OpenMP/*.csv Results/MPI/*.csv

.PHONY: all serial openmp mpi clean
