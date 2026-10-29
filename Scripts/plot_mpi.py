import csv
import os

import matplotlib.pyplot as plt

CSV_DIR = "Results/MPI/CSV"
TABLES_DIR = "Results/MPI/Tables"
GRAPHS_DIR = "Results/MPI/Graphs"

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

STYLE_STRAT = {
    "block":   {"label": "Block",   "color": "#1f77b4", "marker": "o"},
    "cyclic":  {"label": "Cyclic",  "color": "#ff7f0e", "marker": "^"},
    "dynamic": {"label": "Dynamic", "color": "#2ca02c", "marker": "s"},
}


def read_csv_rows(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Se comm_time em linhas dynamic antigas for igual a master_time, ajusta para (tempo - time_avg)
    for r in rows:
        strat = r.get("strategy", "dynamic")
        procs = int(r.get("processes", 12))
        if strat == "dynamic" and procs > 1 and "comm_time" in r and "master_time" in r:
            c_t = float(r["comm_time"])
            m_t = float(r["master_time"])
            t_tot = float(r.get("tempo") or r.get("tempo_paralelo") or 0.0)
            t_avg = float(r.get("time_avg", 0.0))
            if abs(c_t - m_t) < 1e-5 and t_tot > t_avg:
                r["comm_time"] = f"{max(0.0, t_tot - t_avg):.6f}"
    return rows


def save_booktabs_table(headers, rows, group_breaks, out_png, out_tex, col_aligns=None):
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

    fig_w = max(8.5, total_weight * 0.115)
    fig_h = (n_rows + 1.8) * 0.34
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")

    y_top = 1.0
    row_h = 1.0 / (n_rows + 1.5)

    ax.plot([0, 1], [y_top, y_top], color="black", lw=1.6, clip_on=False)

    y_hdr = y_top - 0.6 * row_h
    for c_idx, h_text in enumerate(headers):
        align = col_aligns[c_idx]
        x_pos = col_x[c_idx] + 0.015 if align == "l" else (col_x[c_idx + 1] - 0.015 if align == "r" else (col_x[c_idx] + col_x[c_idx + 1]) / 2)
        ha = "left" if align == "l" else ("right" if align == "r" else "center")
        ax.text(x_pos, y_hdr, h_text, fontweight="bold", fontsize=10.5, ha=ha, va="center")

    y_mid_hdr = y_top - 1.15 * row_h
    ax.plot([0, 1], [y_mid_hdr, y_mid_hdr], color="black", lw=0.9, clip_on=False)

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

    y_bot = y_mid_hdr - (n_rows + 0.1) * row_h
    ax.plot([0, 1], [y_bot, y_bot], color="black", lw=1.6, clip_on=False)

    ax.set_xlim(0, 1)
    ax.set_ylim(y_bot - 0.1 * row_h, y_top + 0.1 * row_h)
    plt.subplots_adjust(left=0.02, right=0.98, top=0.96, bottom=0.04)
    plt.savefig(out_png, bbox_inches="tight", dpi=300)
    plt.close(fig)


def plot_strategy_chunk_suite(rows, prefix, subfolder, title_suffix, is_desbal=False):
    if not rows:
        return

    out_graph_dir = f"{GRAPHS_DIR}/{subfolder}"
    os.makedirs(out_graph_dir, exist_ok=True)

    chunks_order = ["padrao", "1", "8", "32", "128"]
    x_labels = ["Padrão", "1", "8", "32", "128"]
    x_pos = {ch: i for i, ch in enumerate(chunks_order)}

    procs = int(rows[0].get("processes", 12))

    # 1. Tabela booktabs
    headers = ["Estratégia", "Chunk", "Tempo (s)", "Comm. (s)", "Mestre (s)", "Speedup", "Eficiência (%)", "FBC"]
    col_aligns = ["l", "l", "r", "r", "r", "r", "r", "r"]
    table_rows = [
        [
            r["strategy"],
            "padrão" if r["chunk"] == "padrao" else r["chunk"],
            f"{float(r['tempo']):.6f}",
            f"{float(r['comm_time']):.6f}",
            f"{float(r['master_time']):.6f}",
            f"{float(r['speedup']):.3f}",
            f"{float(r['eficiencia']):.2f}",
            f"{float(r['fbc']):.6f}",
        ]
        for r in rows
    ]

    save_booktabs_table(
        headers,
        table_rows,
        group_breaks={1, 5},
        out_png=f"{TABLES_DIR}/tabela_{prefix}.png",
        out_tex=f"{TABLES_DIR}/tabela_{prefix}.tex",
        col_aligns=col_aligns,
    )

    by_strat = {"block": [], "cyclic": [], "dynamic": []}
    for r in rows:
        s = r["strategy"]
        if s in by_strat and r["chunk"] in x_pos:
            by_strat[s].append((x_pos[r["chunk"]], r))

    # 2. Tempo de Execucao
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            xs = [p[0] for p in pts]
            ys = [float(p[1]["tempo"]) for p in pts]
            st = STYLE_STRAT[s]
            ax.plot(xs, ys, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)

    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Tamanho do chunk", fontsize=11)
    ax.set_ylabel("Tempo de execução (s)", fontsize=11)
    ax.set_title(f"{title_suffix} ({procs} processos)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_tempo.png", bbox_inches="tight")
    plt.close(fig)

    # 3. Speedup
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            xs = [p[0] for p in pts]
            ys = [float(p[1]["speedup"]) for p in pts]
            st = STYLE_STRAT[s]
            ax.plot(xs, ys, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)

    ax.plot([], [], color="none", label=f"Ideal: {procs}")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Tamanho do chunk", fontsize=11)
    ax.set_ylabel("Speedup", fontsize=11)
    ax.set_title(f"Speedup - {title_suffix} ({procs} processos)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_speedup.png", bbox_inches="tight")
    plt.close(fig)

    # 4. Eficiencia
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            xs = [p[0] for p in pts]
            ys = [float(p[1]["eficiencia"]) for p in pts]
            st = STYLE_STRAT[s]
            ax.plot(xs, ys, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)

    ax.plot([], [], color="none", label="Ideal: 100%")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Tamanho do chunk", fontsize=11)
    ax.set_ylabel("Eficiência paralela (%)", fontsize=11)
    ax.set_title(f"Eficiência - {title_suffix} ({procs} processos)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_eficiencia.png", bbox_inches="tight")
    plt.close(fig)

    # 5. FBC = (T_max - T_min) / T_max
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            xs = [p[0] for p in pts]
            ys = [float(p[1]["fbc"]) for p in pts]
            st = STYLE_STRAT[s]
            ax.plot(xs, ys, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)

    ax.plot([], [], color="none", label="Ideal: 0")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Tamanho do chunk", fontsize=11)
    ax.set_ylabel("FBC $(T_{max} - T_{min}) / T_{max}$", fontsize=11)
    ax.set_title(f"Fator de Balanceamento (FBC) - {title_suffix}", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_fbc.png", bbox_inches="tight")
    plt.close(fig)

    # 6. Cargas Minima, Media e Maxima por configuracao
    short_map = {"block": "B", "cyclic": "C", "dynamic": "D"}
    cfg_labels = [f"{short_map.get(r['strategy'], r['strategy'])}-{'p' if r['chunk'] == 'padrao' else r['chunk']}" for r in rows]
    t_mins = [float(r["time_min"]) for r in rows]
    t_avgs = [float(r["time_avg"]) for r in rows]
    t_maxs = [float(r["time_max"]) for r in rows]
    t_comms = [float(r["comm_time"]) for r in rows]

    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    xs = list(range(len(cfg_labels)))
    ax.plot(xs, t_mins, label="Carga mínima", color="#1f77b4", marker="o", lw=1.3, markersize=5.5)
    ax.plot(xs, t_avgs, label="Carga média", color="#2ca02c", marker="s", lw=1.3, markersize=5.5)
    ax.plot(xs, t_maxs, label="Carga máxima", color="#d62728", marker="^", lw=1.3, markersize=6)
    ax.set_xticks(xs)
    ax.set_xticklabels(cfg_labels, rotation=40, ha="right")
    ax.set_xlabel("Configuração", fontsize=11)
    ax.set_ylabel("Tempo de computação por processo (s)", fontsize=11)
    ax.set_title(f"Tempos mínimo, médio e máximo - {title_suffix}", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_cargas.png", bbox_inches="tight")
    plt.close(fig)

    # 7. Custo de Comunicacao por configuracao
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.bar(xs, t_comms, color="#4c72b0", edgecolor="black", width=0.55, label="Tempo de comunicação")
    ax.set_xticks(xs)
    ax.set_xticklabels(cfg_labels, rotation=40, ha="right")
    ax.set_xlabel("Configuração", fontsize=11)
    ax.set_ylabel("Tempo de comunicação (s)", fontsize=11)
    ax.set_title(f"Custo de Comunicação - {title_suffix} ({procs} processos)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True, axis="y")
    plt.savefig(f"{out_graph_dir}/fig_{prefix}_comunicacao.png", bbox_inches="tight")
    plt.close(fig)


def plot_strong_scaling(rows):
    if not rows:
        return

    out_graph_dir = f"{GRAPHS_DIR}/Strong_Scaling"
    os.makedirs(out_graph_dir, exist_ok=True)

    headers = ["Estratégia", "Processos", "Tempo (s)", "Comm. (s)", "Mestre (s)", "Speedup", "Eficiência (%)", "FBC"]
    table_rows = [
        [
            r["strategy"],
            r["processes"],
            f"{float(r['tempo']):.6f}",
            f"{float(r['comm_time']):.6f}",
            f"{float(r['master_time']):.6f}",
            f"{float(r['speedup']):.3f}",
            f"{float(r['eficiencia']):.2f}",
            f"{float(r['fbc']):.6f}",
        ]
        for r in rows
    ]

    # Quebras de grupo onde muda a estrategia
    breaks = set()
    for i in range(len(rows) - 1):
        if rows[i]["strategy"] != rows[i + 1]["strategy"]:
            breaks.add(i + 1)

    save_booktabs_table(
        headers,
        table_rows,
        group_breaks=breaks,
        out_png=f"{TABLES_DIR}/tabela_escalabilidade_forte.png",
        out_tex=f"{TABLES_DIR}/tabela_escalabilidade_forte.tex",
        col_aligns=["l", "r", "r", "r", "r", "r", "r", "r"],
    )

    by_strat = {"block": [], "cyclic": [], "dynamic": []}
    for r in rows:
        s = r["strategy"]
        if s in by_strat:
            by_strat[s].append(r)

    all_procs = sorted({int(r["processes"]) for r in rows})

    # 1. Tempo de Execucao por Estrategia
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            ps = [int(r["processes"]) for r in pts]
            ts = [float(r["tempo"]) for r in pts]
            st = STYLE_STRAT[s]
            ax.plot(ps, ts, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)
    ax.set_xticks(all_procs)
    ax.set_xlabel("Número de processos MPI", fontsize=11)
    ax.set_ylabel("Tempo de execução (s)", fontsize=11)
    ax.set_title("Escalabilidade Forte - Tempo de Execução", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_tempo.png", bbox_inches="tight")
    plt.close(fig)

    # 2. Speedup
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            ps = [int(r["processes"]) for r in pts]
            sp = [float(r["speedup"]) for r in pts]
            st = STYLE_STRAT[s]
            ax.plot(ps, sp, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: $S(n,p) = p$")
    ax.set_xticks(all_procs)
    ax.set_xlabel("Número de processos MPI", fontsize=11)
    ax.set_ylabel("Speedup", fontsize=11)
    ax.set_title("Escalabilidade Forte - Speedup", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_speedup.png", bbox_inches="tight")
    plt.close(fig)

    # 3. Eficiencia
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            ps = [int(r["processes"]) for r in pts]
            ef = [float(r["eficiencia"]) for r in pts]
            st = STYLE_STRAT[s]
            ax.plot(ps, ef, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 100%")
    ax.set_xticks(all_procs)
    ax.set_xlabel("Número de processos MPI", fontsize=11)
    ax.set_ylabel("Eficiência paralela (%)", fontsize=11)
    ax.set_title("Escalabilidade Forte - Eficiência", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_eficiencia.png", bbox_inches="tight")
    plt.close(fig)

    # 4. FBC
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            ps = [int(r["processes"]) for r in pts]
            fb = [float(r["fbc"]) for r in pts]
            st = STYLE_STRAT[s]
            ax.plot(ps, fb, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 0")
    ax.set_xticks(all_procs)
    ax.set_xlabel("Número de processos MPI", fontsize=11)
    ax.set_ylabel("FBC $(T_{max} - T_{min}) / T_{max}$", fontsize=11)
    ax.set_title("Escalabilidade Forte - Fator de Balanceamento (FBC)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_fbc.png", bbox_inches="tight")
    plt.close(fig)

    # 5. Tempo de Comunicacao vs Processos
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for s in ["block", "cyclic", "dynamic"]:
        pts = by_strat[s]
        if pts:
            ps = [int(r["processes"]) for r in pts]
            cm = [float(r["comm_time"]) for r in pts]
            st = STYLE_STRAT[s]
            ax.plot(ps, cm, label=st["label"], color=st["color"], marker=st["marker"], lw=1.3, markersize=6)
    ax.set_xticks(all_procs)
    ax.set_xlabel("Número de processos MPI", fontsize=11)
    ax.set_ylabel("Tempo de comunicação (s)", fontsize=11)
    ax.set_title("Escalabilidade Forte - Custo de Comunicação", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_forte_comunicacao.png", bbox_inches="tight")
    plt.close(fig)


def plot_weak_scaling(rows):
    if not rows:
        return

    out_graph_dir = f"{GRAPHS_DIR}/Weak_Scaling"
    os.makedirs(out_graph_dir, exist_ok=True)

    headers = ["Resolução", "Processos", "Tempo (s)", "Comm. (s)", "Serial ref. (s)", "Speedup", "Eficiência (%)", "FBC"]
    table_rows = [
        [
            r["resolucao"],
            r["processes"],
            f"{float(r['tempo_paralelo']):.6f}",
            f"{float(r['comm_time']):.6f}",
            f"{float(r['tempo_serial']):.6f}",
            f"{float(r['speedup']):.3f}",
            f"{float(r['eficiencia']):.2f}",
            f"{float(r['fbc']):.6f}",
        ]
        for r in rows
    ]
    save_booktabs_table(
        headers,
        table_rows,
        group_breaks=set(),
        out_png=f"{TABLES_DIR}/tabela_escalabilidade_fraca.png",
        out_tex=f"{TABLES_DIR}/tabela_escalabilidade_fraca.tex",
        col_aligns=["r", "r", "r", "r", "r", "r", "r", "r"],
    )

    labels = [f"{r['resolucao']} / {r['processes']}" for r in rows]
    xs = list(range(len(labels)))
    t_pars = [float(r["tempo_paralelo"]) for r in rows]
    speedups = [float(r["speedup"]) for r in rows]
    efics = [float(r["eficiencia"]) for r in rows]
    fbcs = [float(r["fbc"]) for r in rows]

    # 1. Tempo de Execucao Paralelo
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, t_pars, label="MPI - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de processos", fontsize=11)
    ax.set_ylabel("Tempo de execução (s)", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Tempo de Execução", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=1, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_tempo.png", bbox_inches="tight")
    plt.close(fig)

    # 2. Speedup
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, speedups, label="MPI - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: $S(n,p) = p$")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de processos", fontsize=11)
    ax.set_ylabel("Speedup", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Speedup", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_speedup.png", bbox_inches="tight")
    plt.close(fig)

    # 3. Eficiencia
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, efics, label="MPI - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 100%")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de processos", fontsize=11)
    ax.set_ylabel("Eficiência paralela (%)", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Eficiência", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_eficiencia.png", bbox_inches="tight")
    plt.close(fig)

    # 4. FBC
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(xs, fbcs, label="MPI - dynamic,1", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 0")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=40, ha="right")
    ax.set_xlabel("Resolução / Número de processos", fontsize=11)
    ax.set_ylabel("FBC $(T_{max} - T_{min}) / T_{max}$", fontsize=11)
    ax.set_title("Escalabilidade Fraca - Fator de Balanceamento (FBC)", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2, edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_fraca_fbc.png", bbox_inches="tight")
    plt.close(fig)


def plot_comparison_openmp_mpi(rows_cmp, rows_strong):
    if not rows_cmp:
        return

    out_graph_dir = f"{GRAPHS_DIR}/Comparacao_OpenMP_MPI"
    os.makedirs(out_graph_dir, exist_ok=True)

    # Mapear tambem cyclic,1 do MPI para comparacao completa
    cyclic_map = {}
    for r in rows_strong:
        if r["strategy"] == "cyclic":
            cyclic_map[int(r["processes"])] = r

    headers = ["Unidades", "Tempo OpenMP (s)", "Tempo MPI Circ. (s)", "Tempo MPI Din. (s)", "Speedup OpenMP", "Speedup MPI Din.", "Efic. OpenMP (%)", "Efic. MPI Din. (%)"]
    table_rows = []
    for r in rows_cmp:
        u = int(r["unidades"])
        t_cyc = f"{float(cyclic_map[u]['tempo']):.6f}" if u in cyclic_map else "-"
        table_rows.append([
            u,
            f"{float(r['tempo_openmp']):.6f}",
            t_cyc,
            f"{float(r['tempo_mpi']):.6f}",
            f"{float(r['speedup_openmp']):.3f}",
            f"{float(r['speedup_mpi']):.3f}",
            f"{float(r['eficiencia_openmp']):.2f}",
            f"{float(r['eficiencia_mpi']):.2f}",
        ])

    save_booktabs_table(
        headers,
        table_rows,
        group_breaks=set(),
        out_png=f"{TABLES_DIR}/tabela_comparacao_openmp_mpi.png",
        out_tex=f"{TABLES_DIR}/tabela_comparacao_openmp_mpi.tex",
        col_aligns=["r"] * len(headers),
    )

    units = [int(r["unidades"]) for r in rows_cmp]
    t_omp = [float(r["tempo_openmp"]) for r in rows_cmp]
    t_mpi_dyn = [float(r["tempo_mpi"]) for r in rows_cmp]
    s_omp = [float(r["speedup_openmp"]) for r in rows_cmp]
    s_mpi_dyn = [float(r["speedup_mpi"]) for r in rows_cmp]
    e_omp = [float(r["eficiencia_openmp"]) for r in rows_cmp]
    e_mpi_dyn = [float(r["eficiencia_mpi"]) for r in rows_cmp]

    has_cyc = all(u in cyclic_map for u in units)
    t_mpi_cyc = [float(cyclic_map[u]["tempo"]) for u in units] if has_cyc else []
    s_mpi_cyc = [float(cyclic_map[u]["speedup"]) for u in units] if has_cyc else []
    e_mpi_cyc = [float(cyclic_map[u]["eficiencia"]) for u in units] if has_cyc else []

    # 1. Comparacao de Tempo
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(units, t_omp, label="OpenMP (dynamic,1)", color="#1f77b4", marker="o", lw=1.3, markersize=6)
    if has_cyc:
        ax.plot(units, t_mpi_cyc, label="MPI (cyclic,1)", color="#ff7f0e", marker="^", lw=1.3, markersize=6)
    ax.plot(units, t_mpi_dyn, label="MPI (dynamic,1)", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.set_xticks(units)
    ax.set_xlabel("Número de threads / processos", fontsize=11)
    ax.set_ylabel("Tempo de execução (s)", fontsize=11)
    ax.set_title("Comparação OpenMP vs. MPI - Tempo de Execução", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_comp_tempo.png", bbox_inches="tight")
    plt.close(fig)

    # 2. Comparacao de Speedup
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(units, s_omp, label="OpenMP (dynamic,1)", color="#1f77b4", marker="o", lw=1.3, markersize=6)
    if has_cyc:
        ax.plot(units, s_mpi_cyc, label="MPI (cyclic,1)", color="#ff7f0e", marker="^", lw=1.3, markersize=6)
    ax.plot(units, s_mpi_dyn, label="MPI (dynamic,1)", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: $S(n,p) = p$")
    ax.set_xticks(units)
    ax.set_xlabel("Número de threads / processos", fontsize=11)
    ax.set_ylabel("Speedup", fontsize=11)
    ax.set_title("Comparação OpenMP vs. MPI - Speedup", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_comp_speedup.png", bbox_inches="tight")
    plt.close(fig)

    # 3. Comparacao de Eficiencia
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(units, e_omp, label="OpenMP (dynamic,1)", color="#1f77b4", marker="o", lw=1.3, markersize=6)
    if has_cyc:
        ax.plot(units, e_mpi_cyc, label="MPI (cyclic,1)", color="#ff7f0e", marker="^", lw=1.3, markersize=6)
    ax.plot(units, e_mpi_dyn, label="MPI (dynamic,1)", color="#2ca02c", marker="s", lw=1.3, markersize=6)
    ax.plot([], [], color="none", label="Ideal: 100%")
    ax.set_xticks(units)
    ax.set_xlabel("Número de threads / processos", fontsize=11)
    ax.set_ylabel("Eficiência paralela (%)", fontsize=11)
    ax.set_title("Comparação OpenMP vs. MPI - Eficiência", fontweight="bold", fontsize=11.5, pad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", edgecolor="black", fancybox=False)
    plt.savefig(f"{out_graph_dir}/fig_comp_eficiencia.png", bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    os.makedirs(TABLES_DIR, exist_ok=True)
    os.makedirs(GRAPHS_DIR, exist_ok=True)

    rows_strat = read_csv_rows(f"{CSV_DIR}/resumo_estrategia_chunk.csv")
    if rows_strat:
        plot_strategy_chunk_suite(rows_strat, "estrategia_chunk", "Estrategia_Chunk", "Estratégia/Chunk", is_desbal=False)

    rows_strong = read_csv_rows(f"{CSV_DIR}/resumo_escalabilidade_forte.csv")
    if rows_strong:
        plot_strong_scaling(rows_strong)

    rows_desbal = read_csv_rows(f"{CSV_DIR}/resumo_desbalanceamento.csv")
    if rows_desbal:
        plot_strategy_chunk_suite(
            rows_desbal, "desbalanceamento", "Desbalanceamento", "Caso de Desbalanceamento", is_desbal=True
        )

    rows_weak = read_csv_rows(f"{CSV_DIR}/resumo_escalabilidade_fraca.csv")
    if rows_weak:
        plot_weak_scaling(rows_weak)

    rows_cmp = read_csv_rows(f"{CSV_DIR}/resumo_comparacao_openmp_mpi.csv")
    if rows_cmp:
        plot_comparison_openmp_mpi(rows_cmp, rows_strong)

    print("Graficos e tabelas do MPI gerados em Results/MPI/{Tables,Graphs}/")


if __name__ == "__main__":
    main()
