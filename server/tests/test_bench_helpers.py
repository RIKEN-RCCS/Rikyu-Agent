"""Unit tests for bench_download.py's pure helpers — no SSH, no cluster access.

Only exercises parse_sizes() and legacy_token_cost(), which do not touch the
network, filesystem, or any transport. The rest of bench_download.py
(make_fixture, bench_one, measure_legacy_tool, write_report, main) requires a
live host and is validated by hand against the real cluster separately, per
the leaf task's offline-only validation constraint.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bench_download import legacy_token_cost, parse_sizes  # noqa: E402


class TestParseSizes:
    def test_mixed_suffixes(self):
        assert parse_sizes("1K,1M,100M") == [1024, 1024**2, 100 * 1024**2]

    def test_bare_bytes(self):
        assert parse_sizes("512") == [512]

    def test_gigabyte_suffix_parses(self):
        # parse_sizes itself does not enforce the hard cap -- that check
        # lives in main() so it can log a NOTE; parsing "1G" must still work.
        assert parse_sizes("1G") == [1024**3]

    def test_lowercase_suffix(self):
        assert parse_sizes("1k,10m") == [1024, 10 * 1024**2]

    def test_whitespace_tolerant(self):
        assert parse_sizes(" 1K , 1M ") == [1024, 1024**2]

    def test_empty_tokens_ignored(self):
        assert parse_sizes("1K,,1M,") == [1024, 1024**2]

    def test_default_sweep_spec(self):
        assert parse_sizes("1K,1M,10M,100M") == [
            1024, 1024**2, 10 * 1024**2, 100 * 1024**2,
        ]

    def test_invalid_token_raises(self):
        import pytest
        with pytest.raises(ValueError):
            parse_sizes("1KB")  # trailing B not accepted, only K/M/G

    def test_invalid_unit_raises(self):
        import pytest
        with pytest.raises(ValueError):
            parse_sizes("1T")


class TestLegacyTokenCost:
    def test_size_3_no_padding(self):
        # 3 raw bytes -> exactly 4 base64 chars, no padding.
        result = legacy_token_cost(3)
        assert result["b64_bytes"] == 4
        assert result["est_tokens"] == 1.0
        assert result["size"] == 3

    def test_size_1_padded_to_one_block(self):
        # 1 raw byte still costs a full 4-char base64 block (with padding).
        result = legacy_token_cost(1)
        assert result["b64_bytes"] == 4

    def test_size_0(self):
        result = legacy_token_cost(0)
        assert result["b64_bytes"] == 0
        assert result["est_tokens"] == 0.0

    def test_size_1kb(self):
        result = legacy_token_cost(1024)
        assert result["b64_bytes"] == ((1024 + 2) // 3) * 4
        assert result["est_tokens"] == result["b64_bytes"] / 4

    def test_size_1mb_breaches_10k_token_cap(self):
        result = legacy_token_cost(1024**2)
        assert result["est_tokens"] > 10_000

    def test_est_tokens_is_quarter_of_b64_bytes(self):
        for size in (3, 100, 4096, 1_048_576):
            result = legacy_token_cost(size)
            assert result["est_tokens"] == result["b64_bytes"] / 4

    def test_monotonic_in_size(self):
        smaller = legacy_token_cost(1024)
        larger = legacy_token_cost(1024 * 1024)
        assert larger["b64_bytes"] > smaller["b64_bytes"]
        assert larger["est_tokens"] > smaller["est_tokens"]
