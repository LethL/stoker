import stoker_server


def test_version_exposed() -> None:
    assert stoker_server.__version__ == "0.1.0"
