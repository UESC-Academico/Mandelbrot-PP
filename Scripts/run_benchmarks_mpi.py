import array
import csv
import filecmp
import math
import os
import re
import statistics
import subprocess
import sys

RESULTS_DIR = "Results/MPI/CSV"
OPENMP_CSV_DIR = "Results/OpenMP/CSV"
DEFAULT_REPEATS = 5


def get_cli_config():
    repeats = DEFAULT_REPEATS
    stat_mode = "mean" if "--mean" in sys.argv else "median"
    for arg in sys.argv[1:]:
        if arg.startswith("--repeats="):
            repeats = max(1, int(arg.split("=", 1)[1]))
    return repeats, stat_mode


def parse_time(output):
    match = re.search(r"Tempo de execucao:\s*([0-9.]+)", output)
    return float(match.group(1)) if match else 0.0


def aggregate_rows(runs, stat_mode="median"):
    if not runs:
        return {}
    if len(runs) == 1:
        return runs[0]
    if stat_mode == "median":
        sorted_runs = sorted(runs, key=lambda r: float(r["total_time"]))
        return sorted_runs[len(sorted_runs) // 2]

    agg = dict(runs[0])
    num_keys = [
        "total_time", "comm_time", "master_time", "io_time",
        "time_max", "time_min", "time_avg", "time_max_avg", "time_fbc",
    ]
    for k in num_keys:
        if k in agg:
            vals = [float(r[k]) for r in runs]
            agg[k] = f"{statistics.mean(vals):.6f}"
    return agg


def detect_mpirun_flags():
    try:
        res = subprocess.run(["mpirun", "--version"], capture_output=True, text=True, check=False)
        ver_text = (res.stdout or "") + (res.stderr or "")
        if "Open MPI" in ver_text or "OpenRTE" in ver_text:
            return ["--oversubscribe"]
    except FileNotFoundError:
        print("Erro: 'mpirun' nao encontrado. Instale o OpenMPI ou MPICH (ex: sudo apt install openmpi-bin libopenmpi-dev).")
        sys.exit(1)
    return []


def verify_matrices(serial_bin, mpi_bin):
    if filecmp.cmp(serial_bin, mpi_bin, shallow=False):
        return True, 0.0, 0

    with open(serial_bin, "rb") as f1, open(mpi_bin, "rb") as f2:
        a1 = array.array("i")
        a2 = array.array("i")
        a1.frombytes(f1.read())
        a2.frombytes(f2.read())

    if len(a1) != len(a2):
        return False, 100.0, -1

    diff_count = 0
    max_diff = 0
    for v1, v2 in zip(a1, a2):
        d = abs(v1 - v2)
        if d > 0:
            diff_count += 1
            max_diff = max(max_diff, d)

    pct_diff = (diff_count / len(a1)) * 100.0
    is_valid = (pct_diff <= 0.01) and (max_diff <= 1)
    return is_valid, pct_diff, max_diff


def run_serial(width=4096, mode="normal", skip_io=True, skip_ppm=True, repeats=DEFAULT_REPEATS, stat_mode="median"):
    cmd = ["./mandelbrot_sequencial", str(width)]
    if mode == "desbalanceamento":
        cmd.append("desbalanceamento")

    times = []
    for i in range(repeats):
        env = os.environ.copy()
        if skip_io or i > 0:
            env["SKIP_IO"] = "1"
        elif skip_ppm:
            env["SKIP_PPM"] = "1"

        res = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        times.append(parse_time(res.stdout))

    return statistics.mean(times) if stat_mode == "mean" else statistics.median(times)


def run_mpi(
    mpirun_flags,
    width=4096,
    mode="normal",
    nprocs=4,
    strategy="block",
    chunk=1,
    skip_io=True,
    skip_ppm=True,
    repeats=DEFAULT_REPEATS,
    stat_mode="median",
):
    cmd = ["mpirun"] + mpirun_flags + ["-np", str(nprocs), "./mandelbrot_mpi", str(width)]
    if mode == "desbalanceamento":
        cmd.append("desbalanceamento")

    runs = []
    csv_path = None
    fieldnames = None

    for i in range(repeats):
        env = os.environ.copy()
        env["OMPI_MCA_rmaps_base_oversubscribe"] = "1"
        if skip_io or i > 0:
            env["SKIP_IO"] = "1"
        elif skip_ppm:
            env["SKIP_PPM"] = "1"

        if strategy == "block" or chunk is None or chunk == 0:
            env["MPI_SCHEDULE"] = strategy
        else:
            env["MPI_SCHEDULE"] = f"{strategy},{chunk}"

        res = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

        match = re.search(r"Estatisticas salvas em:\s*(.+\.csv)", res.stdout)
        csv_path = match.group(1).strip() if match else None
        if csv_path and os.path.exists(csv_path):
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                runs.append(next(reader))

    chosen = aggregate_rows(runs, stat_mode=stat_mode)
    if csv_path and fieldnames and chosen and len(runs) > 1:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(chosen)
    return chosen


def load_cached_serial_times():
    cached = {}
    weak_omp = f"{OPENMP_CSV_DIR}/resumo_escalabilidade_fraca.csv"
    if os.path.exists(weak_omp):
        with open(weak_omp, "r", newline="") as f:
            for r in csv.DictReader(f):
                cached[int(r["resolucao"])] = float(r["tempo_serial"])
    return cached


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    mpirun_flags = detect_mpirun_flags()
    repeats, stat_mode = get_cli_config()
    stat_label = "media" if stat_mode == "mean" else "mediana"
    print(f"Configuracao de benchmark: {repeats} repeticoes por teste (estatistica: {stat_label})")

    max_procs = os.cpu_count() or 4
    proc_list = [p for p in [1, 2, 4, 6, 8, 12, 16] if p <= max_procs]
    if max_procs not in proc_list:
        proc_list.append(max_procs)

    configs = [
        ("block", 0),
        ("cyclic", 1), ("cyclic", 8), ("cyclic", 32), ("cyclic", 128),
        ("dynamic", 1), ("dynamic", 8), ("dynamic", 32), ("dynamic", 128),
    ]

    subprocess.run(["make", "serial", "mpi"], check=True)

    # 1. Teste de Corretude (nas 3 estrategias) e Caso Base Serial
    print("\n=== 1. TESTE DE CORRETUDE E CASO BASE SERIAL (4096x4096) ===")
    t_serial_normal = run_serial(4096, "normal", skip_io=False, skip_ppm=True, repeats=repeats, stat_mode=stat_mode)
    print(f"Tempo Serial (Normal 4096, {stat_label} de {repeats}x): {t_serial_normal:.6f} s")

    io_time_ref = 0.0
    for idx, strat in enumerate(["block", "cyclic", "dynamic"]):
        # Na primeira estrategia salva o .bin + .ppm para medir o tempo completo de I/O; nas demais salva o .bin para o cmp
        row_c = run_mpi(
            mpirun_flags, 4096, "normal", nprocs=max_procs, strategy=strat, chunk=1,
            skip_io=False, skip_ppm=(idx > 0), repeats=1, stat_mode=stat_mode
        )
        if idx == 0:
            io_time_ref = float(row_c.get("io_time", 0.0))
        ok, pct_diff, max_diff = verify_matrices("mandelbrot_matriz.bin", "mandelbrot_mpi_matriz.bin")
        status_str = "IGUAIS" if (ok and max_diff == 0) else (f"VALIDO (diff={pct_diff:.4f}%, max={max_diff})" if ok else "DIFERENTES")
        print(f"Corretude [{strat:<7}]: {status_str} | Tempo Escrita Binario: {float(row_c.get('io_time', 0.0)):.6f} s")
    print(f"Tempo Total de Escrita em Disco (.bin + .ppm): {io_time_ref:.6f} s")

    # 2. Estrategias e Chunk no Input Padrao (4096x4096, MAX_ITER=1000)
    print(f"\n=== 2. CASOS DE TESTE ESTRATEGIA/CHUNK (4096x4096, {max_procs} processos) ===")
    print(f"{'Strategy':<10} {'Chunk':<8} {'Tempo (s)':>11} {'Comm (s)':>10} {'Mestre (s)':>11} {'Speedup':>9} {'Efic.(%)':>10} {'FBC':>10} {'Fator(max/avg)':>15}")
    with open(f"{RESULTS_DIR}/resumo_estrategia_chunk.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow([
            "strategy", "chunk", "processes", "tempo", "comm_time", "master_time", "io_time",
            "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fbc", "fator_max_avg"
        ])
        for strat, ch in configs:
            row = run_mpi(mpirun_flags, 4096, "normal", nprocs=max_procs, strategy=strat, chunk=ch, repeats=repeats, stat_mode=stat_mode)
            t = float(row["total_time"])
            t_comm = float(row["comm_time"])
            t_mast = float(row["master_time"])
            t_min = float(row["time_min"])
            t_avg = float(row["time_avg"])
            t_max = float(row["time_max"])
            fbc = float(row["time_fbc"])
            fator = float(row["time_max_avg"])
            speedup = t_serial_normal / t
            efic = (speedup / max_procs) * 100.0
            ch_label = "padrao" if ch == 0 else str(ch)
            print(f"{strat:<10} {ch_label:<8} {t:>11.6f} {t_comm:>10.6f} {t_mast:>11.6f} {speedup:>9.3f} {efic:>10.2f} {fbc:>10.6f} {fator:>15.6f}")
            writer.writerow([
                strat, ch_label, max_procs, f"{t:.6f}", f"{t_comm:.6f}", f"{t_mast:.6f}", f"{io_time_ref:.6f}",
                f"{t_serial_normal:.6f}", f"{speedup:.3f}", f"{efic:.2f}",
                f"{t_min:.6f}", f"{t_avg:.6f}", f"{t_max:.6f}", f"{fbc:.6f}", f"{fator:.6f}"
            ])

    # 3. Escalabilidade Forte por Estrategia (4096x4096, variando processos para block, cyclic,1 e dynamic,1)
    print("\n=== 3. ESCALABILIDADE FORTE POR ESTRATEGIA (4096x4096) ===")
    print(f"{'Strategy':<10} {'Procs':<7} {'Tempo (s)':>11} {'Comm (s)':>10} {'Mestre (s)':>11} {'Speedup':>9} {'Efic.(%)':>10} {'FBC':>10}")
    strong_mpi_dynamic = {}
    with open(f"{RESULTS_DIR}/resumo_escalabilidade_forte.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow([
            "strategy", "chunk", "processes", "tempo", "comm_time", "master_time",
            "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fbc", "fator_max_avg"
        ])
        for strat, ch in [("block", 0), ("cyclic", 1), ("dynamic", 1)]:
            ch_label = "padrao" if ch == 0 else str(ch)
            for np_val in proc_list:
                row = run_mpi(mpirun_flags, 4096, "normal", nprocs=np_val, strategy=strat, chunk=ch, repeats=repeats, stat_mode=stat_mode)
                t = float(row["total_time"])
                t_comm = float(row["comm_time"])
                t_mast = float(row["master_time"])
                t_min = float(row["time_min"])
                t_avg = float(row["time_avg"])
                t_max = float(row["time_max"])
                fbc = float(row["time_fbc"])
                fator = float(row["time_max_avg"])
                speedup = t_serial_normal / t
                efic = (speedup / np_val) * 100.0
                print(f"{strat:<10} {np_val:<7} {t:>11.6f} {t_comm:>10.6f} {t_mast:>11.6f} {speedup:>9.3f} {efic:>10.2f} {fbc:>10.6f}")
                writer.writerow([
                    strat, ch_label, np_val, f"{t:.6f}", f"{t_comm:.6f}", f"{t_mast:.6f}",
                    f"{t_serial_normal:.6f}", f"{speedup:.3f}", f"{efic:.2f}",
                    f"{t_min:.6f}", f"{t_avg:.6f}", f"{t_max:.6f}", f"{fbc:.6f}", f"{fator:.6f}"
                ])
                if strat == "dynamic":
                    strong_mpi_dynamic[np_val] = (t, speedup, efic, fbc, fator)

    # 4. Caso de Desbalanceamento (4096x4096, MAX_ITER=5000, max_procs processos)
    print(f"\n=== 4. CASO DE DESBALANCEAMENTO (4096x4096, MAX_ITER=5000, {max_procs} processos) ===")
    t_serial_desbal = run_serial(4096, "desbalanceamento", repeats=repeats, stat_mode=stat_mode)
    print(f"Tempo Serial (Desbalanceamento 4096, {stat_label} de {repeats}x): {t_serial_desbal:.6f} s")
    print(f"{'Strategy':<10} {'Chunk':<8} {'Tempo (s)':>11} {'Comm (s)':>10} {'Mestre (s)':>11} {'Speedup':>9} {'Efic.(%)':>10} {'FBC':>10} {'Fator(max/avg)':>15}")
    with open(f"{RESULTS_DIR}/resumo_desbalanceamento.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow([
            "strategy", "chunk", "processes", "tempo", "comm_time", "master_time",
            "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fbc", "fator_max_avg"
        ])
        for strat, ch in configs:
            row = run_mpi(mpirun_flags, 4096, "desbalanceamento", nprocs=max_procs, strategy=strat, chunk=ch, repeats=repeats, stat_mode=stat_mode)
            t = float(row["total_time"])
            t_comm = float(row["comm_time"])
            t_mast = float(row["master_time"])
            t_min = float(row["time_min"])
            t_avg = float(row["time_avg"])
            t_max = float(row["time_max"])
            fbc = float(row["time_fbc"])
            fator = float(row["time_max_avg"])
            speedup = t_serial_desbal / t
            efic = (speedup / max_procs) * 100.0
            ch_label = "padrao" if ch == 0 else str(ch)
            print(f"{strat:<10} {ch_label:<8} {t:>11.6f} {t_comm:>10.6f} {t_mast:>11.6f} {speedup:>9.3f} {efic:>10.2f} {fbc:>10.6f} {fator:>15.6f}")
            writer.writerow([
                strat, ch_label, max_procs, f"{t:.6f}", f"{t_comm:.6f}", f"{t_mast:.6f}",
                f"{t_serial_desbal:.6f}", f"{speedup:.3f}", f"{efic:.2f}",
                f"{t_min:.6f}", f"{t_avg:.6f}", f"{t_max:.6f}", f"{fbc:.6f}", f"{fator:.6f}"
            ])

    # 5. Escalabilidade Fraca (trabalho por processo constante)
    if "--skip-weak" not in sys.argv:
        cached_serial = load_cached_serial_times()
        print("\n=== 5. ESCALABILIDADE FRACA (dynamic,1) ===")
        print(f"{'Resolucao':<10} {'Procs':<7} {'Serial (s)':>12} {'Paral. (s)':>12} {'Comm (s)':>10} {'Speedup':>9} {'Efic.(%)':>10} {'FBC':>10}")
        with open(f"{RESULTS_DIR}/resumo_escalabilidade_fraca.csv", "w", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow([
                "resolucao", "processes", "tempo_paralelo", "comm_time", "master_time",
                "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fbc", "fator_max_avg"
            ])
            for np_val in proc_list:
                res_w = round(4096 * math.sqrt(np_val))
                if res_w == 4096:
                    t_ser = t_serial_normal
                elif res_w in cached_serial:
                    t_ser = cached_serial[res_w]
                else:
                    t_ser = run_serial(res_w, "normal", repeats=repeats, stat_mode=stat_mode)

                row = run_mpi(mpirun_flags, res_w, "normal", nprocs=np_val, strategy="dynamic", chunk=1, repeats=repeats, stat_mode=stat_mode)
                t_par = float(row["total_time"])
                t_comm = float(row["comm_time"])
                t_mast = float(row["master_time"])
                t_min = float(row["time_min"])
                t_avg = float(row["time_avg"])
                t_max = float(row["time_max"])
                fbc = float(row["time_fbc"])
                fator = float(row["time_max_avg"])
                speedup = t_ser / t_par
                efic = (speedup / np_val) * 100.0
                print(f"{res_w:<10} {np_val:<7} {t_ser:>12.6f} {t_par:>12.6f} {t_comm:>10.6f} {speedup:>9.3f} {efic:>10.2f} {fbc:>10.6f}")
                writer.writerow([
                    res_w, np_val, f"{t_par:.6f}", f"{t_comm:.6f}", f"{t_mast:.6f}",
                    f"{t_ser:.6f}", f"{speedup:.3f}", f"{efic:.2f}",
                    f"{t_min:.6f}", f"{t_avg:.6f}", f"{t_max:.6f}", f"{fbc:.6f}", f"{fator:.6f}"
                ])

    # 6. Comparacao automatica OpenMP vs MPI (se existir CSV do OpenMP)
    omp_strong_csv = f"{OPENMP_CSV_DIR}/resumo_escalabilidade_forte.csv"
    if os.path.exists(omp_strong_csv) and strong_mpi_dynamic:
        print("\n=== 6. COMPARACAO OPENMP vs MPI (4096x4096, dynamic,1) ===")
        print(f"{'Unidades':<9} {'OMP Tempo(s)':>13} {'MPI Tempo(s)':>13} {'OMP Speedup':>12} {'MPI Speedup':>12} {'OMP Efic.(%)':>13} {'MPI Efic.(%)':>13}")
        with open(omp_strong_csv, "r", newline="") as f_omp, open(f"{RESULTS_DIR}/resumo_comparacao_openmp_mpi.csv", "w", newline="") as f_cmp:
            omp_rows = {int(r["threads"]): r for r in csv.DictReader(f_omp)}
            writer = csv.writer(f_cmp)
            writer.writerow([
                "unidades", "tempo_openmp", "tempo_mpi", "speedup_openmp", "speedup_mpi",
                "eficiencia_openmp", "eficiencia_mpi", "fator_openmp", "fbc_mpi"
            ])
            for u in sorted(strong_mpi_dynamic.keys()):
                if u in omp_rows:
                    r_omp = omp_rows[u]
                    t_omp = float(r_omp["tempo"])
                    s_omp = float(r_omp["speedup"])
                    e_omp = float(r_omp["eficiencia"])
                    f_omp = float(r_omp["fator_max_avg"])
                    t_mpi, s_mpi, e_mpi, fbc_mpi, _ = strong_mpi_dynamic[u]
                    print(f"{u:<9} {t_omp:>13.6f} {t_mpi:>13.6f} {s_omp:>12.3f} {s_mpi:>12.3f} {e_omp:>13.2f} {e_mpi:>13.2f}")
                    writer.writerow([
                        u, f"{t_omp:.6f}", f"{t_mpi:.6f}", f"{s_omp:.3f}", f"{s_mpi:.3f}",
                        f"{e_omp:.2f}", f"{e_mpi:.2f}", f"{f_omp:.6f}", f"{fbc_mpi:.6f}"
                    ])


if __name__ == "__main__":
    main()
