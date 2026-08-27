"""Tests for pxygen.cli — argument parsing and dispatch."""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from pxygen.cli import _build_parser, configure_logging, main

# ---------------------------------------------------------------------------
# _build_parser — flag parsing
# ---------------------------------------------------------------------------


class TestParser:
    def _parse(self, argv):
        return _build_parser().parse_args(argv)

    def test_input_and_output(self):
        args = self._parse(["-i", "/footage", "-o", "/proxy"])
        assert args.input == "/footage"
        assert args.output == "/proxy"

    def test_version_flag_prints_version_and_exits(self, capsys):
        for flag in ("-v", "-V", "--version"):
            with pytest.raises(SystemExit) as exc_info:
                self._parse([flag])
            assert exc_info.value.code == 0
        assert "pxygen v" in capsys.readouterr().out

    def test_long_input_output(self):
        args = self._parse(["--input", "/footage", "--output", "/proxy"])
        assert args.input == "/footage"
        assert args.output == "/proxy"

    def test_in_depth_short(self):
        args = self._parse(["-i", "/f", "-o", "/p", "-n", "3"])
        assert args.in_depth == 3

    def test_out_depth_short(self):
        args = self._parse(["-i", "/f", "-o", "/p", "-d", "6"])
        assert args.out_depth == 6

    def test_group_short(self):
        args = self._parse(["-i", "comp.json", "-o", "/p", "-g", "b"])
        assert args.group == "b"

    def test_group_invalid_raises(self):
        with pytest.raises(SystemExit):
            self._parse(["-i", "comp.json", "-o", "/p", "-g", "c"])

    def test_filter_short(self):
        # comma-joined tokens are tolerated; parser passes them through raw
        args = self._parse(["-i", "/f", "-o", "/p", "-f", "Day1,Day2"])
        assert args.filter == ["Day1,Day2"]

    def test_select_short(self):
        args = self._parse(["-i", "/f", "-o", "/p", "-s"])
        assert args.select is True

    def test_select_and_filter_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            self._parse(["-i", "/f", "-o", "/p", "-s", "-f", "Day1"])

    def test_codec_short(self):
        args = self._parse(["-i", "/f", "-o", "/p", "-k", "prores"])
        assert args.codec == "prores"

    def test_codec_invalid_raises(self):
        with pytest.raises(SystemExit):
            self._parse(["-i", "/f", "-o", "/p", "-k", "vp9"])

    def test_defaults(self):
        args = self._parse(["-i", "/f", "-o", "/p"])
        assert args.in_depth == 1
        assert args.out_depth == 2
        assert args.group == "a"
        assert args.codec == "auto"
        assert args.log_level == "warning"
        assert args.select is False
        assert args.filter is None

    def test_log_level_flag(self):
        args = self._parse(["-i", "/f", "-o", "/p", "--log-level", "debug"])
        assert args.log_level == "debug"

    def test_log_file_flag(self):
        args = self._parse(["-i", "/f", "-o", "/p", "--log-file", "/tmp/pxygen.log"])
        assert args.log_file == "/tmp/pxygen.log"


class TestLoggingConfig:
    def test_configure_logging_uses_standard_structured_format(self):
        with patch("pxygen.cli.logging.basicConfig") as mock_basic_config:
            configure_logging("debug")

        kwargs = mock_basic_config.call_args.kwargs
        assert kwargs["level"] == logging.DEBUG
        assert "%(asctime)s" in kwargs["format"]
        assert "%(levelname)" in kwargs["format"]
        assert "%(name)s" in kwargs["format"]
        assert kwargs["datefmt"] == "%Y-%m-%d %H:%M:%S"
        assert len(kwargs["handlers"]) == 1
        assert kwargs["force"] is True

    def test_configure_logging_adds_file_handler_when_requested(self, tmp_path):
        log_path = tmp_path / "logs" / "run.log"
        with patch("pxygen.cli.logging.basicConfig") as mock_basic_config:
            configure_logging("info", str(log_path))

        kwargs = mock_basic_config.call_args.kwargs
        assert len(kwargs["handlers"]) == 2
        assert log_path.parent.exists()

    def test_configure_logging_writes_messages_to_log_file(self, tmp_path):
        log_path = tmp_path / "logs" / "run.log"
        configure_logging("info", str(log_path))

        logger = logging.getLogger("pxygen.test")
        logger.info("hello log file")

        contents = log_path.read_text(encoding="utf-8")
        assert "INFO" in contents
        assert "pxygen.test" in contents
        assert "hello log file" in contents


