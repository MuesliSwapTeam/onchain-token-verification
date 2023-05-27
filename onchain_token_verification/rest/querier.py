import argparse
import logging
import time
from collections import defaultdict
from pathlib import Path
import uuid
import json
import concurrent.futures

import pycardano
from opshin.ledger.api_v2 import Nothing
from pycardano import OgmiosChainContext, Network, AssetName, ScriptHash, PlutusData

from gelidum import freeze

logging.basicConfig(level=logging.INFO)

from onchain_token_verification.cip68 import cip68_to_json
from onchain_token_verification.rest.util import (
    CONTRACTS,
    CONTRACT_ARTIFACTS,
    contract_data_path,
    FULL_LIST,
    SIGNERS,
)

_LOGGER = logging.getLogger(__name__)

from ..utils import network, ogmios_url

# initialize an Ogmios Chain context
context = OgmiosChainContext(f"{ogmios_url}", network=network)


def atomic_dump(content: str, p: Path, mode="w"):
    # This sounds more drastic than it is
    new_path = Path(str(p) + ".new" + str(uuid.uuid4()))
    with new_path.open(mode) as fp:
        fp.write(content)
    new_path.replace(p)


def fetch_entities(interval, contract, artifacts):
    contract_name = Path(contract.__file__).stem
    _LOGGER.info(f"Starting Fetching UTxOs for {contract_name}")
    while True:
        try:
            # keep a list for all registered subjects and who signed them
            registered_subjects = defaultdict(list)

            _LOGGER.debug(f"Fetching UTxOs for {contract_name}")
            registration_class = contract.Registration
            tokenname = AssetName(contract.TOKENNAME)
            policy_id = ScriptHash(bytes.fromhex(artifacts.policy_id))
            address = (
                artifacts.mainnet_addr
                if network == Network.MAINNET
                else artifacts.testnet_addr
            )
            for utxo in context.utxos(address):
                # validate that the output has the valid format
                if (
                    utxo.output.amount.multi_asset.get(policy_id, {}).get(tokenname, 0)
                    != 1
                ):
                    _LOGGER.debug(
                        f"UTxO {utxo.input.transaction_id}#{utxo.input.index} does not contain the required token"
                    )
                    continue
                if utxo.output.datum is None:
                    _LOGGER.debug(
                        f"UTxO {utxo.input.transaction_id}#{utxo.input.index} does not contain the required datum"
                    )
                    continue
                try:
                    trust_datum = registration_class.from_cbor(utxo.output.datum.cbor)
                except pycardano.DeserializeException as e:
                    _LOGGER.debug(
                        f"UTxO {utxo.input.transaction_id}#{utxo.input.index} contains malformed datum"
                    )
                    continue

                # generate a frozen version of the trust datum json representation
                subject = PlutusData.to_json(trust_datum.subject)
                # attach all the metadata and the original signer
                registered_subjects[subject].append(
                    {
                        "signer": trust_datum.signer.hex(),
                        "utxo": f"{utxo.input.transaction_id}#{utxo.input.index}",
                        **(
                            cip68_to_json(trust_datum.metadata)
                            if trust_datum.metadata != Nothing()
                            else {"metadata": None}
                        ),
                    }
                )

            registered_subjects_list = [
                {"subject": json.loads(s), "verifiers": d}
                for s, d in registered_subjects.items()
            ]

            atomic_dump(
                json.dumps(registered_subjects_list, separators=(",", ":")),
                contract_data_path(contract_name, FULL_LIST),
            )

            # restructure to store signed_by variation

            signed_by = defaultdict(list)
            for subject, trustees in registered_subjects.items():
                for trustee in trustees:
                    signed_by[trustee["signer"]].append(
                        {"subject": json.loads(subject), "signature": trustee}
                    )
            signed_by_list = [
                {"signer": signer, "subjects": subjects}
                for signer, subjects in signed_by.items()
            ]

            atomic_dump(
                json.dumps(signed_by_list, separators=(",", ":")),
                contract_data_path(contract_name, SIGNERS),
            )
        except Exception as e:
            _LOGGER.error(
                f"While fetching entities of {contract_name}, encountered unexpected issue",
                exc_info=e,
            )
        # re-fetch every 20 seconds
        time.sleep(interval)


def main():
    argparser = argparse.ArgumentParser(
        "Periodically fetches up-to-date information about vouched entities from the chain"
    )
    argparser.add_argument(
        "--interval",
        "-i",
        default=20,
        help="Period of re-fetching in seconds, defaults to 20s",
    )
    args = argparser.parse_args()
    interval = args.interval
    workers = len(CONTRACTS)
    _LOGGER.info(
        f"Starting fetching of contract UTxOs, running {workers} jobs concurrently."
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as tpe:
        for contract, artifacts in zip(CONTRACTS, CONTRACT_ARTIFACTS):
            tpe.submit(fetch_entities, interval, contract, artifacts)
        # will await completion of jobs here, indefinitely


if __name__ == "__main__":
    main()
