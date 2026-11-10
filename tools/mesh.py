"""STL loading, measurements and exact edge audits; standard library only."""
from pathlib import Path
import struct,math
from collections import Counter

def read_triangles(path: Path) -> list[tuple[tuple[float, ...], ...]]:
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:512]:
        vertices = [
            tuple(float(v) for v in line.split()[1:4])
            for line in data.decode("utf-8", "replace").splitlines()
            if line.strip().startswith("vertex")
        ]
        return [tuple(vertices[i : i + 3]) for i in range(0, len(vertices), 3)]
    count = struct.unpack_from("<I", data, 80)[0]
    triangles = []
    for i in range(count):
        values = struct.unpack_from("<12f", data, 84 + i * 50)
        triangles.append((values[3:6], values[6:9], values[9:12]))
    return triangles


def canonical(triangles, decimals: int) -> list:
    rounded = []
    for triangle in triangles:
        points = [tuple(round(c, decimals) for c in p) for p in triangle]
        start = points.index(min(points))
        rounded.append(tuple(points[start:] + points[:start]))
    return sorted(rounded)


def measure(triangles) -> tuple[float, float, list[float], list[float]]:
    """Signed volume, surface area, bbox min, bbox max."""
    volume = area = 0.0
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for a, b, c in triangles:
        volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        area += (cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2) ** 0.5 / 2
        for p in (a, b, c):
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    return volume, area, lo, hi


