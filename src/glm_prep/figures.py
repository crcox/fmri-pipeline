from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from nilearn.plotting import plot_design_matrix, plot_design_matrix_correlation

from glm_prep.artifacts import DesignMatrix, RegressorInfo, RegressorSource
from glm_prep.domain import RunKey

_SOURCE_COLORS = {
    RegressorSource.STIMULUS: "tab:blue",
    RegressorSource.DRIFT: "tab:orange",
    RegressorSource.MOTION: "tab:green",
    RegressorSource.ACOMPCOR: "tab:red",
    RegressorSource.TEDANA: "tab:purple",
}


def save_figure(fig: Figure, path: Path, dpi: int = 100) -> None:
    fig.savefig(  # pyright: ignore[reportUnknownMemberType]
        path, dpi=dpi, bbox_inches="tight"
    )


def figure_prefix(root: Path, run_key: RunKey) -> Path:
    design_dir = root / f"sub-{run_key.subject:03d}" / "figures"
    design_stem = f"sub-{run_key.subject:03d}_run-{run_key.run:02d}_design"
    return design_dir / design_stem


def design_matrix_to_dataframe(
    design: DesignMatrix,
) -> pd.DataFrame:
    return pd.DataFrame(
        design.matrix,
        columns=[r.name for r in design.regressors],
    )


def regressor_ranges_by_source(info: list[RegressorInfo]):
    columns_by_source: dict[RegressorSource, list[int]] = defaultdict(list)
    for reg in info:
        columns_by_source[reg.source].append(reg.column)

    ranges_by_source = {
        src: (min(cols), max(cols)) for src, cols in columns_by_source.items()
    }

    return ranges_by_source


def remove_xtick_labels(ax: Axes) -> Axes:
    ax.set_xticks([])

    return ax


def remove_tick_labels(ax: Axes) -> Axes:
    ax.set_xticks([])
    ax.set_yticks([])

    return ax


def add_source_labels(ax: Axes, ranges: dict[RegressorSource, tuple[int, int]]) -> Axes:
    centers = {source: (start + end) / 2 for source, (start, end) in ranges.items()}

    ax = remove_tick_labels(ax)

    for source, center in centers.items():
        ax.text(
            center,
            -5,
            source.value,
            ha="center",
            va="top",
            fontsize=10,
        )

    for source, center in centers.items():
        ax.text(
            -5,
            center,
            source.value,
            ha="right",
            va="center",
            rotation=90,
            fontsize=10,
        )

    return ax


def add_bands_across_top(
    ax: Axes, ranges: dict[RegressorSource, tuple[int, int]], line_width=1
) -> Axes:
    for source, (start, end) in ranges.items():
        ax.axvspan(
            xmin=start - 0.5,
            xmax=end + 0.5,
            ymin=1.00,
            ymax=1.0 + (line_width / 100),
            color=_SOURCE_COLORS[source],
            clip_on=False,
        )

    return ax


def add_bands_down_left(
    ax: Axes, ranges: dict[RegressorSource, tuple[int, int]]
) -> Axes:
    for source, (start, end) in ranges.items():
        ax.axhspan(  # pyright: ignore[reportUnknownMemberType]
            xmin=-0.01,
            xmax=0.0,
            ymin=start - 0.5,
            ymax=end + 0.5,
            color=_SOURCE_COLORS[source],
            clip_on=False,
        )

    return ax


def add_source_bands(ax: Axes, ranges: dict[RegressorSource, tuple[int, int]]) -> Axes:
    ax = add_bands_across_top(ax, ranges)
    ax = add_bands_down_left(ax, ranges)

    return ax


def add_vertical_boundaries(
    ax: Axes, ranges: dict[RegressorSource, tuple[int, int]]
) -> Axes:
    boundaries: set[int] = set()
    for _, end in ranges.values():
        boundaries.add(end)

    boundaries.remove(max(boundaries))

    for boundary in boundaries:
        ax.axvline(  # pyright: ignore[reportUnknownMemberType]
            boundary + 0.5,
            color="black",
            linewidth=1.0,
        )

    return ax


def add_source_boundaries(
    ax: Axes, ranges: dict[RegressorSource, tuple[int, int]]
) -> Axes:
    ax = add_vertical_boundaries(ax, ranges)
    ax = add_horizontal_boundaries(ax, ranges)
    return ax


def add_horizontal_boundaries(
    ax: Axes, ranges: dict[RegressorSource, tuple[int, int]]
) -> Axes:
    boundaries: set[int] = set()
    for _, end in ranges.values():
        boundaries.add(end)

    boundaries.remove(max(boundaries))

    for boundary in boundaries:
        ax.axhline(  # pyright: ignore[reportUnknownMemberType]
            boundary + 0.5,
            color="black",
            linewidth=1.0,
        )

    return ax


def save_design_matrix_figure(
    design: DesignMatrix, root: Path, run_key: RunKey
) -> None:
    prefix = figure_prefix(root, run_key)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    design_df = design_matrix_to_dataframe(design)

    ax = plot_design_matrix(design_df)

    if ax is None or not isinstance(ax, Axes):
        raise RuntimeError(
            f"Expected 'design_ax' to be of type 'matplotlib.axes.Axes', received {type(ax)!r}."  # pyright: ignore[reportUnknownArgumentType]
        )

    ranges_by_source = regressor_ranges_by_source(design.regressors)
    remove_xtick_labels(ax)
    add_bands_across_top(ax, ranges_by_source, line_width=2)
    add_source_legend(ax)

    fig = ax.figure
    fig.set_size_inches(12, 4)

    save_figure(fig, prefix.parent / f"{prefix.name}.svg")
    plt.close(fig)


def add_source_legend(ax: Axes) -> Axes:
    handles = [
        Patch(
            facecolor=color,
            edgecolor="black",
            label=source.value,
        )
        for source, color in _SOURCE_COLORS.items()
    ]

    ax.legend(
        handles=handles,
        title="Regressor source",
        loc="upper center",
        bbox_to_anchor=(0.5, -0.03),
        ncol=3,
        frameon=False,
    )

    return ax


def save_design_matrix_correlation_figure(
    design: DesignMatrix, root: Path, run_key: RunKey
) -> None:
    prefix = figure_prefix(root, run_key)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    design_df = design_matrix_to_dataframe(design)

    corr_img = plot_design_matrix_correlation(design_df)
    ax = corr_img.axes

    if ax is None or not isinstance(ax, Axes):
        raise RuntimeError(
            f"Expected 'corr_ax' to be of type 'matplotlib.axes.Axes', received {type(ax)!r}."  # pyright: ignore[reportUnknownArgumentType]
        )

    ranges_by_source = regressor_ranges_by_source(design.regressors)

    remove_tick_labels(ax)
    add_source_boundaries(ax, ranges_by_source)
    add_source_bands(ax, ranges_by_source)
    add_source_legend(ax)

    fig = ax.figure

    save_figure(fig, prefix.parent / f"{prefix.name}_correlation.svg")

    plt.close(fig)
