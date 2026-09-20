"""
fragrance_analysis.py

Question: Does "fragrance-free" — one of the most common clean-beauty
claims — actually predict a better-rated product? Or does it just cost
less/more without moving customer satisfaction?

Data: 1,472 Sephora skincare products (Label, Brand, Name, Price, Rank
[1-5 star rating], Ingredients, and skin-type flags). Source: public
GitHub mirror of a Sephora product dataset originally used for beauty/
consumer-insights analysis practice.

Method: A product is flagged "fragrance-free" if its ingredient list
does not mention "fragrance" or "parfum" (the standard label terms for
added scent, natural or synthetic). This is a simple text-presence
check, not a claim about actual product formulation nuance -- some
products may contain fragrance from a named essential oil without using
the word "fragrance," so this slightly undercounts true fragrance-free
products. It's a reasonable first-pass signal, not a certified label.
"""

import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

DATA_PATH = "cosmetics.csv"


def load_data(path: str = DATA_PATH) -> pd.DataFrame:
    """Load the raw cosmetics dataset and add a fragrance_free flag column."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["fragrance_free"] = ~df["Ingredients"].str.contains(
        "fragrance|parfum", case=False, na=False
    )
    return df


def explore_data(df: pd.DataFrame) -> None:
    """
    Print a basic data-quality pass: shape, missing values, duplicate
    rows, and the distribution of the two numeric columns we care about
    (Rank and Price). This is meant to run BEFORE any analysis, so any
    issue it surfaces gets handled in clean_data() rather than silently
    skewing the results.
    """
    print("Shape:", df.shape)
    print("\nMissing values per column:")
    print(df.isnull().sum())
    print("\nFull duplicate rows:", df.duplicated().sum())
    print("\nRank (rating) summary:")
    print(df["Rank"].describe())
    print("Products with Rank == 0:", (df["Rank"] == 0).sum())
    print("\nPrice summary:")
    print(df["Price"].describe())


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the cleaning decision found during exploration: drop products
    with a Rank of exactly 0.

    Why: ratings in this dataset run 1-5 stars. A small number of
    products (19 of 1,472) show a Rank of 0, which lines up with
    "not yet rated" rather than a genuine below-1-star score -- no
    product actually has a worse rating than a 1-star product would.
    Left in, these zeros would silently drag down average ratings for
    whichever group they happened to fall into. There were no missing
    values or full duplicate rows to handle otherwise.
    """
    before = len(df)
    cleaned = df[df["Rank"] > 0].copy()
    dropped = before - len(cleaned)
    print(f"Dropped {dropped} rows with Rank == 0 ({before} -> {len(cleaned)})")
    return cleaned


def overall_comparison(df: pd.DataFrame) -> dict:
    """
    Compare average rating and price between fragrance-free and
    fragranced products overall, with a t-test for each comparison.

    Returns a dict summarizing sample sizes, means, and p-values.
    """
    ff = df[df["fragrance_free"]]
    fr = df[~df["fragrance_free"]]

    rating_t, rating_p = stats.ttest_ind(
        ff["Rank"].dropna(), fr["Rank"].dropna(), equal_var=False
    )
    price_t, price_p = stats.ttest_ind(
        ff["Price"].dropna(), fr["Price"].dropna(), equal_var=False
    )

    return {
        "fragrance_free_n": len(ff),
        "fragrance_free_avg_rating": ff["Rank"].mean(),
        "fragrance_free_avg_price": ff["Price"].mean(),
        "fragranced_n": len(fr),
        "fragranced_avg_rating": fr["Rank"].mean(),
        "fragranced_avg_price": fr["Price"].mean(),
        "rating_ttest_p": rating_p,
        "price_ttest_p": price_p,
    }


