# test_bundler.py
"""Unit tests for lta/bundler.py."""

from unittest.mock import call, mock_open, patch

import pytest  # type: ignore
from tornado.web import HTTPError  # type: ignore

from lta.bundler import Bundler, main
from .test_util import AsyncMock


@pytest.fixture
def config():
    """Supply a stock Bundler component configuration."""
    return {
        "BUNDLER_OUTBOX_PATH": "/tmp/lta/testing/bundler/outbox",
        "BUNDLER_WORKBOX_PATH": "/tmp/lta/testing/bundler/workbox",
        "COMPONENT_NAME": "testing-bundler",
        "HEARTBEAT_PATCH_RETRIES": "3",
        "HEARTBEAT_PATCH_TIMEOUT_SECONDS": "30",
        "HEARTBEAT_SLEEP_DURATION_SECONDS": "60",
        "LTA_REST_TOKEN": "fake-lta-rest-token",
        "LTA_REST_URL": "http://RmMNHdPhHpH2ZxfaFAC9d2jiIbf5pZiHDqy43rFLQiM.com/",
        "LTA_SITE_CONFIG": "etc/site.json",
        "SOURCE_SITE": "WIPAC",
        "WORK_RETRIES": "3",
        "WORK_SLEEP_DURATION_SECONDS": "60",
        "WORK_TIMEOUT_SECONDS": "30",
    }


def test_constructor_missing_config():
    """Fail with a TypeError if a configuration object isn't provided."""
    with pytest.raises(TypeError):
        Bundler()


def test_constructor_missing_logging():
    """Fail with a TypeError if a logging object isn't provided."""
    with pytest.raises(TypeError):
        config = {
            "PAN_GALACTIC_GARGLE_BLASTER": "Yummy"
        }
        Bundler(config)


def test_constructor_config_missing_values(mocker):
    """Fail with a ValueError if the configuration object is missing required configuration variables."""
    config = {
        "PAN_GALACTIC_GARGLE_BLASTER": "Yummy"
    }
    logger_mock = mocker.MagicMock()
    with pytest.raises(ValueError):
        Bundler(config, logger_mock)


def test_constructor_config_poison_values(config, mocker):
    """Fail with a ValueError if the configuration object is missing required configuration variables."""
    bundler_config = config.copy()
    bundler_config["LTA_REST_URL"] = None
    logger_mock = mocker.MagicMock()
    with pytest.raises(ValueError):
        Bundler(bundler_config, logger_mock)


def test_constructor_config(config, mocker):
    """Test that a Bundler can be constructed with a configuration object and a logging object."""
    logger_mock = mocker.MagicMock()
    p = Bundler(config, logger_mock)
    assert p.heartbeat_sleep_duration_seconds == 60
    assert p.lta_rest_url == "http://RmMNHdPhHpH2ZxfaFAC9d2jiIbf5pZiHDqy43rFLQiM.com/"
    assert p.name == "testing-bundler"
    assert p.work_sleep_duration_seconds == 60
    assert p.logger == logger_mock


def test_constructor_config_sleep_type_int(config, mocker):
    """Ensure that sleep seconds can also be provided as an integer."""
    logger_mock = mocker.MagicMock()
    p = Bundler(config, logger_mock)
    assert p.heartbeat_sleep_duration_seconds == 60
    assert p.lta_rest_url == "http://RmMNHdPhHpH2ZxfaFAC9d2jiIbf5pZiHDqy43rFLQiM.com/"
    assert p.name == "testing-bundler"
    assert p.work_sleep_duration_seconds == 60
    assert p.logger == logger_mock


def test_constructor_state(config, mocker):
    """Verify that the Bundler has a reasonable state when it is first constructed."""
    logger_mock = mocker.MagicMock()
    p = Bundler(config, logger_mock)
    assert p.last_work_begin_timestamp is p.last_work_end_timestamp


def test_do_status(config, mocker):
    """Verify that the Bundler has no additional state to offer."""
    logger_mock = mocker.MagicMock()
    p = Bundler(config, logger_mock)
    assert p._do_status() == {}


