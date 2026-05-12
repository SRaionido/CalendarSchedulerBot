"""
utils/calendar_render.py - Generate a monthly calendar PNG showing all
members' availability as colour-coded vertical hour blocks.

Each day cell contains a 24-hour timeline. Each member gets their own
column within the cell, coloured distinctly. A legend at the bottom maps
colours to member names.

Returns the path to a temporary PNG file. The caller is responsible for
sending it to Discord and then deleting it.
"""

import calendar
import os
import tempfile
from datetime import date
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe for headless/server use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import config as config

TimeRange = Tuple[str, str]

# Up to 12 distinct member colours; repeats beyond that
_PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
    "#d4a6c8", "#86bcb6",
]

# Dark theme colours
_BG_FIGURE  = "#1e1e2e"
_BG_CELL    = "#2a2a3e"
_BG_EMPTY   = "#1a1a2e"
_BG_TLINE   = "#1e1e2e"
_COL_BORDER = "#3a3a5e"
_COL_GRID   = "#2e2e4e"
_COL_TEXT   = "#ccccee"
_COL_DOW    = "#aaaacc"
_COL_EMPTY  = "#444466"


def _time_to_float(t: str) -> float:
    h, m = map(int, t.split(":"))
    return h + m / 60.0


def _assign_colors(user_ids: List[str]) -> Dict[str, str]:
    return {uid: _PALETTE[i % len(_PALETTE)] for i, uid in enumerate(user_ids)}


def render_month(
    year: int,
    month: int,
    availability: Dict[str, Dict[str, List[TimeRange]]],  # uid → date → ranges
    usernames:    Dict[str, str],                          # uid → display name
) -> str:
    """
    Render a full-month availability calendar as a PNG and return its file path.
    The caller must delete the file after use.
    """
    os.makedirs(config.CALENDAR_OUTPUT_DIR, exist_ok=True)

    user_ids   = sorted(availability.keys())
    color_map  = _assign_colors(user_ids)
    cal        = calendar.monthcalendar(year, month)
    num_weeks  = len(cal)
    month_name = date(year, month, 1).strftime("%B %Y")

    # ── Figure dimensions ──────────────────────────────────────────────────────
    DAY_W    = 2.2   # inches per column
    WEEK_H   = 3.8   # inches per week row
    HEADER_H = 0.9   # space for title + day-of-week labels

    fig_w = DAY_W * 7
    fig_h = HEADER_H + WEEK_H * num_weeks

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=config.CALENDAR_DPI)
    fig.patch.set_facecolor(_BG_FIGURE)

    # Month title
    fig.text(
        0.5, 1 - 0.18 / fig_h,
        month_name,
        ha="center", va="top",
        fontsize=18, fontweight="bold", color="white", fontfamily="monospace",
    )

    # Day-of-week header
    for col, label in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        fig.text(
            (col + 0.5) / 7, 1 - 0.52 / fig_h,
            label,
            ha="center", va="top",
            fontsize=9, color=_COL_DOW, fontfamily="monospace",
        )

    # ── Week / day grid ────────────────────────────────────────────────────────
    AVAIL_TOP  = 1 - HEADER_H / fig_h       # fraction where week rows begin
    WEEK_H_FR  = (1 - HEADER_H / fig_h) / num_weeks
    CELL_W     = 1 / 7
    HOUR_START = 0
    HOUR_END   = 24

    for week_idx, week in enumerate(cal):
        week_top = AVAIL_TOP - week_idx * WEEK_H_FR
        week_bot = week_top - WEEK_H_FR

        for col_idx, day_num in enumerate(week):
            left = col_idx * CELL_W

            # Cell background
            ax_bg = fig.add_axes([left, week_bot, CELL_W, WEEK_H_FR])
            ax_bg.set_facecolor(_BG_CELL if day_num != 0 else _BG_EMPTY)
            for spine in ax_bg.spines.values():
                spine.set_edgecolor(_COL_BORDER)
                spine.set_linewidth(0.8)
            ax_bg.set_xticks([])
            ax_bg.set_yticks([])

            if day_num == 0:
                continue

            date_str  = f"{year}-{month:02d}-{day_num:02d}"
            day_users = [uid for uid in user_ids if date_str in availability.get(uid, {})]

            # Day number label
            ax_bg.text(
                0.06, 0.97, str(day_num),
                transform=ax_bg.transAxes,
                va="top", ha="left",
                fontsize=8, color=_COL_TEXT, fontweight="bold", fontfamily="monospace",
            )

            if not day_users:
                ax_bg.text(
                    0.5, 0.45, "—",
                    transform=ax_bg.transAxes,
                    va="center", ha="center",
                    fontsize=10, color=_COL_EMPTY,
                )
                continue

            # Timeline axes inset inside the cell
            M_L, M_R, M_T, M_B = 0.04, 0.04, 0.18, 0.04
            ax = fig.add_axes([
                left  + CELL_W   * M_L,
                week_bot + WEEK_H_FR * M_B,
                CELL_W   * (1 - M_L - M_R),
                WEEK_H_FR * (1 - M_T - M_B),
            ])
            ax.set_facecolor(_BG_TLINE)
            ax.set_xlim(0, len(day_users))
            ax.set_ylim(HOUR_END, HOUR_START)       # inverted: midnight at bottom
            ax.set_yticks(range(HOUR_START, HOUR_END + 1, 3))
            ax.set_yticklabels(
                [f"{h:02d}" for h in range(HOUR_START, HOUR_END + 1, 3)],
                fontsize=5, color="#888899",
            )
            ax.set_xticks([])
            ax.tick_params(axis="y", length=0, pad=1)
            for spine in ax.spines.values():
                spine.set_visible(False)

            # Hour grid lines
            for h in range(HOUR_START, HOUR_END + 1, 3):
                ax.axhline(h, color=_COL_GRID, linewidth=0.4, zorder=0)

            # Availability bars — one column per member
            bar_w = 0.8
            for u_idx, uid in enumerate(day_users):
                x_pos = u_idx + 0.5 - bar_w / 2
                for start_t, end_t in availability[uid][date_str]:
                    s = _time_to_float(start_t)
                    e = _time_to_float(end_t)
                    rect = mpatches.FancyBboxPatch(
                        (x_pos, s), bar_w, e - s,
                        boxstyle="round,pad=0.02",
                        facecolor=color_map[uid],
                        edgecolor="none",
                        alpha=0.85,
                        zorder=2,
                    )
                    ax.add_patch(rect)

    # ── Legend ─────────────────────────────────────────────────────────────────
    if user_ids:
        legend_patches = [
            mpatches.Patch(color=color_map[uid], label=usernames.get(uid, uid))
            for uid in user_ids
        ]
        fig.legend(
            handles=legend_patches,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.005),
            ncol=min(len(user_ids), 6),
            fontsize=7,
            framealpha=0.2,
            facecolor="#2a2a3e",
            edgecolor="#444466",
            labelcolor="white",
        )

    # ── Save to temp file ──────────────────────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(
        suffix=".png",
        dir=config.CALENDAR_OUTPUT_DIR,
        delete=False,
    )
    plt.savefig(
        tmp.name,
        dpi=config.CALENDAR_DPI,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)
    return tmp.name