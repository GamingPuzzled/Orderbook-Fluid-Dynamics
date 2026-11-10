import numpy as np
import pytest

from lobflow.book import sample_book


def _arrays(rows: list[tuple[int, bool, bool, float, float]]):
    ts, snap, bid, px, amt = zip(*rows, strict=True)
    return (
        np.array(ts, dtype=np.int64),
        np.array(snap),
        np.array(bid),
        np.array(px, dtype=np.float64),
        np.array(amt, dtype=np.float64),
    )


ROWS = [
    # snapshot at t=0
    (0, True, True, 99.0, 1.0),
    (0, True, True, 98.0, 2.0),
    (0, True, False, 101.0, 3.0),
    (0, True, False, 102.0, 4.0),
    # t=10: ask 101 removed (swept), new ask 103
    (10, False, False, 101.0, 0.0),
    (10, False, False, 103.0, 5.0),
    # t=20: new snapshot resets book
    (20, True, True, 50.0, 1.0),
    (20, True, False, 60.0, 1.0),
]


def test_as_of_semantics_and_order_preserved() -> None:
    q = np.array([10, 5, 25], dtype=np.int64)  # unsorted on purpose
    s = sample_book(*_arrays(ROWS), q, n_levels=3)
    # q=10 includes update at t=10
    assert s.ask_px[0, 0] == 102.0
    assert list(s.ask_px[0, :2]) == [102.0, 103.0]
    # q=5 sees snapshot only
    assert s.ask_px[1, 0] == 101.0
    assert s.bid_px[1, 0] == 99.0 and s.bid_sz[1, 1] == 2.0
    assert np.isnan(s.bid_px[1, 2])
    # q=25 after reset: old levels gone
    assert s.bid_px[2, 0] == 50.0 and np.isnan(s.bid_px[2, 1])
    assert s.resets[2] == 2 and s.resets[1] == 1
    assert s.mid[1] == pytest.approx(100.0)


def test_query_before_first_update_is_empty() -> None:
    s = sample_book(*_arrays(ROWS), np.array([-1], dtype=np.int64), n_levels=2)
    assert np.isnan(s.bid_px[0, 0]) and s.last_update_ts[0] == -1


def test_rejects_unsorted_updates() -> None:
    bad = [ROWS[4], ROWS[0]]
    with pytest.raises(ValueError):
        sample_book(*_arrays(bad), np.array([0], dtype=np.int64))


def test_compiled_matches_reference_random_stream() -> None:
    from lobflow.book import sample_book, sample_book_reference

    rng = np.random.default_rng(7)
    n = 5000
    ts = np.sort(rng.integers(0, 1_000_000, n)).astype(np.int64)
    snap = np.zeros(n, dtype=bool)
    snap[:40] = True
    snap[2500:2520] = True  # mid-stream snapshot reset
    is_bid = rng.random(n) < 0.5
    px = np.where(
        is_bid, 100.0 - rng.integers(0, 60, n) * 0.5, 100.5 + rng.integers(0, 60, n) * 0.5
    )
    amt = np.where(rng.random(n) < 0.3, 0.0, rng.random(n) * 5)
    q = rng.integers(-10, 1_100_000, 300).astype(np.int64)
    a = sample_book(ts, snap, is_bid, px, amt, q, n_levels=20)
    b = sample_book_reference(ts, snap, is_bid, px, amt, q, n_levels=20)
    for f in ("bid_px", "bid_sz", "ask_px", "ask_sz", "last_update_ts", "resets"):
        np.testing.assert_array_equal(getattr(a, f), getattr(b, f), err_msg=f)


def test_tardis_retry_wait() -> None:
    from lobflow.tardis import _retry_wait

    assert _retry_wait("12", 0, 30.0) == 12.0
    assert _retry_wait(None, 2, 30.0) == 120.0
    assert _retry_wait(None, 10, 30.0) == 600.0
    assert _retry_wait("soon", 0, 5.0) == 5.0
