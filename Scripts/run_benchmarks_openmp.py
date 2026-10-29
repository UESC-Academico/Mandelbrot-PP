import csv
import filecmp
import math
import os
import re
import statistics
import subprocess
import sys

RESULTS_DIR = "Results/OpenMP/CSV"
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
    num_keys = ["total_time", "time_max", "time_min", "time_avg", "time_max_avg", "time_fbc"]
    for k in num_keys:
        if k in agg:
            vals = [float(r[k]) for r in runs]
            agg[k] = f"{statistics.mean(vals):.6f}"
    return agg


def run_serial(width=4096, mode="normal", skip_io=True, repeats=DEFAULT_REPEATS, stat_mode="median"):
    cmd = ["./mandelbrot_sequencial", str(width)]
    if mode == "desbalanceamento":
        cmd.append("desbalanceamento")

    times = []
    for i in range(repeats):
        env = os.environ.copy()
        if skip_io or i > 0:
            env["SKIP_IO"] = "1"
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        times.append(parse_time(res.stdout))

    return statistics.mean(times) if stat_mode == "mean" else statistics.median(times)


def run_openmp(width=4096, mode="normal", threads=12, schedule="dynamic", chunk=1, skip_io=True, repeats=DEFAULT_REPEATS, stat_mode="median"):
    cmd = ["./mandelbrot_openmp", str(width)]
    if mode == "desbalanceamento":
        cmd.append("desbalanceamento")

    runs = []
    csv_path = None
    fieldnames = None

    for i in range(repeats):
        env = os.environ.copy()
        if skip_io or i > 0:
            env["SKIP_IO"] = "1"

        env["OMP_NUM_THREADS"] = str(threads)
        if chunk is None or chunk == 0:
            env["OMP_SCHEDULE"] = schedule
        else:
            env["OMP_SCHEDULE"] = f"{schedule},{chunk}"

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


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    repeats, stat_mode = get_cli_config()
    stat_label = "media" if stat_mode == "mean" else "mediana"
    print(f"Configuracao de benchmark: {repeats} repeticoes por teste (estatistica: {stat_label})")

    max_threads = os.cpu_count() or 4
    thread_list = [t for t in [1, 2, 4, 6, 8, 12, 16] if t <= max_threads]
    if max_threads not in thread_list:
        thread_list.append(max_threads)

    configs = [
        ("static", 0), ("static", 1), ("static", 8), ("static", 32), ("static", 128),
        ("dynamic", 1), ("dynamic", 8), ("dynamic", 32), ("dynamic", 128),
        ("guided", 1), ("guided", 8), ("guided", 32), ("guided", 128),
    ]

    subprocess.run(["make", "serial", "openmp"], check=True)

    # 1. Teste de Corretude e Caso Base Serial
    print("\n=== 1. TESTE DE CORRETUDE E CASO BASE SERIAL (4096x4096) ===")
    t_serial_normal = run_serial(4096, "normal", skip_io=False, repeats=repeats, stat_mode=stat_mode)
    run_openmp(4096, "normal", threads=max_threads, schedule="dynamic", chunk=1, skip_io=False, repeats=1, stat_mode=stat_mode)
    is_equal = filecmp.cmp("mandelbrot_matriz.bin", "mandelbrot_paralelo_matriz.bin", shallow=False)
    print(f"Corretude (cmp binarios): {'IGUAIS' if is_equal else 'DIFERENTES'}")
    print(f"Tempo Serial (Normal 4096, {stat_label} de {repeats}x): {t_serial_normal:.6f} s")

    # 2. Casos de Teste Schedule / Chunk
    print(f"\n=== 2. CASOS DE TESTE SCHEDULE/CHUNK (4096x4096, {max_threads} threads) ===")
    print(f"{'Schedule':<10} {'Chunk':<8} {'Tempo (s)':>12} {'Speedup':>10} {'Eficiencia (%)':>16} {'Fator (max/avg)':>17} {'FBC':>12}")
    with open(f"{RESULTS_DIR}/resumo_schedule_chunk.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["schedule", "chunk", "threads", "tempo", "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fator_max_avg", "fbc"])
        for sched, ch in configs:
            row = run_openmp(4096, "normal", threads=max_threads, schedule=sched, chunk=ch, repeats=repeats, stat_mode=stat_mode)
            t = float(row["total_time"])
            t_min = float(row["time_min"])
            t_avg = float(row["time_avg"])
            t_max = float(row["time_max"])
            fator = float(row["time_max_avg"])
            fbc = float(row["time_fbc"])
            speedup = t_serial_normal / t
            efic = (speedup / max_threads) * 100.0
            ch_label = "padrao" if ch == 0 else str(ch)
            print(f"{sched:<10} {ch_label:<8} {t:>12.6f} {speedup:>10.3f} {efic:>16.2f} {fator:>17.6f} {fbc:>12.6f}")
            writer.writerow([sched, ch_label, max_threads, f"{t:.6f}", f"{t_serial_normal:.6f}", f"{speedup:.3f}", f"{efic:.2f}", f"{t_min:.6f}", f"{t_avg:.6f}", f"{t_max:.6f}", f"{fator:.6f}", f"{fbc:.6f}"])

    # 3. Escalabilidade Forte
    print("\n=== 3. ESCALABILIDADE FORTE (4096x4096, dynamic,1) ===")
    print(f"{'Threads':<8} {'Tempo (s)':>12} {'Speedup':>10} {'Eficiencia (%)':>16} {'Fator (max/avg)':>17} {'FBC':>12}")
    with open(f"{RESULTS_DIR}/resumo_escalabilidade_forte.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["threads", "tempo", "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fator_max_avg", "fbc"])
        for th in thread_list:
            row = run_openmp(4096, "normal", threads=th, schedule="dynamic", chunk=1, repeats=repeats, stat_mode=stat_mode)
            t = float(row["total_time"])
            t_min = float(row["time_min"])
            t_avg = float(row["time_avg"])
            t_max = float(row["time_max"])
            fator = float(row["time_max_avg"])
            fbc = float(row["time_fbc"])
            speedup = t_serial_normal / t
            efic = (speedup / th) * 100.0
            print(f"{th:<8} {t:>12.6f} {speedup:>10.3f} {efic:>16.2f} {fator:>17.6f} {fbc:>12.6f}")
            writer.writerow([th, f"{t:.6f}", f"{t_serial_normal:.6f}", f"{speedup:.3f}", f"{efic:.2f}", f"{t_min:.6f}", f"{t_avg:.6f}", f"{t_max:.6f}", f"{fator:.6f}", f"{fbc:.6f}"])

    # 4. Caso de Desbalanceamento
    print(f"\n=== 4. CASO DE DESBALANCEAMENTO (4096x4096, MAX_ITER=5000, {max_threads} threads) ===")
    t_serial_desbal = run_serial(4096, "desbalanceamento", repeats=repeats, stat_mode=stat_mode)
    print(f"Tempo Serial (Desbalanceamento 4096, {stat_label} de {repeats}x): {t_serial_desbal:.6f} s")
    print(f"{'Schedule':<10} {'Chunk':<8} {'Tempo (s)':>12} {'Speedup':>10} {'Eficiencia (%)':>16} {'Fator (max/avg)':>17} {'FBC':>12}")
    with open(f"{RESULTS_DIR}/resumo_desbalanceamento.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["schedule", "chunk", "threads", "tempo", "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fator_max_avg", "fbc"])
        for sched, ch in configs:
            row = run_openmp(4096, "desbalanceamento", threads=max_threads, schedule=sched, chunk=ch, repeats=repeats, stat_mode=stat_mode)
            t = float(row["total_time"])
            t_min = float(row["time_min"])
            t_avg = float(row["time_avg"])
            t_max = float(row["time_max"])
            fator = float(row["time_max_avg"])
            fbc = float(row["time_fbc"])
            speedup = t_serial_desbal / t
            efic = (speedup / max_threads) * 100.0
            ch_label = "padrao" if ch == 0 else str(ch)
            print(f"{sched:<10} {ch_label:<8} {t:>12.6f} {speedup:>10.3f} {efic:>16.2f} {fator:>17.6f} {fbc:>12.6f}")
            writer.writerow([sched, ch_label, max_threads, f"{t:.6f}", f"{t_serial_desbal:.6f}", f"{speedup:.3f}", f"{efic:.2f}", f"{t_min:.6f}", f"{t_avg:.6f}", f"{t_max:.6f}", f"{fator:.6f}", f"{fbc:.6f}"])

    # 5. Escalabilidade Fraca
    if "--skip-weak" not in sys.argv:
        print("\n=== 5. ESCALABILIDADE FRACA (dynamic,1) ===")
        print(f"{'Resolucao':<10} {'Threads':<8} {'Tempo Serial (s)':>18} {'Tempo Paral. (s)':>18} {'Speedup':>10} {'Eficiencia (%)':>16} {'Fator (max/avg)':>17} {'FBC':>12}")
        with open(f"{RESULTS_DIR}/resumo_escalabilidade_fraca.csv", "w", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["resolucao", "threads", "tempo_paralelo", "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fator_max_avg", "fbc"])
            for th in thread_list:
                res_w = round(4096 * math.sqrt(th))
                t_ser = t_serial_normal if res_w == 4096 else run_serial(res_w, "normal", repeats=repeats, stat_mode=stat_mode)
                row = run_openmp(res_w, "normal", threads=th, schedule="dynamic", chunk=1, repeats=repeats, stat_mode=stat_mode)
                t_par = float(row["total_time"])
                t_min = float(row["time_min"])
                t_avg = float(row["time_avg"])
                t_max = float(row["time_max"])
                fator = float(row["time_max_avg"])
                fbc = float(row["time_fbc"])
                speedup = t_ser / t_par
                efic = (speedup / th) * 100.0
                print(f"{res_w:<10} {th:<8} {t_ser:>18.6f} {t_par:>18.6f} {speedup:>10.3f} {efic:>16.2f} {fator:>17.6f} {fbc:>12.6f}")
                writer.writerow([res_w, th, f"{t_par:.6f}", f"{t_ser:.6f}", f"{speedup:.3f}", f"{efic:.2f}", f"{t_min:.6f}", f"{t_avg:.6f}", f"{t_max:.6f}", f"{fator:.6f}", f"{fbc:.6f}"])


if __name__ == "__main__":
    main()
