import csv
import os

import matplotlib.pyplot as plt

CSV_DIR = "Results/OpenMP/CSV"
TABLES_DIR = "Results/OpenMP/Tables"
GRAPHS_DIR = "Results/OpenMP/Graphs"

# Estilo visual LaTeX (STIX / Computer Modern / pgfplots)
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "CMU Serif", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8,
    "grid.color": "#E0E0E0",
    "grid.linestyle": "-",
    "grid.linewidth": 0.6,
    "figure.dpi": 300,
})

STYLE_SCHED = {
    "static":  {"label": "Static",  "color": "#1f77b4", "marker": "o"},
    "dynamic": {"label": "Dynamic", "color": "#2ca02c", "marker": "s"},
    "guided":  {"label": "Guided",  "color": "#ff7f0e", "marker": "^"},
}


def read_csv_rows(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_thread_times(sched, chunk, threads):
    chunk_num = "1" if chunk == "padrao" and sched != "static" else ("0" if chunk == "padrao" else str(chunk))
    candidates = [
        f"{CSV_DIR}/estatisticas_{sched}_{chunk_num}_threads_{threads}.csv",
        f"{CSV_DIR}/estatisticas_{sched}_0_threads_{threads}.csv",
    ]
    for path in candidates:
        if os.path.exists(path):
            rows = read_csv_rows(path)
            if rows:
                r = rows[0]
                t_avg = r.get("time_avg") or r.get("time_media") or r.get("total_time")
                return float(r["time_min"]), float(t_avg), float(r["time_max"])
    return None


def save_booktabs_table(headers, rows, group_breaks, out_png, out_tex, col_aligns=None):
    # 1. Exportar codigo LaTeX (.tex) no padrao booktabs
    align_str = "".join(col_aligns) if col_aligns else ("ll" + "r" * (len(headers) - 2))
    with open(out_tex, "w", encoding="utf-8") as f:
        f.write("\\begin{tabular}{" + align_str + "}\n")
        f.write("\\toprule\n")
        f.write(" & ".join(f"\\textbf{{{h}}}" for h in headers) + " \\\\\n")
        f.write("\\midrule\n")
        for idx, r in enumerate(rows):
            f.write(" & ".join(str(c) for c in r) + " \\\\\n")
            if idx + 1 in group_breaks:
                f.write("\\midrule\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")

    # 2. Renderizar imagem (.png) no estilo LaTeX booktabs com larguras proporcionais
    n_rows = len(rows)
    n_cols = len(headers)
    if not col_aligns:
        col_aligns = ["l", "l"] + ["r"] * (n_cols - 2)

    col_weights = []
    for c_idx in range(n_cols):
        max_len = len(str(headers[c_idx]))
        for r in rows:
            max_len = max(max_len, len(str(r[c_idx])))
        col_weights.append(max_len + 4)

    total_weight = sum(col_weights)
    col_x = [0.0]
    for w in col_weights:
        col_x.append(col_x[-1] + (w / total_weight))

    fig_w = max(8.2, total_weight * 0.115)
    fig_h = (n_rows + 1.8) * 0.34
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")

    y_top = 1.0
    row_h = 1.0 / (n_rows + 1.5)

    # Linha \toprule
    ax.plot([0, 1], [y_top, y_top], color="black", lw=1.6, clip_on=False)

    # Cabecalho
    y_hdr = y_top - 0.6 * row_h
    for c_idx, h_text in enumerate(headers):
        align = col_aligns[c_idx]
        x_pos = col_x[c_idx] + 0.015 if align == "l" else (col_x[c_idx + 1] - 0.015 if align == "r" else (col_x[c_idx] + col_x[c_idx + 1]) / 2)
        ha = "left" if align == "l" else ("right" if align == "r" else "center")
        ax.text(x_pos, y_hdr, h_text, fontweight="bold", fontsize=10.5, ha=ha, va="center")

    # Linha \midrule abaixo do cabecalho
    y_mid_hdr = y_top - 1.15 * row_h
    ax.plot([0, 1], [y_mid_hdr, y_mid_hdr], color="black", lw=0.9, clip_on=False)

    # Linhas de dados
    for r_idx, r_data in enumerate(rows):
        y_row = y_mid_hdr - (r_idx + 0.55) * row_h
        for c_idx, val in enumerate(r_data):
            align = col_aligns[c_idx]
            x_pos = col_x[c_idx] + 0.015 if align == "l" else (col_x[c_idx + 1] - 0.015 if align == "r" else (col_x[c_idx] + col_x[c_idx + 1]) / 2)
            ha = "left" if align == "l" else ("right" if align == "r" else "center")
            ax.text(x_pos, y_row, str(val), fontsize=10, ha=ha, va="center")

        if (r_idx + 1) in group_breaks:
            y_sep = y_mid_hdr - (r_idx + 1.05) * row_h
            ax.plot([0, 1], [y_sep, y_sep], color="black", lw=0.7, clip_on=False)

    # Linha \bottomrule
    y_bot = y_mid_hdr - (n_rows + 0.1) * row_h
    ax.plot([0, 1], [y_bot, y_bot], color="black", lw=1.6, clip_on=False)

    ax.set_xlim(0, 1)
    ax.set_ylim(y_bot - 0.1 * row_h, y_top + 0.1 * row_h)
    plt.subplots_adjust(left=0.02, right=0.98, top=0.96, bottom=0.04)
    plt.savefig(out_png, bbox_inches="tight", dpi=300)
    plt.close(fig)


def plot_schedule_suite(rows, prefix, subfolder, title_suffix, is_desbal=False):
    if not rows:
        return

    out_graph_dir = f"{GRAPHS_DIR}/{subfolder}"
    os.makedirs(out_graph_dir, exist_ok=True)

    chunks_order = ["padrao", "1", "8", "32", "128"]
    x_labels = ["Padrão", "1", "8", "32", "128"]
    x_pos = {ch: i for i, ch in enumerate(chunks_order)}

    threads = int(rows[0].get("threads", 12))
    tempo_first = float(rows[0]["tempo"])
    speedup_first = float(rows[0]["speedup"])
    t_serial = float(rows[0].get("tempo_serial", tempo_first * speedup_first))

    # 1. Tabela booktabs
    if is_desbal:
        headers = ["Schedule", "Chunk", "Tempo (s)", "Tempo serial ref. (s)", "Speedup", "Eficiência (%)", "Fator de Balanceamento"]
        col_aligns = ["l", "l", "r", "r", "r", "r", "r"]
        table_rows = [
            [
                r["schedule"],
                "padrão" if r["chunk"] == "padrao" else r["chunk"],
                f"{float(r['tempo']):.6f}",
                f"{t_serial:.6f}",
                f"{float(r['speedup']):.3f}",
                f"{float(r['eficiencia']):.2f}",
                f"{float(r['fator_max_avg']):.6f}",
            ]
            for r in rows
        ]
    else:
        headers = ["Schedule", "Chunk", "Tempo (s)", "Speedup", "Eficiência (%)", "Fator de Balanceamento"]
        col_aligns = ["l", "l", "r", "r", "r", "r"]
        table_rows = [
            [
                r["schedule"],
                "padrão" if r["chunk"] == "padrao" else r["chunk"],
                f"{float(r['tempo']):.6f}",
                f"{float(r['speedup']):.3f}",
                f"{float(r['eficiencia']):.2f}",
                f"{float(r['fator_max_avg']):.6f}",
            ]
            for r in rows
        ]

    save_booktabs_table(
        headers,
        table_rows,
        group_breaks={5, 9},
        out_png=f"{TABLES_DIR}/tabela_{prefix}.png",
        out_tex=f"{TABLES_DIR}/tabela_{prefix}.tex",
        col_aligns=col_aligns,
    )

    # Agrupar por schedule
    by_sched = {"static": [], "dynamic": [], "guided": []}
    for r in rows:
        s = r["schedule"]
        if s in by_sched and r["chunk"] in x_pos:
            by_sched[s].append((x_pos[r["chunk"]], r))

    # 2. Grafico de Tempo de Execucao
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["static", "dynamic", "guided"]:
        pts = by_sched[s]
        if pts:
            xs = [p[0] for p in pts]
            ys = [float(p[1]["tempo"]) for p in pts]
            st = STYLE_SCHED[s]
            ax.plot(xs, ys, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)

    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Tamanho do chunk", fontsize=11)
    ax.set_ylabel("Tempo de execução (s)", fontsize=11)
    ax.set_title(f"{title_suffix} ({threads} threads)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_tempo.png", bbox_inches="tight")
    plt.close(fig)

    # 3. Grafico de Speedup
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["static", "dynamic", "guided"]:
        pts = by_sched[s]
        if pts:
            xs = [p[0] for p in pts]
            ys = [float(p[1]["speedup"]) for p in pts]
            st = STYLE_SCHED[s]
            ax.plot(xs, ys, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)

    ax.plot([], [], color="none", label=f"Ideal: {threads}")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Tamanho do chunk", fontsize=11)
    ax.set_ylabel("Speedup", fontsize=11)
    ax.set_title(f"Speedup - {title_suffix} ({threads} threads)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_speedup.png", bbox_inches="tight")
    plt.close(fig)

    # 4. Grafico de Eficiencia
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["static", "dynamic", "guided"]:
        pts = by_sched[s]
        if pts:
            xs = [p[0] for p in pts]
            ys = [float(p[1]["eficiencia"]) for p in pts]
            st = STYLE_SCHED[s]
            ax.plot(xs, ys, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)

    ax.plot([], [], color="none", label="Ideal: 100%")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Tamanho do chunk", fontsize=11)
    ax.set_ylabel("Eficiência paralela (%)", fontsize=11)
    ax.set_title(f"Eficiência - {title_suffix} ({threads} threads)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_eficiencia.png", bbox_inches="tight")
    plt.close(fig)

    # 5. Grafico de Fator de Balanceamento
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["static", "dynamic", "guided"]:
        pts = by_sched[s]
        if pts:
            xs = [p[0] for p in pts]
            ys = [float(p[1]["fator_max_avg"]) for p in pts]
            st = STYLE_SCHED[s]
            ax.plot(xs, ys, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)

    ax.plot([], [], color="none", label="Ideal: 1")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Tamanho do chunk", fontsize=11)
    ax.set_ylabel("Fator de balanceamento", fontsize=11)
    ax.set_title(f"Fator de Balanceamento - {title_suffix} ({threads} threads)", fontweight="bold", fontsize=11.5, pad=10)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_fator.png", bbox_inches="tight")
    plt.close(fig)

    # 6. Grafico de Cargas Minima, Media e Maxima por configuracao
    cfg_labels = []
    t_mins, t_avgs, t_maxs = [], [], []
    short_prefix = {"static": "S", "dynamic": "D", "guided": "G"}

    for r in rows:
        s = r["schedule"]
        ch = r["chunk"]
        lbl = f"{short_prefix.get(s, s)}-{'p' if ch == 'padrao' else ch}"
        if "time_min" in r and "time_avg" in r and "time_max" in r:
            tmin, tavg, tmax = float(r["time_min"]), float(r["time_avg"]), float(r["time_max"])
        else:
            res_times = get_thread_times(s, ch, threads)
            if not res_times:
                continue
            tmin, tavg, tmax = res_times
        cfg_labels.append(lbl)
        t_mins.append(tmin)
        t_avgs.append(tavg)
        t_maxs.append(tmax)

    if cfg_labels:
        fig, ax = plt.subplots(figsize=(6.8, 4.4))
        xs = list(range(len(cfg_labels)))
        ax.plot(xs, t_mins, label="Carga mínima", color="#1f77b4", marker="o", lw=1.3, markersize=5.5)
        ax.plot(xs, t_avgs, label="Carga média", color="#2ca02c", marker="s", lw=1.3, markersize=5.5)
        ax.plot(xs, t_maxs, label="Carga máxima", color="#d62728", marker="^", lw=1.3, markersize=6)
        ax.set_xticks(xs)
        ax.set_xticklabels(cfg_labels, rotation=40, ha="right")
        ax.set_xlabel("Configuração", fontsize=11)
        ax.set_ylabel("Tempo por thread (s)", fontsize=11)
        ax.set_title(f"Tempos mínimo, médio e máximo - {title_suffix}", fontweight="bold", fontsize=11.5, pad=10)
        ax.set_ylim(bottom=0)
        ax.grid(True)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, edgecolor="black", fancybox=False)
        plt.savefig(f"{out_graph_dir}/fig_{prefix}_cargas.png", bbox_inches="tight")
        plt.close(fig)


