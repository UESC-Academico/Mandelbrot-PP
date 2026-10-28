import csv
import filecmp
import math
import os
import re
import subprocess
import sys


def parse_time(output):
    match = re.search(r"Tempo de execucao:\s*([0-9.]+)", output)
    return float(match.group(1)) if match else 0.0


def run_serial(width=4096, mode="normal", skip_io=True):
    env = os.environ.copy()
    if skip_io:
        env["SKIP_IO"] = "1"

    cmd = ["./mandelbrot_sequencial", str(width)]
    if mode == "desbalanceamento":
        cmd.append("desbalanceamento")

    res = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
    return parse_time(res.stdout)


def run_openmp(width=4096, mode="normal", threads=12, schedule="dynamic", chunk=1, skip_io=True):
    env = os.environ.copy()
    if skip_io:
        env["SKIP_IO"] = "1"

    env["OMP_NUM_THREADS"] = str(threads)
    if chunk is None or chunk == 0:
        env["OMP_SCHEDULE"] = schedule
    else:
        env["OMP_SCHEDULE"] = f"{schedule},{chunk}"

    cmd = ["./mandelbrot_openmp", str(width)]
    if mode == "desbalanceamento":
        cmd.append("desbalanceamento")

    res = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

    match = re.search(r"Estatisticas salvas em:\s*(.+\.csv)", res.stdout)
    csv_path = match.group(1).strip() if match else None
    if csv_path and os.path.exists(csv_path):
        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            return next(reader)
    return {}


def main():
    os.makedirs("Results", exist_ok=True)
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
    t_serial_normal = run_serial(4096, "normal", skip_io=False)
    run_openmp(4096, "normal", threads=max_threads, schedule="dynamic", chunk=1, skip_io=False)
    is_equal = filecmp.cmp("mandelbrot_matriz.bin", "mandelbrot_paralelo_matriz.bin", shallow=False)
    print(f"Corretude (cmp binarios): {'IGUAIS' if is_equal else 'DIFERENTES'}")
    print(f"Tempo Serial (Normal 4096): {t_serial_normal:.6f} s")

    # 2. Casos de Teste Schedule / Chunk
    print(f"\n=== 2. CASOS DE TESTE SCHEDULE/CHUNK (4096x4096, {max_threads} threads) ===")
    print(f"{'Schedule':<10} {'Chunk':<8} {'Tempo (s)':>12} {'Speedup':>10} {'Eficiencia (%)':>16} {'Fator (max/avg)':>17} {'FBC':>12}")
    with open("Results/resumo_schedule_chunk.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["schedule", "chunk", "threads", "tempo", "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fator_max_avg", "fbc"])
        for sched, ch in configs:
            row = run_openmp(4096, "normal", threads=max_threads, schedule=sched, chunk=ch)
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
    with open("Results/resumo_escalabilidade_forte.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["threads", "tempo", "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fator_max_avg", "fbc"])
        for th in thread_list:
            row = run_openmp(4096, "normal", threads=th, schedule="dynamic", chunk=1)
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
    t_serial_desbal = run_serial(4096, "desbalanceamento")
    print(f"Tempo Serial (Desbalanceamento 4096): {t_serial_desbal:.6f} s")
    print(f"{'Schedule':<10} {'Chunk':<8} {'Tempo (s)':>12} {'Speedup':>10} {'Eficiencia (%)':>16} {'Fator (max/avg)':>17} {'FBC':>12}")
    with open("Results/resumo_desbalanceamento.csv", "w", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["schedule", "chunk", "threads", "tempo", "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fator_max_avg", "fbc"])
        for sched, ch in configs:
            row = run_openmp(4096, "desbalanceamento", threads=max_threads, schedule=sched, chunk=ch)
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
        with open("Results/resumo_escalabilidade_fraca.csv", "w", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["resolucao", "threads", "tempo_paralelo", "tempo_serial", "speedup", "eficiencia", "time_min", "time_avg", "time_max", "fator_max_avg", "fbc"])
            for th in thread_list:
                res_w = int(round(4096 * math.sqrt(th)))
                t_ser = t_serial_normal if res_w == 4096 else run_serial(res_w, "normal")
                row = run_openmp(res_w, "normal", threads=th, schedule="dynamic", chunk=1)
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
