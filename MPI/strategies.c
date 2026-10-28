#include <stdlib.h>
#include <string.h>
#include <mpi.h>
#include "strategies.h"

// Função que lê a variável de ambiente MPI_SCHEDULE (ex: "dynamic,8")
void get_mpi_schedule(int height, int size, int *strategy, int *chunk)
{
    *strategy = STRAT_BLOCK;
    *chunk    = 1;

    const char *env_sched = getenv("MPI_SCHEDULE");
    if (env_sched)
    {
        char sched_buf[64];
        strncpy(sched_buf, env_sched, sizeof(sched_buf) - 1);
        sched_buf[sizeof(sched_buf) - 1] = '\0';

        char *comma = strchr(sched_buf, ',');
        if (comma)
        {
            *comma = '\0';
            *chunk = atoi(comma + 1);
            if (*chunk < 1)
            {
                *chunk = 1;
            }
        }

        if (strcmp(sched_buf, "cyclic") == 0)
        {
            *strategy = STRAT_CYCLIC;
        }
        else if (strcmp(sched_buf, "dynamic") == 0)
        {
            *strategy = STRAT_DYNAMIC;
        }
    }

    if (*strategy == STRAT_BLOCK)
    {
        *chunk = height / size;
    }
}

// Função auxiliar que calcula um bloco de linhas e acumula as métricas locais
static void compute_rows(int start_y, 
                         int rows, 
                         const MandelbrotParams *params, 
                         int *out_buf, 
                         ProcessMetrics *metrics)
{
    double t0 = MPI_Wtime();
    for (int i = 0; i < rows; i++)
    {
        int y = start_y + i;
        for (int x = 0; x < params->width; x++)
        {
            int n = mandelbrot(x, y, params);
            out_buf[i * params->width + x] = n;
            metrics->pixels++;
            metrics->iters += n;
        }
    }
    metrics->comp_time += MPI_Wtime() - t0;
}

// Função auxiliar que conta o total de linhas de um processo na distribuição cíclica
static int count_cyclic_rows(int r, int size, int height, int chunk)
{
    int total = 0;
    for (int y0 = r * chunk; y0 < height; y0 += size * chunk)
    {
        int rows = (y0 + chunk <= height) ? chunk : (height - y0);
        total += rows;
    }
    return total;
}