def plot_strong_scaling(rows):
    if not rows:
        return

    out_graph_dir = f"{GRAPHS_DIR}/Strong_Scaling"
    os.makedirs(out_graph_dir, exist_ok=True)

    headers = ["Threads", "Tempo (s)", "Tempo serial ref. (s)", "Speedup", "Eficiência (%)", "Fator de Balanceamento"]
    table_rows = [
        [
            r["threads"],
            f"{float(r['tempo']):.6f}",
            f"{float(r['tempo_serial']):.6f}",
            f"{float(r['speedup']):.3f}",
            f"{float(r['eficiencia']):.2f}",
            f"{float(r['fator_max_avg']):.6f}",
        ]
        for r in rows
    ]
    save_booktabs_table(
        headers,
        table_rows,
        group_breaks=set(),
        out_png=f"{TABLES_DIR}/tabela_escalabilidade_forte.png",
        out_tex=f"{TABLES_DIR}/tabela_escalabilidade_forte.tex",
        col_aligns=["r", "r", "r", "r", "r", "r"],
    )

    threads = [int(r["threads"]) for r in rows]
    tempos = [float(r["tempo"]) for r in rows]
    speedups = [float(r["speedup"]) for r in rows]
    efics = [float(r["eficiencia"]) for r in rows]
    fatores = [float(r["fator_max_avg"]) for r in rows]

    # 1. Tempo de Execucao
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.plot(threads, tempos, label="Paralelo - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.set_xticks(threads)
    ax.set_xlabel("Número de threads", fontsize=11)
    ax.set_ylabel("Tempo de execução (s)", fontsize=11)
    ax.set_title("Escalabilidade Forte - Tempo de Execução", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=1, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_tempo.png", bbox_inches="tight")
    plt.close(fig)

    # 2. Speedup
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.plot(threads, speedups, label="Paralelo - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: $S(n,p) = p$")
    ax.set_xticks(threads)
    ax.set_xlabel("Número de threads", fontsize=11)
    ax.set_ylabel("Speedup", fontsize=11)
    ax.set_title("Escalabilidade Forte - Speedup", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_speedup.png", bbox_inches="tight")
    plt.close(fig)

    # 3. Eficiencia
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.plot(threads, efics, label="Paralelo - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 100%")
    ax.set_xticks(threads)
    ax.set_xlabel("Número de threads", fontsize=11)
    ax.set_ylabel("Eficiência paralela (%)", fontsize=11)
    ax.set_title("Escalabilidade Forte - Eficiência", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_eficiencia.png", bbox_inches="tight")
    plt.close(fig)

    # 4. Fator de Balanceamento
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.plot(threads, fatores, label="Paralelo - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 1")
    ax.set_xticks(threads)
    ax.set_xlabel("Número de threads", fontsize=11)
    ax.set_ylabel("Fator de balanceamento", fontsize=11)
    ax.set_title("Escalabilidade Forte - Fator de Balanceamento de Carga", fontweight="bold", fontsize=11.5, pad=10)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_fator.png", bbox_inches="tight")
    plt.close(fig)

    # 5. Carga por Thread
    t_mins, t_avgs, t_maxs = [], [], []
    for r in rows:
        th = int(r["threads"])
        if "time_min" in r and "time_avg" in r and "time_max" in r:
            t_mins.append(float(r["time_min"]))
            t_avgs.append(float(r["time_avg"]))
            t_maxs.append(float(r["time_max"]))
        else:
            res_times = get_thread_times("dynamic", "1", th)
            if res_times:
                t_mins.append(res_times[0])
                t_avgs.append(res_times[1])
                t_maxs.append(res_times[2])

    if len(t_mins) == len(threads):
        fig, ax = plt.subplots(figsize=(6.2, 4.2))
        ax.plot(threads, t_mins, label="Carga mínima", color="#1f77b4", marker="o", lw=1.3, markersize=5.5)
        ax.plot(threads, t_avgs, label="Carga média", color="#2ca02c", marker="s", lw=1.3, markersize=5.5)
        ax.plot(threads, t_maxs, label="Carga máxima", color="#d62728", marker="^", lw=1.3, markersize=6)
        ax.set_xticks(threads)
        ax.set_xlabel("Número de threads", fontsize=11)
        ax.set_ylabel("Tempo por thread (s)", fontsize=11)
        ax.set_title("Escalabilidade Forte - Carga por Thread", fontweight="bold", fontsize=11.5, pad=10)
        ax.set_ylim(bottom=0)
        ax.grid(True)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, edgecolor="black", fancybox=False)
        plt.savefig(f"{out_graph_dir}/fig_forte_cargas.png", bbox_inches="tight")
        plt.close(fig)


def plot_weak_scaling(rows):
    if not rows:
        return

    out_graph_dir = f"{GRAPHS_DIR}/Weak_Scaling"
    os.makedirs(out_graph_dir, exist_ok=True)

    headers = ["Resolução", "Threads", "Tempo (s)", "Tempo serial ref. (s)", "Speedup", "Eficiência (%)", "Fator de Balanceamento"]
    table_rows = [
        [
            r["resolucao"],
            r["threads"],
            f"{float(r['tempo_paralelo']):.6f}",
            f"{float(r['tempo_serial']):.6f}",
            f"{float(r['speedup']):.3f}",
            f"{float(r['eficiencia']):.2f}",
            f"{float(r['fator_max_avg']):.6f}",
        ]
        for r in rows
    ]
    save_booktabs_table(
        headers,
        table_rows,
        group_breaks=set(),
        out_png=f"{TABLES_DIR}/tabela_escalabilidade_fraca.png",
        out_tex=f"{TABLES_DIR}/tabela_escalabilidade_fraca.tex",
        col_aligns=["r", "r", "r", "r", "r", "r", "r"],
    )

    labels = [f"{r['resolucao']} / {r['threads']}" for r in rows]
    xs = list(range(len(labels)))
    t_sers = [float(r["tempo_serial"]) for r in rows]
    t_pars = [float(r["tempo_paralelo"]) for r in rows]
    speedups = [float(r["speedup"]) for r in rows]
    efics = [float(r["eficiencia"]) for r in rows]
    fatores = [float(r["fator_max_avg"]) for r in rows]

    # 1. Tempos Seriais de Referencia
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, t_sers, label="Serial de referência", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de threads", fontsize=11)
    ax.set_ylabel("Tempo serial de referência (s)", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Tempos Seriais de Referência", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=1, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_serial.png", bbox_inches="tight")
    plt.close(fig)

    # 2. Tempo de Execucao Paralelo
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, t_pars, label="Paralelo - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de threads", fontsize=11)
    ax.set_ylabel("Tempo de execução (s)", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Tempo de Execução", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=1, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_tempo.png", bbox_inches="tight")
    plt.close(fig)

    # 3. Speedup
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, speedups, label="Paralelo - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: $S(n,p) = p$")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de threads", fontsize=11)
    ax.set_ylabel("Speedup", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Speedup", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_speedup.png", bbox_inches="tight")
    plt.close(fig)

    # 4. Eficiencia
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, efics, label="Paralelo - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 100%")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de threads", fontsize=11)
    ax.set_ylabel("Eficiência paralela (%)", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Eficiência", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_eficiencia.png", bbox_inches="tight")
    plt.close(fig)

    # 5. Fator de Balanceamento
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, fatores, label="Paralelo - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 1")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de threads", fontsize=11)
    ax.set_ylabel("Fator de balanceamento", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Fator de Balanceamento de Carga", fontweight="bold", fontsize=11.5, pad=10)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_fator.png", bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    os.makedirs(TABLES_DIR, exist_ok=True)
    os.makedirs(GRAPHS_DIR, exist_ok=True)

    rows_sched = read_csv_rows(f"{CSV_DIR}/resumo_schedule_chunk.csv")
    if rows_sched:
        plot_schedule_suite(rows_sched, "schedule_chunk", "Schedule_Chunk", "Schedule/Chunk", is_desbal=False)

    rows_strong = read_csv_rows(f"{CSV_DIR}/resumo_escalabilidade_forte.csv")
    if rows_strong:
        plot_strong_scaling(rows_strong)

    rows_desbal = read_csv_rows(f"{CSV_DIR}/resumo_desbalanceamento.csv")
    if rows_desbal:
        plot_schedule_suite(rows_desbal, "desbalanceamento", "Desbalanceamento", "Caso de Desbalanceamento", is_desbal=True)

    rows_weak = read_csv_rows(f"{CSV_DIR}/resumo_escalabilidade_fraca.csv")
    if rows_weak:
        plot_weak_scaling(rows_weak)

    print("Graficos e tabelas organizados em Results/OpenMP/{CSV,Tables,Graphs}/")


if __name__ == "__main__":
    main()
