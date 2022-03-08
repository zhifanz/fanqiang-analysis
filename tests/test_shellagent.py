import pathlib
import jc


def test_jc_ping():
    with open(pathlib.Path(__file__).parent / "ping_stdout") as f:
        content = f.read()

    result = jc.parse("ping", content)
    assert result["destination_ip"] == "14.215.177.38"
    assert result["packets_transmitted"] == 3
    assert result["packets_received"] == 3
    assert result["round_trip_ms_min"] == 0.113
    assert result["round_trip_ms_avg"] == 0.223
    assert result["round_trip_ms_max"] == 0.292
    assert result["round_trip_ms_stddev"] == 0.078
