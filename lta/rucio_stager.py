# rucio_stager.py
"""Module to implement the RucioStager component of the Long Term Archive."""

import asyncio
from logging import Logger
import logging
import os
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

from rest_tools.client import RestClient  # type: ignore
from rest_tools.server import from_environment  # type: ignore

from .component import COMMON_CONFIG, Component, now, status_loop, work_loop
from .log_format import StructuredFormatter
from .lta_types import BundleType

EXPECTED_CONFIG = COMMON_CONFIG.copy()
EXPECTED_CONFIG.update({
    "BUNDLER_OUTBOX_PATH": None,
    "DEST_QUOTA": None,
    "DEST_SITE": None,
    "RUCIO_INBOX_PATH": None,
    "WORK_RETRIES": "3",
    "WORK_TIMEOUT_SECONDS": "30",
})

def _enumerate_path(path: str) -> List[str]:
    """Recursively walk the file system to enumerate files at provided path."""
    # enumerate all of the files on disk to be checked
    disk_files = []
    for root, dirs, files in os.walk(path):
        disk_files.extend([os.path.join(root, file) for file in files])
    return disk_files

def _get_files_and_size(path: str) -> Tuple[List[str], int]:
    """Recursively walk and add the files of files in the file system."""
    # enumerate all of the files on disk to be checked
    disk_files = _enumerate_path(path)
    # for all of the files we want to check
    size = 0
    for disk_file in disk_files:
        # determine the size of the file
        size += os.path.getsize(disk_file)
    return (disk_files, size)


