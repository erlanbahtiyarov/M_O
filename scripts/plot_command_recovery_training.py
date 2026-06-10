"""Render training charts from command recovery summary JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = PROJECT_ROOT / "artifacts" / "training" / "command_recovery_summary.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "training" / "plots"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def get_font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def draw_line_chart(
    output_path: Path,
    title: str,
    x_values: list[int],
    train_values: list[float],
    val_values: list[float] | None,
    y_min: float,
    y_max: float,
    y_label_suffix: str = "",
) -> None:
    width, height = 1280, 720
    left, top, right, bottom = 110, 110, 1150, 590

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = get_font(30, bold=True)
    axis_font = get_font(18)
    label_font = get_font(20)
    legend_font = get_font(18)

    draw.text((80, 30), title, fill="black", font=title_font)
    draw.line((left, top, left, bottom), fill="black", width=3)
    draw.line((left, bottom, right, bottom), fill="black", width=3)

    scale = max(y_max - y_min, 1e-6)
    for tick in range(6):
        value = y_min + scale * tick / 5
        y = bottom - (bottom - top) * tick / 5
        draw.line((left - 8, y, left, y), fill="black", width=2)
        draw.text((20, y - 10), f"{value:.2f}{y_label_suffix}", fill="black", font=axis_font)

    x_step = (right - left - 60) / max(1, len(x_values) - 1)
    train_points = []
    val_points = []
    for idx, epoch in enumerate(x_values):
        x = left + 30 + idx * x_step
        train_y = bottom - (bottom - top) * ((train_values[idx] - y_min) / scale)
        train_points.append((x, train_y))
        if val_values is not None:
            val_y = bottom - (bottom - top) * ((val_values[idx] - y_min) / scale)
            val_points.append((x, val_y))
        draw.text((x - 10, bottom + 16), str(epoch), fill="black", font=axis_font)

    if len(train_points) > 1:
        draw.line(train_points, fill="#2F6DB3", width=4)
    for x, y in train_points:
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#2F6DB3", outline="#1F4E85")

    if val_values is not None:
        if len(val_points) > 1:
            draw.line(val_points, fill="#A61C00", width=4)
        for x, y in val_points:
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#A61C00", outline="#7C1300")

    draw.rectangle((920, 70, 1140, 135), outline="#BBBBBB", width=1)
    draw.line((940, 95, 990, 95), fill="#2F6DB3", width=4)
    draw.text((1005, 84), "Train", fill="black", font=legend_font)
    if val_values is not None:
        draw.line((940, 120, 990, 120), fill="#A61C00", width=4)
        draw.text((1005, 109), "Validation", fill="black", font=legend_font)

    draw.text((right - 120, bottom + 45), "Epoch", fill="black", font=label_font)
    image.save(output_path)


def draw_bar_chart(output_path: Path, title: str, labels: list[str], values: list[int]) -> None:
    width, height = 1280, 720
    left, top, right, bottom = 110, 110, 1150, 590

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = get_font(30, bold=True)
    axis_font = get_font(18)
    label_font = get_font(20)

    draw.text((80, 30), title, fill="black", font=title_font)
    draw.line((left, top, left, bottom), fill="black", width=3)
    draw.line((left, bottom, right, bottom), fill="black", width=3)

    ymax = max(values) if values else 1
    for tick in range(6):
        value = ymax * tick / 5
        y = bottom - (bottom - top) * tick / 5
        draw.line((left - 8, y, left, y), fill="black", width=2)
        draw.text((20, y - 10), f"{value:.0f}", fill="black", font=axis_font)

    step = (right - left - 40) / max(1, len(values))
    bar_width = int(step * 0.55)
    for idx, (label, value) in enumerate(zip(labels, values)):
        bar_left = left + 20 + idx * step + (step - bar_width) / 2
        bar_right = bar_left + bar_width
        bar_top = bottom - (bottom - top) * (value / max(ymax, 1))
        draw.rounded_rectangle(
            (bar_left, bar_top, bar_right, bottom),
            radius=10,
            fill="#4F81BD",
            outline="#2F5D8A",
        )
        draw.text((bar_left + 5, bar_top - 28), str(value), fill="black", font=axis_font)
        draw.text((bar_left - 15, bottom + 16), label, fill="black", font=label_font)

    image.save(output_path)


def draw_metric_bar_chart(
    output_path: Path,
    title: str,
    labels: list[str],
    values: list[float],
    ymax: float = 1.0,
) -> None:
    width, height = 1280, 720
    left, top, right, bottom = 110, 110, 1150, 590

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = get_font(30, bold=True)
    axis_font = get_font(18)
    label_font = get_font(20)

    draw.text((80, 30), title, fill="black", font=title_font)
    draw.line((left, top, left, bottom), fill="black", width=3)
    draw.line((left, bottom, right, bottom), fill="black", width=3)

    for tick in range(6):
        value = ymax * tick / 5
        y = bottom - (bottom - top) * tick / 5
        draw.line((left - 8, y, left, y), fill="black", width=2)
        draw.text((20, y - 10), f"{value:.2f}", fill="black", font=axis_font)

    step = (right - left - 40) / max(1, len(values))
    bar_width = int(step * 0.55)
    colors = ["#2F6DB3", "#A61C00", "#4F8A10"]
    outlines = ["#1F4E85", "#7C1300", "#346107"]
    for idx, (label, value) in enumerate(zip(labels, values)):
        bar_left = left + 20 + idx * step + (step - bar_width) / 2
        bar_right = bar_left + bar_width
        bar_top = bottom - (bottom - top) * (value / max(ymax, 1e-6))
        draw.rounded_rectangle(
            (bar_left, bar_top, bar_right, bottom),
            radius=10,
            fill=colors[idx % len(colors)],
            outline=outlines[idx % len(outlines)],
        )
        draw.text((bar_left + 5, bar_top - 28), f"{value:.3f}", fill="black", font=axis_font)
        draw.text((bar_left - 15, bottom + 16), label, fill="black", font=label_font)

    image.save(output_path)


def draw_confusion_matrix_chart(
    output_path: Path,
    title: str,
    labels: list[str],
    matrix: list[list[int]],
) -> None:
    cell_size = 70
    left, top = 260, 120
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    width = max(1280, left + cols * cell_size + 80)
    height = max(720, top + rows * cell_size + 120)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = get_font(28, bold=True)
    axis_font = get_font(16)
    label_font = get_font(16)

    draw.text((60, 30), title, fill="black", font=title_font)
    max_value = max((value for row in matrix for value in row), default=1)

    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            x0 = left + col_index * cell_size
            y0 = top + row_index * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            intensity = int(255 - (180 * (value / max(max_value, 1))))
            color = (intensity, intensity, 255)
            draw.rectangle((x0, y0, x1, y1), fill=color, outline="#888888", width=1)
            draw.text((x0 + 24, y0 + 24), str(value), fill="black", font=axis_font)

    for index, label in enumerate(labels):
        short_label = label[:10]
        x = left + index * cell_size + 8
        y = top - 28
        draw.text((x, y), short_label, fill="black", font=label_font)
        draw.text((40, top + index * cell_size + 24), short_label, fill="black", font=label_font)

    draw.text((left, top + rows * cell_size + 24), "Predicted label", fill="black", font=label_font)
    draw.text((40, 90), "True", fill="black", font=label_font)
    image.save(output_path)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    history = summary.get("history", [])
    if not history:
        raise SystemExit(f"No history found in {args.summary}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    epochs = [int(item["epoch"]) for item in history]
    train_loss = [float(item["loss"]) for item in history]
    train_accuracy = [float(item["accuracy"]) for item in history]
    val_loss = [float(item["val_loss"]) for item in history if "val_loss" in item]
    val_accuracy = [float(item["val_accuracy"]) for item in history if "val_accuracy" in item]

    loss_path = args.output_dir / "loss_curve.png"
    acc_path = args.output_dir / "accuracy_curve.png"
    split_path = args.output_dir / "split_sizes.png"
    final_acc_path = args.output_dir / "final_accuracy_by_split.png"
    confusion_path = args.output_dir / "test_confusion_matrix.png"

    draw_line_chart(
        output_path=loss_path,
        title="Loss Curve",
        x_values=epochs,
        train_values=train_loss,
        val_values=val_loss if len(val_loss) == len(epochs) else None,
        y_min=0.0,
        y_max=max(train_loss + val_loss + [1.0]),
    )
    draw_line_chart(
        output_path=acc_path,
        title="Accuracy Curve",
        x_values=epochs,
        train_values=train_accuracy,
        val_values=val_accuracy if len(val_accuracy) == len(epochs) else None,
        y_min=0.0,
        y_max=1.0,
    )
    draw_bar_chart(
        output_path=split_path,
        title="Dataset Split Sizes",
        labels=["Train", "Validation", "Test"],
        values=[
            int(summary.get("train_rows", 0)),
            int(summary.get("val_rows", 0)),
            int(summary.get("test_rows", 0)),
        ],
    )

    final_labels = ["Train"]
    final_values = [train_accuracy[-1]]
    if len(val_accuracy) == len(epochs):
        final_labels.append("Validation")
        final_values.append(val_accuracy[-1])
    if "test_accuracy" in summary:
        final_labels.append("Test")
        final_values.append(float(summary["test_accuracy"]))
    draw_metric_bar_chart(
        output_path=final_acc_path,
        title="Final Accuracy by Split",
        labels=final_labels,
        values=final_values,
    )

    if "test_confusion_matrix" in summary and "intent_labels" in summary:
        draw_confusion_matrix_chart(
            output_path=confusion_path,
            title="Test Confusion Matrix",
            labels=[str(item) for item in summary["intent_labels"]],
            matrix=[[int(value) for value in row] for row in summary["test_confusion_matrix"]],
        )

    plots = [
        str(loss_path.resolve()),
        str(acc_path.resolve()),
        str(split_path.resolve()),
        str(final_acc_path.resolve()),
    ]
    if confusion_path.exists():
        plots.append(str(confusion_path.resolve()))

    print(
        json.dumps(
            {
                "summary": str(args.summary.resolve()),
                "plots": plots,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
