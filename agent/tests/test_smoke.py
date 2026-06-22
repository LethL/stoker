import stoker_agent


def test_version_exposed() -> None:
    assert stoker_agent.__version__ == "0.1.0"
