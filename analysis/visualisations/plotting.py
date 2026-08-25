"""Focused plotting helpers for publication figures."""

from __future__ import annotations

import csv
from pathlib import Path


PANEL_SPECS = (
    ("total_project_count", "Rank by total project count"),
    ("greedy_marginal_coverage", "Greedy marginal coverage"),
)


def plot_owner_sampling_coverage(
    figure_data_path: Path,
    *,
    png_path: Path,
    svg_path: Path,
    pdf_path: Path | None = None,
) -> None:
    """Draw the classic cumulative-coverage and new-project comparison."""

    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    with figure_data_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    cumulative_color = "#1F4E79"
    marginal_color = "#8FB9D8"

    with plt.rc_context(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
            "font.size": 10.5,
            "axes.titlesize": 12.5,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    ):
        fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.35), sharex=True, sharey=True)
        max_step = 0
        max_cumulative = 0
        cumulative_handle = None
        marginal_handle = None
        for axis, (strategy, title) in zip(axes, PANEL_SPECS, strict=True):
            selected = [row for row in rows if row["strategy"] == strategy]
            steps = [int(row["selection_step"]) for row in selected]
            cumulative = [int(row["cumulative_unique_projects"]) for row in selected]
            selection_steps = steps[1:]
            marginal = [int(row["marginal_unique_projects"]) for row in selected[1:]]
            max_step = max(max_step, max(steps))
            max_cumulative = max(max_cumulative, max(cumulative))

            marginal_handle = axis.bar(
                selection_steps,
                marginal,
                width=0.72,
                color=marginal_color,
                alpha=0.78,
                edgecolor="none",
                label="New unique projects",
                zorder=2,
            )
            (cumulative_handle,) = axis.plot(
                steps,
                cumulative,
                color=cumulative_color,
                linewidth=2.7,
                marker="o",
                markersize=3.3,
                markerfacecolor="white",
                markeredgewidth=1.1,
                label="Cumulative unique coverage",
                zorder=3,
            )
            axis.set_title(title, pad=10, weight="semibold")
            axis.set_xlabel("Researchers selected", labelpad=7)
            axis.grid(axis="y", color="#D7DDE3", linewidth=0.7, alpha=0.8, zorder=0)
            axis.set_axisbelow(True)
            axis.tick_params(axis="both", length=3, color="#606870")
            axis.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
            axis.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))

        axes[0].set_ylabel("Unique projects", labelpad=8)
        for axis in axes:
            axis.set_xlim(-0.3, max_step + 0.8)
            axis.set_ylim(0, max_cumulative * 1.08)
        fig.legend(
            [cumulative_handle, marginal_handle],
            ["Cumulative unique coverage", "New unique projects"],
            loc="center",
            bbox_to_anchor=(0.5, 0.145),
            ncol=2,
            frameon=False,
            handlelength=2.4,
            columnspacing=2.0,
        )
        fig.text(
            0.5,
            0.045,
            "Cumulative coverage is the unique project total after each selection; new "
            "unique projects are those not represented earlier. Contactability ignored.",
            ha="center",
            va="center",
            fontsize=9.0,
            color="#38434D",
        )
        fig.subplots_adjust(left=0.075, right=0.985, bottom=0.29, top=0.91, wspace=0.16)

        png_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_path, dpi=320)
        fig.savefig(svg_path)
        if pdf_path is not None:
            fig.savefig(pdf_path)
        plt.close(fig)


def plot_owner_sampling_portfolio_vs_marginal(
    figure_data_path: Path,
    *,
    png_path: Path,
    svg_path: Path,
    pdf_path: Path | None = None,
) -> None:
    """Draw paired portfolio-size and marginal-contribution bars."""

    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    with figure_data_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    portfolio_color = "#B65445"
    marginal_color = "#8FB9D8"
    nonzero_rows = [row for row in rows if int(row["selection_step"]) > 0]
    max_projects = max(
        max(int(row["owner_total_eligible_projects"]) for row in nonzero_rows),
        max(int(row["marginal_unique_projects"]) for row in nonzero_rows),
    )
    with plt.rc_context(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
            "font.size": 10.5,
            "axes.titlesize": 12.5,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    ):
        fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.95), sharex=True, sharey=True)
        portfolio_handle = None
        marginal_handle = None
        width = 0.38
        offset = width / 2
        for axis, (strategy, title) in zip(axes, PANEL_SPECS, strict=True):
            selected = [
                row
                for row in rows
                if row["strategy"] == strategy and int(row["selection_step"]) > 0
            ]
            steps = [int(row["selection_step"]) for row in selected]
            portfolio_total = [
                int(row["owner_total_eligible_projects"]) for row in selected
            ]
            marginal = [int(row["marginal_unique_projects"]) for row in selected]
            portfolio_handle = axis.bar(
                [step - offset for step in steps],
                portfolio_total,
                width=width,
                color=portfolio_color,
                alpha=0.86,
                edgecolor="none",
                label="Researcher's total projects",
                zorder=2,
            )
            marginal_handle = axis.bar(
                [step + offset for step in steps],
                marginal,
                width=width,
                color=marginal_color,
                alpha=0.86,
                edgecolor="none",
                label="New unique projects",
                zorder=2,
            )
            axis.set_title(title, pad=10, weight="semibold")
            axis.set_xlabel("Researchers selected", labelpad=7)
            axis.set_xlim(0.4, max(steps) + 0.6)
            axis.set_ylim(0, max_projects * 1.12)
            axis.set_xticks([1, 5, 10, 15, 20, 25])
            axis.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
            axis.grid(axis="y", color="#D7DDE3", linewidth=0.7, alpha=0.8, zorder=0)
            axis.set_axisbelow(True)
            axis.tick_params(axis="both", length=3, color="#606870")

        axes[0].set_ylabel("Projects", labelpad=8)
        fig.legend(
            [portfolio_handle, marginal_handle],
            ["Researcher's total projects", "New unique projects"],
            loc="center",
            bbox_to_anchor=(0.5, 0.16),
            ncol=2,
            frameon=False,
            columnspacing=2.2,
        )
        fig.text(
            0.5,
            0.06,
            "Red bars show the selected researcher's full eligible portfolio; blue bars "
            "show only projects not represented by earlier selections.\n"
            "The gap reflects overlap with previously selected portfolios. "
            "Contactability ignored.",
            ha="center",
            va="center",
            fontsize=8.8,
            color="#38434D",
        )
        fig.subplots_adjust(left=0.075, right=0.985, bottom=0.31, top=0.90, wspace=0.16)

        png_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_path, dpi=320)
        fig.savefig(svg_path)
        if pdf_path is not None:
            fig.savefig(pdf_path)
        plt.close(fig)
