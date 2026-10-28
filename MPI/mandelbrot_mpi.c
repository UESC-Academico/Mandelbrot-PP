#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "../Common/mandelbrot.h"
#include "../Common/io.h"
#include "../Common/stats.h"
#include "strategies.h"

// Função que salva o relatório de estatísticas do MPI em formato CSV
void save_statistics(const char *filename, 
                     const char *strategy_name, 
                     int chunk, 
                     int nprocs, 
                     int width, 
                     int height, 
                     double total_time,
                     double comm_time,
                     double master_time,
                     double io_time,
                     Statistics pixels_stats, 
                     Statistics iter_stats, 
                     Statistics time_stats)
{
    FILE *fcsv = fopen(filename, "w");
    if (!fcsv)
    {
        printf("Erro ao abrir o arquivo para escrita: %s\n", filename);
        return;
    }

    double pixels_bal = pixels_stats.avg > 0.0 ? pixels_stats.max / pixels_stats.avg : 0.0;
    double iter_bal   = iter_stats.avg > 0.0 ? iter_stats.max / iter_stats.avg : 0.0;
    double time_bal   = time_stats.avg > 0.0 ? time_stats.max / time_stats.avg : 0.0;

    double pixels_ratio = pixels_stats.min > 0.0 ? pixels_stats.max / pixels_stats.min : -1.0;
    double iter_ratio   = iter_stats.min > 0.0 ? iter_stats.max / iter_stats.min : -1.0;
    double time_ratio   = time_stats.min > 0.0 ? time_stats.max / time_stats.min : -1.0;

    fprintf(fcsv,
            "width,height,processes,strategy,chunk,total_time,comm_time,master_time,io_time,"
            "time_min,time_avg,time_max,time_fbc,time_max_avg,time_max_min,"
            "pixels_min,pixels_avg,pixels_max,pixels_fbc,pixels_max_avg,pixels_max_min,"
            "iter_min,iter_avg,iter_max,iter_fbc,iter_max_avg,iter_max_min\n");

    fprintf(fcsv,
            "%d,%d,%d,%s,%d,%.6f,%.6f,%.6f,%.6f,"
            "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,"
            "%.0f,%.2f,%.0f,%.6f,%.6f,%.6f,"
            "%.0f,%.2f,%.0f,%.6f,%.6f,%.6f\n",
            width, height, nprocs, strategy_name, chunk, total_time, comm_time, master_time, io_time,
            time_stats.min, time_stats.avg, time_stats.max, time_stats.fbc, time_bal, time_ratio,
            pixels_stats.min, pixels_stats.avg, pixels_stats.max, pixels_stats.fbc, pixels_bal, pixels_ratio,
            iter_stats.min, iter_stats.avg, iter_stats.max, iter_stats.fbc, iter_bal, iter_ratio);

    fclose(fcsv);
    printf("Estatisticas salvas em: %s\n", filename);
}

int main(int argc, char *argv[])
{
    int rank, size;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    MandelbrotParams params;
    int strategy = STRAT_BLOCK;
    int chunk    = 1;

    if (rank == 0)
    {
        init_params(argc, argv, &params);
        get_mpi_schedule(params.height, size, &strategy, &chunk);
    }

    // Distribuição dos parâmetros a partir do processo raiz (rank 0) via Broadcast
    MPI_Bcast(&params, sizeof(MandelbrotParams), MPI_BYTE, 0, MPI_COMM_WORLD);
    MPI_Bcast(&strategy, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&chunk, 1, MPI_INT, 0, MPI_COMM_WORLD);

    int *matrix = NULL;
    if (rank == 0)
    {
        matrix = (int *)malloc((size_t)params.width * params.height * sizeof(int));
        if (!matrix)
        {
            printf("Erro de alocacao de memoria.\n");
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }

    ProcessMetrics local_metrics = { 0, 0, 0.0, 0.0 };

    // Sincronização dos processos antes do início do cronômetro
    MPI_Barrier(MPI_COMM_WORLD);
    double start_t = MPI_Wtime();

    if (strategy == STRAT_CYCLIC)
    {
        run_cyclic(rank, size, chunk, &params, matrix, &local_metrics);
    }
    else if (strategy == STRAT_DYNAMIC)
    {
        run_dynamic(rank, size, chunk, &params, matrix, &local_metrics);
    }
    else
    {
        run_block(rank, size, &params, matrix, &local_metrics);
    }

    double total_time = MPI_Wtime() - start_t;

    long long *pixels_per_proc = NULL;
    long long *iter_per_proc   = NULL;
    double *comp_time_per_proc = NULL;
    double *comm_time_per_proc = NULL;

    if (rank == 0)
    {
        pixels_per_proc    = (long long *)calloc(size, sizeof(long long));
        iter_per_proc      = (long long *)calloc(size, sizeof(long long));
        comp_time_per_proc = (double *)calloc(size, sizeof(double));
        comm_time_per_proc = (double *)calloc(size, sizeof(double));
    }

    // Coleta das métricas individuais de cada processo para o rank 0
    MPI_Gather(&local_metrics.pixels, 1, MPI_LONG_LONG, pixels_per_proc, 1, MPI_LONG_LONG, 0, MPI_COMM_WORLD);
    MPI_Gather(&local_metrics.iters, 1, MPI_LONG_LONG, iter_per_proc, 1, MPI_LONG_LONG, 0, MPI_COMM_WORLD);
    MPI_Gather(&local_metrics.comp_time, 1, MPI_DOUBLE, comp_time_per_proc, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Gather(&local_metrics.comm_time, 1, MPI_DOUBLE, comm_time_per_proc, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    if (rank == 0)
    {
        printf("Tempo de execucao: %f segundos\n", total_time);

        double start_io = MPI_Wtime();
        save_binary("mandelbrot_mpi_matriz.bin", matrix, params.width, params.height);
        save_image("mandelbrot.ppm", matrix, params.width, params.height, params.max_iter);
        double io_time = MPI_Wtime() - start_io;

        int stats_offset = (strategy == STRAT_DYNAMIC && size > 1) ? 1 : 0;
        int stats_count  = size - stats_offset;

        Statistics pixels_stats, iter_stats, time_stats;
        get_all_statistics(stats_count,
                           &pixels_per_proc[stats_offset],
                           &iter_per_proc[stats_offset],
                           &comp_time_per_proc[stats_offset],
                           &pixels_stats,
                           &iter_stats,
                           &time_stats);

        double comm_time   = comm_time_per_proc[0];
        double master_time = (strategy == STRAT_DYNAMIC && size > 1) ? comm_time_per_proc[0] : 0.0;

        const char *strategy_names[] = { "block", "cyclic", "dynamic" };
        char filename_stats[120];
        snprintf(filename_stats, sizeof(filename_stats),
                 "Results/MPI/CSV/estatisticas_mpi_%s_%d_np_%d.csv",
                 strategy_names[strategy], chunk, size);

        save_statistics(filename_stats, strategy_names[strategy], chunk, size,
                        params.width, params.height,
                        total_time, comm_time, master_time, io_time,
                        pixels_stats, iter_stats, time_stats);

        free(matrix);
        free(pixels_per_proc);
        free(iter_per_proc);
        free(comp_time_per_proc);
        free(comm_time_per_proc);
    }

    MPI_Finalize();
    return 0;
}