# ---------------------------------------------------------------------------
# main() — dispatch logic
# ---------------------------------------------------------------------------

_MOCK_DIR = "pxygen.cli.process_directory_mode"
_MOCK_JSON = "pxygen.cli.process_json_mode"


class TestDispatch:
    def _run(self, argv):
        with patch("sys.argv", ["pxygen"] + argv):
            main()

    def test_directory_mode_dispatched(self, tmp_path):
        footage = tmp_path / "footage"
        footage.mkdir()
        with (
            patch(_MOCK_DIR) as mock_dir,
            patch(_MOCK_JSON) as mock_json,
            patch("pxygen.cli.configure_logging") as mock_logging,
        ):
            self._run(["-i", str(footage), "-o", "/proxy"])
            mock_dir.assert_called_once()
            mock_json.assert_not_called()
            mock_logging.assert_called_once_with("warning", None)
            kwargs = mock_dir.call_args.kwargs
            assert callable(kwargs["input_func"])
            assert callable(kwargs["output"])
            assert callable(kwargs["confirm_render"])

    def test_log_file_passed_to_logging_configuration(self, tmp_path):
        footage = tmp_path / "footage"
        footage.mkdir()
        log_path = tmp_path / "run.log"
        with (
            patch(_MOCK_DIR),
            patch("pxygen.cli.configure_logging") as mock_logging,
        ):
            self._run(["-i", str(footage), "-o", "/proxy", "--log-file", str(log_path)])

        mock_logging.assert_called_once_with("warning", str(log_path))

    def test_json_mode_dispatched(self, tmp_path):
        json_file = tmp_path / "comparison.json"
        json_file.write_text("{}")
        with patch(_MOCK_DIR) as mock_dir, patch(_MOCK_JSON) as mock_json:
            self._run(["-i", str(json_file), "-o", "/proxy"])
            mock_json.assert_called_once()
            mock_dir.assert_not_called()

    def test_json_detected_by_extension(self, tmp_path):
        # File doesn't need to exist — .json extension is enough
        json_path = "/nonexistent/comparison.json"
        with patch(_MOCK_DIR) as mock_dir, patch(_MOCK_JSON) as mock_json:
            self._run(["-i", json_path, "-o", "/proxy"])
            mock_json.assert_called_once()
            mock_dir.assert_not_called()

    def test_missing_output_exits(self, tmp_path):
        footage = tmp_path / "footage"
        footage.mkdir()
        with pytest.raises(SystemExit):
            self._run(["-i", str(footage)])

    def test_filter_accepts_space_separated_names(self):
        args = _build_parser().parse_args(
            ["-i", "/footage", "-o", "/proxy", "-f", "Day1", "Day2"]
        )
        assert args.filter == ["Day1", "Day2"]

    def test_no_args_exits(self):
        with pytest.raises(SystemExit):
            self._run([])

    def test_group_passed_to_json_mode(self, tmp_path):
        json_path = "/nonexistent/comp.json"
        with patch(_MOCK_JSON) as mock_json:
            self._run(["-i", json_path, "-o", "/proxy", "-g", "b"])
            _, call_kwargs = mock_json.call_args
            assert mock_json.call_args[0][2] == "b"  # side is 3rd positional arg

    def test_codec_passed_through(self, tmp_path):
        footage = tmp_path / "footage"
        footage.mkdir()
        with patch(_MOCK_DIR) as mock_dir:
            self._run(["-i", str(footage), "-o", "/proxy", "-k", "prores"])
            _, kwargs = mock_dir.call_args
            assert kwargs["codec"] == "prores"

    def test_attribute_error_logged(self, caplog):
        with patch("sys.argv", ["pxygen", "-i", "/tmp/a.json", "-o", "/proxy"]), patch(
            "pxygen.cli.configure_logging"
        ), patch(_MOCK_JSON, side_effect=AttributeError("boom")), caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit):
                main()
        assert "Resolve API error: boom" in caplog.text
