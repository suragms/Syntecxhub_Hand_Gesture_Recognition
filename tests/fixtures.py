"""Reusable deterministic landmark fixtures for pure recognition tests."""

from __future__ import annotations

from core.models import Point3D


def open_palm_points() -> tuple[Point3D, ...]:
    return (
        Point3D(0.0, 0.0), Point3D(-0.55, -0.10), Point3D(-0.75, -0.25), Point3D(-0.95, -0.45), Point3D(-1.12, -0.68),
        Point3D(-0.35, -0.65), Point3D(-0.38, -1.15), Point3D(-0.40, -1.60), Point3D(-0.42, -2.02),
        Point3D(0.0, -0.72), Point3D(0.0, -1.30), Point3D(0.0, -1.82), Point3D(0.0, -2.25),
        Point3D(0.35, -0.65), Point3D(0.40, -1.13), Point3D(0.45, -1.53), Point3D(0.50, -1.88),
        Point3D(0.67, -0.45), Point3D(0.77, -0.82), Point3D(0.85, -1.12), Point3D(0.92, -1.40),
    )


def fist_points() -> tuple[Point3D, ...]:
    points = list(open_palm_points())
    # Fold distal segments toward the palm while preserving nonzero palm scale.
    for mcp, pip, dip, tip, x in ((5, 6, 7, 8, -0.3), (9, 10, 11, 12, 0.0), (13, 14, 15, 16, 0.3), (17, 18, 19, 20, 0.55)):
        points[mcp] = Point3D(x, -0.55)
        points[pip] = Point3D(x, -0.40)
        points[dip] = Point3D(x + 0.13, -0.25)
        points[tip] = Point3D(x + 0.05, -0.10)
    points[1], points[2], points[3], points[4] = (
        Point3D(-0.35, -0.05), Point3D(-0.22, -0.10), Point3D(-0.15, 0.04), Point3D(-0.28, 0.10)
    )
    return tuple(points)


def thumbs_up_points() -> tuple[Point3D, ...]:
    points = list(fist_points())
    points[1], points[2], points[3], points[4] = (
        Point3D(-0.25, -0.10), Point3D(-0.40, -0.45), Point3D(-0.40, -0.95), Point3D(-0.35, -1.42)
    )
    return tuple(points)
