"""Convert Tardis gzip CSVs to typed Parquet, streaming (bounded memory)."""

from __future__ import annotations

import gzip
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

BOOK_SCHEMA = pa.schema(
    [
        ("timestamp", pa.int64()),  # exchange timestamp, µs since epoch
        ("local_timestamp", pa.int64()),  # receive timestamp at Tardis recorder, µs
        ("is_snapshot", pa.bool_()),
        ("side", pa.string()),  # "bid" | "ask"
        ("price", pa.float64()),
        ("amount", pa.float64()),  # new absolute size at level; 0 = delete
    ]
)

TRADES_SCHEMA = pa.schema(
    [
        ("timestamp", pa.int64()),
        ("local_timestamp", pa.int64()),
        ("id", pa.string()),
        ("side", pa.string()),  # aggressor side: "buy" | "sell" | "unknown"
        ("price", pa.float64()),
        ("amount", pa.float64()),
    ]
)

SCHEMAS: dict[str, pa.Schema] = {"incremental_book_L2": BOOK_SCHEMA, "trades": TRADES_SCHEMA}


def csv_gz_to_parquet(src: Path, dest: Path, data_type: str, *, block_size: int = 1 << 25) -> int:
    """Stream ``src`` (Tardis csv.gz) into ``dest`` Parquet with a fixed schema.

    Returns the number of rows written. Columns ``exchange`` and ``symbol`` are dropped
    (they are encoded in the path).
    """
    if data_type not in SCHEMAS:
        raise ValueError(f"no schema for {data_type!r}")
    schema = SCHEMAS[data_type]
    convert = pacsv.ConvertOptions(
        column_types={f.name: f.type for f in schema},
        include_columns=schema.names,
    )
    read = pacsv.ReadOptions(block_size=block_size)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".parquet.part")
    rows = 0
    with gzip.open(src, "rb") as fh:
        reader = pacsv.open_csv(fh, read_options=read, convert_options=convert)
        with pq.ParquetWriter(tmp, schema, compression="zstd") as writer:
            for batch in reader:
                table = pa.Table.from_batches([batch]).select(schema.names).cast(schema)
                writer.write_table(table)
                rows += table.num_rows
    tmp.replace(dest)
    return rows


def infer_tick_size(prices: np.ndarray, *, decimals: int = 10) -> float:
    """Infer tick size as the smallest positive gap between distinct observed prices.

    Use on a book file with many levels (not trades), where adjacent ticks are observed.
    """
    uniq = np.unique(np.round(prices[np.isfinite(prices)], decimals))
    if uniq.size < 2:
        raise ValueError("need at least two distinct prices to infer tick size")
    diffs = np.diff(uniq)
    tick = float(np.round(diffs[diffs > 0].min(), decimals))
    if tick <= 0:
        raise ValueError("non-positive tick inferred")
    return tick
