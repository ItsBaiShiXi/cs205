import pytest

from hiddencells import build, procurement


@pytest.fixture(scope="session")
def dataset(tmp_path_factory):
    """Every scenario."""
    out = tmp_path_factory.mktemp("procurement")
    return out, build.build_dataset(out, procurement.SCENARIOS)


@pytest.fixture(scope="session")
def fasteners(tmp_path_factory):
    """Only proc-01-fasteners, for tests that hard-code its answers."""
    out = tmp_path_factory.mktemp("fasteners")
    return out, build.build_dataset(out, procurement.SCENARIOS[:1])
