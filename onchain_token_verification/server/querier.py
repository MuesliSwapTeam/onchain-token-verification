import logging
from collections import defaultdict
from typing import Union
from pathlib import Path
import uuid
import json

import pycardano
from opshin.ledger.api_v2 import Nothing
from pycardano import OgmiosChainContext, Network, AssetName, ScriptHash
import opshin

from onchain_token_verification.contracts.cip68 import CIP68Datum
from onchain_token_verification.cip68 import cip68_to_json

_LOGGER = logging.getLogger(__name__)

from ..utils import network, ogmios_url

# initialize an Ogmios Chain context
context = OgmiosChainContext(f"{ogmios_url}", network=network)

# path to store temporary data
# for optimal use, mount in RAM
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True, parents=True)


def atomic_dump(content: str, p: Path, mode="w"):
    # This sounds more drastic than it is
    new_path = Path(str(p) + ".new" + str(uuid.uuid4()))
    with new_path.open(mode) as fp:
        fp.write(content)
    new_path.replace(p)


from ..contracts import (
    register_token_mistrust,
    register_authority_trust,
    register_token_trust,
)

contracts = [
    register_authority_trust,
    register_token_trust,
    register_token_mistrust,
]
contract_artifcats = [
    opshin.generate_artifacts(opshin.build(contract.__file__, force_three_params=True))
    for contract in contracts
]


def main():
    _LOGGER.debug("Starting fetching of contract UTxOs")
    # TODO nicely restructure to re-run periodically
    for contract, artifacts in zip(contracts, contract_artifcats):
        # keep a list for all registered subjects and who signed them
        registered_subjects = defaultdict(list)

        _LOGGER.debug(f"Fetching UTxOs for {contract.__name__}")
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
            if utxo.output.amount.multi_asset.get(policy_id, {}).get(tokenname, 0) != 1:
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
            registered_subjects[trust_datum.subject.hex()].append(
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
            # TODO also fetch the metadata associated with a token

        contract_name = Path(contract.__file__).stem
        contract_data_path = data_dir / (contract_name + ".json")
        atomic_dump(
            json.dumps(registered_subjects, separators=(",", ":")), contract_data_path
        )


if __name__ == "__main__":
    main()
