import json

from b200_emu.cli import main


def test_cli_text(capsys):
    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "B200" in out
    assert "HBM3e" in out
    assert "emulator" in out.lower()


def test_cli_json(capsys):
    rc = main(["--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "NVIDIA B200"
    assert payload["num_sms"] == 208
    assert payload["emulated"] is True