// Estratégia 1: Decomposição estática por blocos contíguos
void run_block(int rank, 
               int size, 
               const MandelbrotParams *params, 
               int *matrix, 
               ProcessMetrics *metrics)
{
    int base_rows  = params->height / size;
    int rem_rows   = params->height % size;
    int local_rows = base_rows + (rank < rem_rows ? 1 : 0);
    int start_y    = rank * base_rows + (rank < rem_rows ? rank : rem_rows);

    size_t alloc_elems = local_rows > 0 ? (size_t)local_rows * params->width : 1;
    int *local_matrix = (int *)malloc(alloc_elems * sizeof(int));

    compute_rows(start_y, local_rows, params, local_matrix, metrics);

    int *recvcounts = NULL;
    int *displs     = NULL;

    if (rank == 0)
    {
        recvcounts = (int *)malloc(size * sizeof(int));
        displs     = (int *)malloc(size * sizeof(int));

        for (int r = 0; r < size; r++)
        {
            int rows_r  = base_rows + (r < rem_rows ? 1 : 0);
            int start_r = r * base_rows + (r < rem_rows ? r : rem_rows);
            recvcounts[r] = rows_r * params->width;
            displs[r]     = start_r * params->width;
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    double t_comm = MPI_Wtime();
    MPI_Gatherv(local_matrix, local_rows * params->width, MPI_INT,
                matrix, recvcounts, displs, MPI_INT,
                0, MPI_COMM_WORLD);
    metrics->comm_time = MPI_Wtime() - t_comm;

    free(local_matrix);
    if (rank == 0)
    {
        free(recvcounts);
        free(displs);
    }
}

// Estratégia 2: Distribuição estática cíclica de linhas
void run_cyclic(int rank, 
                int size, 
                int chunk, 
                const MandelbrotParams *params, 
                int *matrix, 
                ProcessMetrics *metrics)
{
    int local_rows = count_cyclic_rows(rank, size, params->height, chunk);
    size_t alloc_elems = local_rows > 0 ? (size_t)local_rows * params->width : 1;
    int *local_matrix = (int *)malloc(alloc_elems * sizeof(int));

    int row_offset = 0;
    for (int y0 = rank * chunk; y0 < params->height; y0 += size * chunk)
    {
        int rows = (y0 + chunk <= params->height) ? chunk : (params->height - y0);
        compute_rows(y0, rows, params, &local_matrix[row_offset * params->width], metrics);
        row_offset += rows;
    }

    int *recvcounts = NULL;
    int *displs     = NULL;
    int *gather_buf = NULL;

    if (rank == 0)
    {
        recvcounts = (int *)malloc(size * sizeof(int));
        displs     = (int *)malloc(size * sizeof(int));
        gather_buf = (int *)malloc((size_t)params->width * params->height * sizeof(int));

        int offset = 0;
        for (int r = 0; r < size; r++)
        {
            int rows_r = count_cyclic_rows(r, size, params->height, chunk);
            recvcounts[r] = rows_r * params->width;
            displs[r]     = offset;
            offset       += recvcounts[r];
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    double t_comm = MPI_Wtime();
    MPI_Gatherv(local_matrix, local_rows * params->width, MPI_INT,
                gather_buf, recvcounts, displs, MPI_INT,
                0, MPI_COMM_WORLD);

    if (rank == 0)
    {
        for (int r = 0; r < size; r++)
        {
            int src_row = displs[r] / params->width;
            for (int y0 = r * chunk; y0 < params->height; y0 += size * chunk)
            {
                int rows = (y0 + chunk <= params->height) ? chunk : (params->height - y0);
                memcpy(&matrix[y0 * params->width],
                       &gather_buf[src_row * params->width],
                       (size_t)rows * params->width * sizeof(int));
                src_row += rows;
            }
        }
    }
    metrics->comm_time = MPI_Wtime() - t_comm;

    free(local_matrix);
    if (rank == 0)
    {
        free(recvcounts);
        free(displs);
        free(gather_buf);
    }
}

// Estratégia 3: Esquema mestre-trabalhador dinâmico
void run_dynamic(int rank, 
                 int size, 
                 int chunk, 
                 const MandelbrotParams *params, 
                 int *matrix, 
                 ProcessMetrics *metrics)
{
    if (size == 1)
    {
        run_block(rank, size, params, matrix, metrics);
        return;
    }

    if (rank == 0)
    {
        int *assigned_y = (int *)malloc(size * sizeof(int));
        int *recv_buf   = (int *)malloc((size_t)chunk * params->width * sizeof(int));
        int next_y = 0;
        int active_workers = 0;

        double t_comm = MPI_Wtime();
        for (int w = 1; w < size; w++)
        {
            if (next_y < params->height)
            {
                assigned_y[w] = next_y;
                MPI_Send(&next_y, 1, MPI_INT, w, TAG_WORK, MPI_COMM_WORLD);
                next_y += chunk;
                active_workers++;
            }
            else
            {
                MPI_Send(&next_y, 1, MPI_INT, w, TAG_DONE, MPI_COMM_WORLD);
            }
        }

        while (active_workers > 0)
        {
            MPI_Status status;
            MPI_Recv(recv_buf, chunk * params->width, MPI_INT, MPI_ANY_SOURCE, TAG_RESULT, MPI_COMM_WORLD, &status);

            int w    = status.MPI_SOURCE;
            int y0   = assigned_y[w];
            int rows = (y0 + chunk <= params->height) ? chunk : (params->height - y0);

            memcpy(&matrix[y0 * params->width], recv_buf, (size_t)rows * params->width * sizeof(int));

            if (next_y < params->height)
            {
                assigned_y[w] = next_y;
                MPI_Send(&next_y, 1, MPI_INT, w, TAG_WORK, MPI_COMM_WORLD);
                next_y += chunk;
            }
            else
            {
                MPI_Send(&next_y, 1, MPI_INT, w, TAG_DONE, MPI_COMM_WORLD);
                active_workers--;
            }
        }
        metrics->comm_time = MPI_Wtime() - t_comm;

        free(assigned_y);
        free(recv_buf);
    }
    else
    {
        int *local_buf = (int *)malloc((size_t)chunk * params->width * sizeof(int));

        while (1)
        {
            int y0;
            MPI_Status status;

            double t_c0 = MPI_Wtime();
            MPI_Recv(&y0, 1, MPI_INT, 0, MPI_ANY_TAG, MPI_COMM_WORLD, &status);
            metrics->comm_time += MPI_Wtime() - t_c0;

            if (status.MPI_TAG == TAG_DONE)
            {
                break;
            }

            int rows = (y0 + chunk <= params->height) ? chunk : (params->height - y0);
            compute_rows(y0, rows, params, local_buf, metrics);

            double t_c1 = MPI_Wtime();
            MPI_Send(local_buf, rows * params->width, MPI_INT, 0, TAG_RESULT, MPI_COMM_WORLD);
            metrics->comm_time += MPI_Wtime() - t_c1;
        }

        free(local_buf);
    }
}