class RucioStager(Component):
    """
    RucioStager is a Long Term Archive component.

    A RucioStager is responsible for moving files from the Bundler staging
    area to the local Rucio RSE. This allows the bundle to be registered
    with Rucio and scheduled for transfer. This RucioStager component acts
    mostly to limit Rucio, so that it does not exceed the quota at the
    destination due to Rucio misconfiguration.
    """

    def __init__(self, config: Dict[str, str], logger: Logger) -> None:
        """
        Create a RucioStager component.

        config - A dictionary of required configuration values.
        logger - The object the rucio_stager should use for logging.
        """
        super(RucioStager, self).__init__("rucio_stager", config, logger)
        self.bundler_outbox_path = config["BUNDLER_OUTBOX_PATH"]
        self.dest_quota = int(config["DEST_QUOTA"])
        self.dest_site = config["DEST_SITE"]
        self.rucio_inbox_path = config["RUCIO_INBOX_PATH"]
        self.work_retries = int(config["WORK_RETRIES"])
        self.work_timeout_seconds = float(config["WORK_TIMEOUT_SECONDS"])
        pass

    def _do_status(self) -> Dict[str, Any]:
        """Contribute no additional status."""
        return {}

    def _expected_config(self) -> Dict[str, Optional[str]]:
        """Provide expected configuration dictionary."""
        return EXPECTED_CONFIG

    async def _do_work(self) -> None:
        """Perform a work cycle for this component."""
        self.logger.info("Starting work on Bundles.")
        work_claimed = True
        while work_claimed:
            work_claimed = await self._do_work_claim()
            work_claimed &= not self.run_once_and_die
        self.logger.info("Ending work on Bundles.")

    async def _do_work_claim(self) -> bool:
        """Claim a bundle and perform work on it."""
        # 1. Ask the LTA DB for the next Bundle to be staged
        # configure a RestClient to talk to the LTA DB
        lta_rc = RestClient(self.lta_rest_url,
                            token=self.lta_rest_token,
                            timeout=self.work_timeout_seconds,
                            retries=self.work_retries)
        self.logger.info("Asking the LTA DB for a Bundle to stage.")
        pop_body = {
            "claimant": f"{self.name}-{self.instance_uuid}"
        }
        response = await lta_rc.request('POST', f'/Bundles/actions/pop?dest={self.dest_site}&status=created', pop_body)
        self.logger.info(f"LTA DB responded with: {response}")
        bundle = response["bundle"]
        if not bundle:
            self.logger.info("LTA DB did not provide a Bundle to stage. Going on vacation.")
            return False
        # process the Bundle that we were given
        try:
            await self._stage_bundle(lta_rc, bundle)
        except Exception as e:
            await self._quarantine_bundle(lta_rc, bundle, f"{e}")
            raise e
        # even if we were successful, take a break between bundles
        return False

    async def _quarantine_bundle(self,
                                 lta_rc: RestClient,
                                 bundle: BundleType,
                                 reason: str) -> None:
        """Quarantine the supplied bundle using the supplied reason."""
        self.logger.error(f'Sending Bundle {bundle["uuid"]} to quarantine: {reason}.')
        right_now = now()
        patch_body = {
            "status": "quarantined",
            "reason": f"BY:{self.name}-{self.instance_uuid} REASON:{reason}",
            "work_priority_timestamp": right_now,
        }
        try:
            await lta_rc.request('PATCH', f'/Bundles/{bundle["uuid"]}', patch_body)
        except Exception as e:
            self.logger.error(f'Unable to quarantine Bundle {bundle["uuid"]}: {e}.')

    async def _stage_bundle(self, lta_rc: RestClient, bundle: BundleType) -> bool:
        """Stage the Bundle to Rucio for transfer."""
        bundle_id = bundle["uuid"]
        # measure rucio's inbox, our bundle, and the quota
        rucio_size = _get_files_and_size(self.rucio_inbox_path)[1]
        bundle_size = bundle["size"]
        total_size = rucio_size + bundle_size
        # if we would exceed our destination quota
        print(f"rucio_size: {rucio_size}")
        print(f"bundle_size: {bundle_size}")
        print(f"total_size: {total_size}")
        print(f"dest_quota: {self.dest_quota}")
        if total_size > self.dest_quota:
            self.logger.info(f"Bundle {bundle_id} has size {bundle_size} bytes.")
            self.logger.info(f"Rucio currently holds {rucio_size} bytes.")
            self.logger.info(f"Staging Bundle to Rucio would exceed the configured quota of {self.dest_quota}.")
            self.logger.info("Bundle will be unclaimed and staged at a later time.")
            await self._unclaim_bundle(lta_rc, bundle)
            return False
        # this bundle is ready to be staged
        bundle_name = os.path.basename(bundle["bundle_path"])
        src_path = os.path.join(self.bundler_outbox_path, bundle_name)
        dst_path = os.path.join(self.rucio_inbox_path, bundle_name)
        self.logger.info(f"Moving Bundle {src_path} -> {dst_path}")
        shutil.move(src_path, dst_path)
        # update the Bundle in the LTA DB
        self.logger.info("Bundle has been staged to the local Rucio RSE.")
        patch_body = {
            "bundle_path": dst_path,
            "claimed": False,
            "status": "staged",
            "reason": "",
            "update_timestamp": now(),
        }
        self.logger.info(f"PATCH /Bundles/{bundle_id} - '{patch_body}'")
        await lta_rc.request('PATCH', f'/Bundles/{bundle_id}', patch_body)
        return True

    async def _unclaim_bundle(self, lta_rc: RestClient, bundle: BundleType) -> bool:
        """Return the Bundle to the LTA DB, unclaim it for processing at a later date."""
        self.logger.info("Bundle is not ready to be staged; will unclaim it.")
        bundle_id = bundle["uuid"]
        right_now = now()
        patch_body: Dict[str, Any] = {
            "claimed": False,
            "update_timestamp": right_now,
            "work_priority_timestamp": right_now,
        }
        self.logger.info(f"PATCH /Bundles/{bundle_id} - '{patch_body}'")
        await lta_rc.request('PATCH', f'/Bundles/{bundle_id}', patch_body)
        return True


def runner() -> None:
    """Configure a RucioStager component from the environment and set it running."""
    # obtain our configuration from the environment
    config = from_environment(EXPECTED_CONFIG)
    # configure structured logging for the application
    structured_formatter = StructuredFormatter(
        component_type='RucioStager',
        component_name=config["COMPONENT_NAME"],
        ndjson=True)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(structured_formatter)
    root_logger = logging.getLogger(None)
    root_logger.setLevel(logging.NOTSET)
    root_logger.addHandler(stream_handler)
    logger = logging.getLogger("lta.rucio_stager")
    # create our RucioStager service
    rucio_stager = RucioStager(config, logger)
    # let's get to work
    rucio_stager.logger.info("Adding tasks to asyncio loop")
    loop = asyncio.get_event_loop()
    loop.create_task(status_loop(rucio_stager))
    loop.create_task(work_loop(rucio_stager))


def main() -> None:
    """Configure a RucioStager component from the environment and set it running."""
    runner()
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