def category_breakdown(df: pd.DataFrame, min_group_size: int = 5) -> pd.DataFrame:
    """
    Break the same comparison down by product category (the `Label`
    column: Moisturizer, Cleanser, Treatment, Face Mask, Eye cream,
    Sun protect). Categories with fewer than `min_group_size` products
    in either group are skipped since the average would be unreliable.
    """
    rows = []
    for label, sub in df.groupby("Label"):
        ff_sub = sub[sub["fragrance_free"]]
        fr_sub = sub[~sub["fragrance_free"]]
        if len(ff_sub) < min_group_size or len(fr_sub) < min_group_size:
            continue
        rows.append({
            "Category": label,
            "FF_n": len(ff_sub),
            "FF_avg_rating": ff_sub["Rank"].mean(),
            "FF_avg_price": ff_sub["Price"].mean(),
            "Fragranced_n": len(fr_sub),
            "Fragranced_avg_rating": fr_sub["Rank"].mean(),
            "Fragranced_avg_price": fr_sub["Price"].mean(),
        })
    return pd.DataFrame(rows)


def plot_rank_distribution(df: pd.DataFrame, out_path: str = "chart_rank_distribution.png") -> None:
    """
    Histogram of the raw Rank column, run BEFORE cleaning, to visually
    show why the 19 zero-rank products look like a data artifact rather
    than genuine ratings: every other product falls between 3 and 5
    stars, with a clear gap before the 0s.
    """
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(df["Rank"], bins=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5],
            color="#8FB9A8", edgecolor="white")
    ax.axvspan(-0.1, 0.5, color="#C4536B", alpha=0.25)
    ax.text(0.15, ax.get_ylim()[1] * 0.9, "19 products\nat exactly 0", color="#C4536B",
            fontsize=10, ha="left", fontweight="bold")
    ax.set_xlabel("Rating (Rank)")
    ax.set_ylabel("Number of products")
    ax.set_title("Rating Distribution — Before Cleaning")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_overall_comparison(summary: dict, out_path: str = "chart_overall.png") -> None:
    """Bar chart comparing average rating and price, fragrance-free vs. fragranced."""
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    groups = ["Fragrance-free", "Fragranced"]
    ratings = [summary["fragrance_free_avg_rating"], summary["fragranced_avg_rating"]]
    prices = [summary["fragrance_free_avg_price"], summary["fragranced_avg_price"]]

    axes[0].bar(groups, ratings, color=["#8FB9A8", "#C4536B"])
    axes[0].set_title("Average Rating")
    axes[0].set_ylim(3.8, 4.4)

    axes[1].bar(groups, prices, color=["#8FB9A8", "#C4536B"])
    axes[1].set_title("Average Price ($)")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_category_breakdown(cat_df: pd.DataFrame, out_path: str = "chart_by_category.png") -> None:
    """Grouped bar chart of average rating by category, fragrance-free vs. fragranced."""
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(cat_df))
    width = 0.35

    ax.bar([i - width / 2 for i in x], cat_df["FF_avg_rating"], width,
           label="Fragrance-free", color="#8FB9A8")
    ax.bar([i + width / 2 for i in x], cat_df["Fragranced_avg_rating"], width,
           label="Fragranced", color="#C4536B")

    ax.set_xticks(list(x))
    ax.set_xticklabels(cat_df["Category"], rotation=20, ha="right")
    ax.set_ylabel("Average Rating")
    ax.set_title("Average Rating by Category: Fragrance-Free vs. Fragranced")
    ax.legend()
    ax.set_ylim(3.5, 4.6)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


if __name__ == "__main__":
    raw_df = load_data()

    print("=== Data Exploration (before cleaning) ===")
    explore_data(raw_df)
    plot_rank_distribution(raw_df)

    print("\n=== Cleaning ===")
    df = clean_data(raw_df)

    summary = overall_comparison(df)
    print("=== Overall ===")
    for k, v in summary.items():
        print(f"{k}: {v}")

    cat_df = category_breakdown(df)
    print("\n=== By Category ===")
    print(cat_df.to_string(index=False))

    plot_overall_comparison(summary)
    plot_category_breakdown(cat_df)
    print("\nCharts saved: chart_overall.png, chart_by_category.png")
