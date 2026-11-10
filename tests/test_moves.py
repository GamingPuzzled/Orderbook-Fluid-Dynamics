import polars as pl
import pytest

from lobflow.moves import common_sizes, log_frame, move_stats

MS = 1000


def _tot(log: pl.DataFrame, direction: str = "toward") -> dict[str, float]:
    out = move_stats(log, set(), lot=100_000).filter(pl.col("direction") == direction)
    cols = ["v", "v_exact", "v_same", "v_src_first", "v_tgt_first", "v_ctrl"]
    return out.select(pl.col(cols).sum()).row(0, named=True)


def test_exact_matches_by_timing_and_price() -> None:
    # (event, t_us, d, kind, size, depth_px); sizes are multiples of lot 0.001
    log = log_frame(
        [
            (0, 30 * MS, 20, -1, 0.137, 120),  # deep cancel, deeper price
            (0, 30 * MS, 2, 1, 0.137, 102),  # near add, same message -> same
            (0, 50 * MS, 15, -1, 0.250, 115),
            (0, 80 * MS, 1, 1, 0.250, 101),  # cancel 30 ms earlier -> src_first
            (0, 120 * MS, 3, 1, 0.333, 103),
            (0, 150 * MS, 30, -1, 0.333, 130),  # cancel 30 ms later -> tgt_first
            (0, 200 * MS, 2, 1, 0.444, 102),
            (0, 210 * MS, 9, -1, 0.444, 102),  # same price (frame moved) -> not a move
            (0, 300 * MS, 2, 1, 0.555, 102),
            (0, 310 * MS, 9, -1, 0.556, 110),  # one lot larger -> control only
        ]
    )
    t = _tot(log)
    assert t["v"] == pytest.approx(0.137 + 0.25 + 0.333 + 0.444 + 0.555)
    assert t["v_same"] == pytest.approx(0.137)
    assert t["v_src_first"] == pytest.approx(0.25)
    assert t["v_tgt_first"] == pytest.approx(0.333)
    assert t["v_exact"] == pytest.approx(0.137 + 0.25 + 0.333)
    assert t["v_ctrl"] == pytest.approx(0.5 * 0.555)


def test_common_sizes_excluded_from_targets() -> None:
    log = log_frame([(0, 30 * MS, 20, -1, 1.0, 120), (0, 30 * MS, 2, 1, 1.0, 102)] * 5)
    assert move_stats(log, common_sizes([log]), lot=100_000).height == 0