@pytest.mark.asyncio
async def test_script_main(config, mocker, monkeypatch):
    """
    Verify Bundler component behavior when run as a script.

    Test to make sure running the Bundler as a script does the setup work
    that we expect and then launches the bundler service.
    """
    for key in config.keys():
        monkeypatch.setenv(key, config[key])
    mock_event_loop = mocker.patch("asyncio.get_event_loop")
    mock_root_logger = mocker.patch("logging.getLogger")
    mock_status_loop = mocker.patch("lta.bundler.status_loop")
    mock_work_loop = mocker.patch("lta.bundler.work_loop")
    main()
    mock_event_loop.assert_called()
    mock_root_logger.assert_called()
    mock_status_loop.assert_called()
    mock_work_loop.assert_called()


@pytest.mark.asyncio
async def test_bundler_logs_configuration(mocker):
    """Test to make sure the Bundler logs its configuration."""
    logger_mock = mocker.MagicMock()
    bundler_config = {
        "BUNDLER_OUTBOX_PATH": "logme/tmp/lta/testing/bundler/outbox",
        "BUNDLER_WORKBOX_PATH": "logme/tmp/lta/testing/bundler/workbox",
        "COMPONENT_NAME": "logme-testing-bundler",
        "HEARTBEAT_PATCH_RETRIES": "1",
        "HEARTBEAT_PATCH_TIMEOUT_SECONDS": "20",
        "HEARTBEAT_SLEEP_DURATION_SECONDS": "30",
        "LTA_REST_TOKEN": "logme-fake-lta-rest-token",
        "LTA_REST_URL": "logme-http://RmMNHdPhHpH2ZxfaFAC9d2jiIbf5pZiHDqy43rFLQiM.com/",
        "LTA_SITE_CONFIG": "etc/site.json",
        "SOURCE_SITE": "WIPAC",
        "WORK_RETRIES": "5",
        "WORK_SLEEP_DURATION_SECONDS": "70",
        "WORK_TIMEOUT_SECONDS": "90",
    }
    Bundler(bundler_config, logger_mock)
    EXPECTED_LOGGER_CALLS = [
        call("bundler 'logme-testing-bundler' is configured:"),
        call('BUNDLER_OUTBOX_PATH = logme/tmp/lta/testing/bundler/outbox'),
        call('BUNDLER_WORKBOX_PATH = logme/tmp/lta/testing/bundler/workbox'),
        call('COMPONENT_NAME = logme-testing-bundler'),
        call('HEARTBEAT_PATCH_RETRIES = 1'),
        call('HEARTBEAT_PATCH_TIMEOUT_SECONDS = 20'),
        call('HEARTBEAT_SLEEP_DURATION_SECONDS = 30'),
        call('LTA_REST_TOKEN = logme-fake-lta-rest-token'),
        call('LTA_REST_URL = logme-http://RmMNHdPhHpH2ZxfaFAC9d2jiIbf5pZiHDqy43rFLQiM.com/'),
        call('LTA_SITE_CONFIG = etc/site.json'),
        call('SOURCE_SITE = WIPAC'),
        call('WORK_RETRIES = 5'),
        call('WORK_SLEEP_DURATION_SECONDS = 70'),
        call('WORK_TIMEOUT_SECONDS = 90'),
    ]
    logger_mock.info.assert_has_calls(EXPECTED_LOGGER_CALLS)


@pytest.mark.asyncio
async def test_bundler_run(config, mocker):
    """Test the Bundler does the work the bundler should do."""
    logger_mock = mocker.MagicMock()
    p = Bundler(config, logger_mock)
    p._do_work = AsyncMock()
    await p.run()
    p._do_work.assert_called()


@pytest.mark.asyncio
async def test_bundler_run_exception(config, mocker):
    """Test an error doesn't kill the Bundler."""
    logger_mock = mocker.MagicMock()
    p = Bundler(config, logger_mock)
    p.last_work_end_timestamp = None
    p._do_work = AsyncMock()
    p._do_work.side_effect = [Exception("bad thing happen!")]
    await p.run()
    p._do_work.assert_called()
    assert p.last_work_end_timestamp


