import pytest

import polars as pl
from polars.exceptions import ComputeError


@pytest.mark.slow
@pytest.mark.parametrize("format", ["parquet", "csv", "ndjson", "ipc"])
def test_scan_nonexistent_cloud_path_17444(format: str) -> None:
    # https://github.com/pola-rs/polars/issues/17444

    path_str = f"s3://my-nonexistent-bucket/data.{format}"
    scan_function = getattr(pl, f"scan_{format}")

    # Just calling the scan function should not raise any errors
    if format == "ndjson":
        # NDJSON does not have a `retries` parameter yet - so use the default
        result = scan_function(path_str)
    else:
        result = scan_function(path_str, retries=0)
    assert isinstance(result, pl.LazyFrame)

    # Upon collection, it should fail
    with pytest.raises(ComputeError):
        result.collect()


def test_scan_credential_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    err_magic = "err_magic_3"

    def raises(*_: None, **__: None) -> None:
        raise AssertionError(err_magic)

    monkeypatch.setattr(pl.CredentialProviderAWS, "__init__", raises)

    with pytest.raises(AssertionError, match=err_magic):
        pl.scan_parquet("s3://bucket/path", credential_provider="auto")

    # Passing `None` should disable the automatic instantiation of
    # `CredentialProviderAWS`
    pl.scan_parquet("s3://bucket/path", credential_provider=None)
    # Passing `storage_options` should disable the automatic instantiation of
    # `CredentialProviderAWS`
    pl.scan_parquet("s3://bucket/path", credential_provider="auto", storage_options={})

    err_magic = "err_magic_7"

    def raises_2() -> pl.CredentialProviderFunctionReturn:
        raise AssertionError(err_magic)

    # Note to reader: It is converted to a ComputeError as it is being called
    # from Rust.
    with pytest.raises(ComputeError, match=err_magic):
        pl.scan_parquet("s3://bucket/path", credential_provider=raises_2).collect()
