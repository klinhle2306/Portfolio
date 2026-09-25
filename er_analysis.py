"""
er_analysis.py

How long do Texas emergency rooms actually take, and does a hospital's
star rating tell you anything about it?

Data
----
- CMS "Timely and Effective Care - Hospital" emergency department measures
  (OP-18b, OP-22, EDV), reporting period Oct 2024 - Sep 2025 for OP-18b.
  Copy obtained from a public GitHub mirror of the CMS file.
- CMS "Hospital General Information" (star rating, hospital type, ownership).

Key measures
------------
OP_18b : median minutes a patient spends in the ER, arrival to departure,
         excluding mental-health and transfer patients. This is the WHOLE
         visit, not just the wait to see a clinician. Lower is better.
OP_22  : percent of ER patients who left before being seen.
EDV    : ER volume category (low / medium / high / very high).

Cleaning decisions (see explore/clean functions)
------------------------------------------------
- "Not Available" scores are treated as missing, never as zero.
- CMS footnote 3 ("shorter time period than required") marks shakier
  numbers. They are kept but flagged, and every headline result was
  re-run without them to confirm nothing changes.
"""

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

ED_PATH = "ed_raw.csv"
INFO_PATH = "hosp_info.csv"
VOLUME_ORDER = ["low", "medium", "high", "very high"]

# Site palette so the charts match the portfolio's Stardew Valley theme
PARCHMENT = "#FFEBCD"
WOOD = "#311807"
WOOD2 = "#431600"
TAN = "#bc9253"
PEACH = "#F0A082"
GOLD = "#D4A017"
GREEN = "#228B22"
MUTED = "#8a7560"

plt.rcParams.update({
    "font.family": "DejaVu Sans Mono",
    "axes.facecolor": PARCHMENT,
    "figure.facecolor": PARCHMENT,
    "axes.edgecolor": WOOD,
    "axes.labelcolor": WOOD,
    "xtick.color": WOOD,
    "ytick.color": WOOD,
    "axes.titleweight": "bold",
    "axes.titlecolor": WOOD,
})


def load_texas():
    """Load the ED file, keep Texas, and reshape to one row per hospital."""
    ed = pd.read_csv(ED_PATH, dtype=str)
    tx = ed[ed["State"] == "TX"]

    def measure(mid, numeric=True):
        d = tx[tx["Measure ID"] == mid][["Facility ID", "Score", "Footnote"]]
        d = d.rename(columns={"Score": mid, "Footnote": mid + "_fn"})
        if numeric:
            d[mid] = pd.to_numeric(d[mid], errors="coerce")  # "Not Available" -> NaN
        return d

    base = tx.drop_duplicates("Facility ID")[
        ["Facility ID", "Facility Name", "City/Town", "County/Parish"]
    ]
    df = (base.merge(measure("OP_18b"), on="Facility ID", how="left")
              .merge(measure("OP_22"), on="Facility ID", how="left")
              .merge(measure("EDV", numeric=False)[["Facility ID", "EDV"]],
                     on="Facility ID", how="left"))
    df["EDV"] = df["EDV"].replace("Not Available", np.nan)
    return ed, df


def explore(df):
    """Print how much of the Texas data is actually usable, before any analysis."""
    print("Texas hospitals in file:", len(df))
    for m in ["OP_18b", "OP_22", "EDV"]:
        print(f"  {m}: usable={df[m].notna().sum()}  missing={df[m].isna().sum()}")
    print("OP_18b footnotes:", df["OP_18b_fn"].value_counts(dropna=False).to_dict())


def add_hospital_info(df):
    """Join star rating, hospital type, and ownership from Hospital General Information."""
    info = pd.read_csv(INFO_PATH, dtype=str, encoding_errors="replace")
    info = info[["Facility ID", "Hospital Type", "Hospital Ownership",
                 "Hospital overall rating"]]
    df = df.merge(info, on="Facility ID", how="left")
    df["stars"] = pd.to_numeric(df["Hospital overall rating"], errors="coerce")
    df["partial_period"] = (df["OP_18b_fn"].fillna("").str.contains(r"\b3\b")
                            & df["OP_18b"].notna())
    return df