@pytest.mark.asyncio
async def test_bundler_do_work_pop_exception(config, mocker):
    """Test that _do_work raises when the RestClient can't pop."""
    logger_mock = mocker.MagicMock()
    lta_rc_mock = mocker.patch("rest_tools.client.RestClient.request", new_callable=AsyncMock)
    lta_rc_mock.side_effect = HTTPError(500, "LTA DB on fire. Again.")
    p = Bundler(config, logger_mock)
    with pytest.raises(HTTPError):
        await p._do_work()
    lta_rc_mock.assert_called_with("POST", '/Bundles/actions/pop?source=WIPAC&status=specified', mocker.ANY)


@pytest.mark.asyncio
async def test_bundler_do_work_no_results(config, mocker):
    """Test that _do_work goes on vacation when the LTA DB has no work."""
    logger_mock = mocker.MagicMock()
    claim_mock = mocker.patch("lta.bundler.Bundler._do_work_claim", new_callable=AsyncMock)
    claim_mock.return_value = False
    p = Bundler(config, logger_mock)
    await p._do_work()


@pytest.mark.asyncio
async def test_bundler_do_work_claim_no_results(config, mocker):
    """Test that _do_work_claim returns False when the LTA DB has no work."""
    logger_mock = mocker.MagicMock()
    lta_rc_mock = mocker.patch("rest_tools.client.RestClient.request", new_callable=AsyncMock)
    lta_rc_mock.return_value = {
        "bundle": None
    }
    p = Bundler(config, logger_mock)
    assert not await p._do_work_claim()
    lta_rc_mock.assert_called_with("POST", '/Bundles/actions/pop?source=WIPAC&status=specified', mocker.ANY)


@pytest.mark.asyncio
async def test_bundler_do_work_yes_results(config, mocker):
    """Test that _do_work_claim processes each Bundle that it gets from the LTA DB."""
    BUNDLE_OBJ = {
        "uuid": "f74db80e-9661-40cc-9f01-8d087af23f56"
    }
    logger_mock = mocker.MagicMock()
    lta_rc_mock = mocker.patch("rest_tools.client.RestClient.request", new_callable=AsyncMock)
    lta_rc_mock.return_value = {
        "bundle": BUNDLE_OBJ,
    }
    dwb_mock = mocker.patch("lta.bundler.Bundler._do_work_bundle", new_callable=AsyncMock)
    p = Bundler(config, logger_mock)
    assert await p._do_work_claim()
    lta_rc_mock.assert_called_with("POST", '/Bundles/actions/pop?source=WIPAC&status=specified', mocker.ANY)
    dwb_mock.assert_called_with(lta_rc_mock, BUNDLE_OBJ)


@pytest.mark.asyncio
async def test_bundler_do_work_dest_results(config, mocker):
    """Test that _do_work_bundle does the work of preparing an archive."""
    logger_mock = mocker.MagicMock()
    lta_rc_mock = mocker.patch("rest_tools.client.RestClient.request", new_callable=AsyncMock)
    mock_zipfile_init = mocker.patch("zipfile.ZipFile.__init__")
    mock_zipfile_init.return_value = None
    mock_zipfile_write = mocker.patch("zipfile.ZipFile.write")
    mock_zipfile_write.return_value = None
    mock_shutil_move = mocker.patch("shutil.move")
    mock_shutil_move.return_value = None
    mock_adler32sum = mocker.patch("lta.bundler.adler32sum")
    mock_adler32sum.return_value = "89d5efeb"
    mock_sha512sum = mocker.patch("lta.bundler.sha512sum")
    mock_sha512sum.return_value = "c919210281b72327c179e26be799b06cdaf48bf6efce56fb9d53f758c1b997099831ad05453fdb1ba65be7b35d0b4c5cebfc439efbdf83317ba0e38bf6f42570"
    mock_os_path_getsize = mocker.patch("os.path.getsize")
    mock_os_path_getsize.return_value = 1048900
    mock_os_remove = mocker.patch("os.remove")
    mock_os_remove.return_value = None
    p = Bundler(config, logger_mock)
    BUNDLE_OBJ = {
        "uuid": "f74db80e-9661-40cc-9f01-8d087af23f56",
        "source": "WIPAC",
        "dest": "NERSC",
        "files": [{"logical_name": "/path/to/a/data/file", }],
    }
    with patch("builtins.open", mock_open(read_data="data")) as metadata_mock:
        await p._do_work_bundle(lta_rc_mock, BUNDLE_OBJ)
        metadata_mock.assert_called_with(mocker.ANY, mode="w")
