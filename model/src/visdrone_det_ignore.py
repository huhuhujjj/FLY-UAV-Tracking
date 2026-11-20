"""Versioned local DET ignore policy for car, bus and truck evaluation.

This is a project policy, not a claim of bitwise equivalence to the official
MATLAB toolkit. It uses half-open pixel boxes and exact rectangle-union area.
"""
from __future__ import annotations

from math import isfinite

SOURCE_TO_LOCAL = {4: 0, 9: 1, 6: 2}
IGNORE_CATEGORIES = {0, 11}
IGNORE_FRACTION = 0.5


def _box(value, width: int, height: int) -> tuple[float, float, float, float]:
    x, y, w, h = (float(v) for v in value)
    if not all(isfinite(v) for v in (x, y, w, h)) or w <= 0 or h <= 0:
        raise ValueError('box coordinates must be finite with positive size')
    if x < 0 or y < 0 or x + w > width or y + h > height:
        raise ValueError('box must lie inside image')
    return x, y, x + w, y + h


def covered_fraction(box_xywh, ignore_xywh, width: int, height: int) -> float:
    """Fraction of a box covered by the union of ignored rectangles."""
    x1, y1, x2, y2 = _box(box_xywh, width, height)
    pieces = []
    for value in ignore_xywh:
        a, b, c, d = _box(value, width, height)
        left, top, right, bottom = max(x1, a), max(y1, b), min(x2, c), min(y2, d)
        if left < right and top < bottom:
            pieces.append((left, top, right, bottom))
    if not pieces:
        return 0.0
    xs = sorted({edge for a, _, c, _ in pieces for edge in (a, c)})
    area = 0.0
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((b, d) for a, b, c, d in pieces if a < right and c > left)
        if not intervals:
            continue
        first, last = intervals[0]
        length = 0.0
        for low, high in intervals[1:]:
            if low > last:
                length += last - first
                first, last = low, high
            else:
                last = max(last, high)
        length += last - first
        area += (right - left) * length
    return min(1.0, area / ((x2 - x1) * (y2 - y1)))


def prepare_image(source_rows: list[dict], detections: list[dict],
                  width: int, height: int) -> dict:
    """Filter source targets and predictions with the project ignore policy.

    Source rows use bbox_xywh, score, source_category. Detections use
    bbox_xywh, score and local_class (0=car, 1=bus, 2=truck). Other scored
    source classes, including van, do not become local target boxes.
    """
    if width <= 0 or height <= 0:
        raise ValueError('image dimensions must be positive')
    regions = []
    for row in source_rows:
        category = row['source_category']
        if category not in range(12) or row['score'] not in (0, 1):
            raise ValueError('invalid source category or score')
        _box(row['bbox_xywh'], width, height)
        if category in IGNORE_CATEGORIES or row['score'] == 0:
            regions.append(row['bbox_xywh'])
    kept_gt, kept_detections = [], []
    counts = {'source_target_boxes': 0, 'target_boxes_ignored': 0,
              'input_detections': len(detections), 'detections_ignored': 0,
              'ignore_boxes': len(regions)}
    for row in source_rows:
        if row['score'] != 1 or row['source_category'] not in SOURCE_TO_LOCAL:
            continue
        counts['source_target_boxes'] += 1
        if covered_fraction(row['bbox_xywh'], regions, width, height) >= IGNORE_FRACTION:
            counts['target_boxes_ignored'] += 1
        else:
            kept_gt.append({'bbox_xywh': row['bbox_xywh'],
                            'local_class': SOURCE_TO_LOCAL[row['source_category']]})
    for det in detections:
        if det['local_class'] not in (0, 1, 2) or not isfinite(float(det['score'])):
            raise ValueError('invalid detection class or score')
        _box(det['bbox_xywh'], width, height)
        if covered_fraction(det['bbox_xywh'], regions, width, height) >= IGNORE_FRACTION:
            counts['detections_ignored'] += 1
        else:
            kept_detections.append(det)
    return {'ground_truth': kept_gt, 'detections': kept_detections, 'counts': counts}