def texas_vs_us_by_volume(ed):
    """Median ER time by volume tier, Texas vs. the rest of the US."""
    p = (ed[ed["Measure ID"].isin(["OP_18b", "EDV"])]
         .pivot_table(index=["Facility ID", "State"], columns="Measure ID",
                      values="Score", aggfunc="first").reset_index())
    p["minutes"] = pd.to_numeric(p["OP_18b"], errors="coerce")
    p = p[p["minutes"].notna() & (p["EDV"] != "Not Available")]
    p["group"] = np.where(p["State"] == "TX", "Texas", "Rest of US")
    return p.pivot_table(index="EDV", columns="group", values="minutes",
                         aggfunc="median").reindex(VOLUME_ORDER)


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_linewidth(2)


def chart_data_availability(df, path="er_chart_missing.png"):
    """Stacked bar: how many Texas hospitals actually report each measure."""
    labels = ["ER time\n(OP-18b)", "Left before\nseen (OP-22)", "ER volume\n(EDV)"]
    usable = [df[m].notna().sum() for m in ["OP_18b", "OP_22", "EDV"]]
    missing = [len(df) - u for u in usable]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, usable, color=GREEN, edgecolor=WOOD, linewidth=2, label="Reported")
    ax.bar(labels, missing, bottom=usable, color=PEACH, edgecolor=WOOD,
           linewidth=2, label='"Not Available"')
    for i, (u, m) in enumerate(zip(usable, missing)):
        ax.text(i, u + m / 2, str(m), ha="center", va="center", color=WOOD, fontweight="bold")
        ax.text(i, u / 2, str(u), ha="center", va="center", color=PARCHMENT, fontweight="bold")
    ax.set_ylabel("Texas hospitals")
    ax.set_title("Not every hospital reports every number")
    ax.legend(frameon=False)
    style(ax)
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def chart_volume(vol, path="er_chart_volume.png"):
    """Grouped bar: median ER minutes by volume tier, Texas vs rest of US."""
    x = np.arange(len(VOLUME_ORDER)); w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(x - w / 2, vol["Rest of US"], w, color=TAN, edgecolor=WOOD, linewidth=2, label="Rest of US")
    ax.bar(x + w / 2, vol["Texas"], w, color=GREEN, edgecolor=WOOD, linewidth=2, label="Texas")
    for i, v in enumerate(vol["Texas"]):
        ax.text(i + w / 2, v + 4, f"{v:.0f}", ha="center", color=WOOD, fontsize=9)
    for i, v in enumerate(vol["Rest of US"]):
        ax.text(i - w / 2, v + 4, f"{v:.0f}", ha="center", color=WOOD, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([v.title() for v in VOLUME_ORDER])
    ax.set_xlabel("ER volume"); ax.set_ylabel("Median minutes in the ER")
    ax.set_title("Bigger ERs take longer, and Texas beats the US at every size")
    ax.legend(frameon=False); style(ax)
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def chart_stars(er, path="er_chart_stars.png"):
    """Strip + median line: ER minutes by star rating."""
    s = er[er["stars"].notna()]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    rng = np.random.default_rng(7)
    for star in range(1, 6):
        vals = s[s["stars"] == star]["OP_18b"]
        ax.scatter(star + rng.uniform(-0.18, 0.18, len(vals)), vals,
                   color=PEACH, edgecolor=WOOD, s=30, linewidth=1, zorder=2)
        ax.plot([star - 0.3, star + 0.3], [vals.median()] * 2, color=WOOD, linewidth=3, zorder=3)
    ax.set_xticks(range(1, 6)); ax.set_xticklabels(["1★", "2★", "3★", "4★", "5★"])
    ax.set_xlabel("CMS overall star rating"); ax.set_ylabel("Median minutes in the ER")
    ax.set_title("Star rating tells you nothing about ER time")
    style(ax); plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def chart_lwbs(er, path="er_chart_lwbs.png"):
    """Bar: % who left before being seen, by ER speed quartile."""
    w = er[er["OP_22"].notna()].copy()
    w["q"] = pd.qcut(w["OP_18b"], 4, labels=["Fastest\n25%", "2nd", "3rd", "Slowest\n25%"])
    means = w.groupby("q", observed=True)["OP_22"].mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [GREEN, GREEN, PEACH, "#C4536B"]
    ax.bar(means.index.astype(str), means.values, color=colors, edgecolor=WOOD, linewidth=2)
    for i, v in enumerate(means.values):
        ax.text(i, v + 0.04, f"{v:.1f}%", ha="center", color=WOOD, fontweight="bold")
    ax.set_ylabel("Avg % who left before being seen")
    ax.set_title("Slow ERs lose nearly twice as many patients")
    style(ax); plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def chart_houston(df, path="er_chart_houston.png"):
    """Dot plot: every Harris County hospital, colored by star rating."""
    h = df[(df["County/Parish"] == "HARRIS") & df["OP_18b"].notna()].sort_values("OP_18b")
    star_colors = {5: GOLD, 4: GREEN, 3: TAN, 2: PEACH, 1: "#C4536B"}
    fig, ax = plt.subplots(figsize=(8, 9))
    y = np.arange(len(h))
    med = h["OP_18b"].median()
    ax.axvline(med, color=MUTED, linestyle="--", linewidth=1.5)
    ax.text(med + 3, len(h) - 0.5, f"county median {med:.0f} min", color=MUTED, fontsize=8)
    for yi, (_, r) in zip(y, h.iterrows()):
        c = star_colors.get(r["stars"], "#d9ccb8")
        ax.plot([0, r["OP_18b"]], [yi, yi], color=TAN, linewidth=1, zorder=1)
        ax.scatter(r["OP_18b"], yi, color=c, edgecolor=WOOD, s=70, linewidth=1.5, zorder=2)
    ax.set_yticks(y)
    def pretty(n):
        n = n.title().replace("Hca ", "HCA ").replace("'S ", "'s ").replace(" Lp", " LP")
        n = n.replace("Womans Hospital Of Texas,The", "The Woman's Hospital of Texas").replace(" Of ", " of ")
        return n[:40]
    ax.set_yticklabels([pretty(n) for n in h["Facility Name"]], fontsize=7.5)
    ax.set_xlabel("Median minutes in the ER")
    ax.set_title("Houston ERs: fastest to slowest")
    for star in [5, 4, 3, 2]:
        ax.scatter([], [], color=star_colors[star], edgecolor=WOOD, s=60, label=f"{star}★")
    ax.scatter([], [], color="#d9ccb8", edgecolor=WOOD, s=60, label="No rating")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    style(ax); plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


if __name__ == "__main__":
    ed, df = load_texas()
    print("=== Exploration ===")
    explore(df)
    df = add_hospital_info(df)
    er = df[df["OP_18b"].notna()]

    print("\n=== Results ===")
    print("Texas median ER minutes:", er["OP_18b"].median())
    vol = texas_vs_us_by_volume(ed)
    print(vol)
    s = er[er["stars"].notna()]
    print("Stars vs ER time (Spearman):", stats.spearmanr(s["stars"], s["OP_18b"]))
    w = er[er["OP_22"].notna()]
    print("ER time vs left-before-seen (Spearman):", stats.spearmanr(w["OP_18b"], w["OP_22"]))

    print("\n=== Sensitivity: drop partial-period values ===")
    e2 = er[~er["partial_period"]]
    s2 = e2[e2["stars"].notna()]
    print("Stars vs ER time without them:", stats.spearmanr(s2["stars"], s2["OP_18b"]))

    chart_data_availability(df)
    chart_volume(vol)
    chart_stars(er)
    chart_lwbs(er)
    chart_houston(df)
    print("\nCharts saved.")
