import logging
from collections import defaultdict
from pathlib import Path
import uuid
import json

import pycardano
from pycardano import OgmiosChainContext, Network
import opshin

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
contract_artifcats = [opshin.build(contract.__file__) for contract in contracts]


def main():
    _LOGGER.debug("Starting fetching of contract UTxOs")
    # TODO nicely restructure to re-run periodically
    for contract, artifacts in zip(contracts, contract_artifcats):
        # keep a list for all registered subjects and who signed them
        registered_subjects = defaultdict(list)

        _LOGGER.debug(f"Fetching UTxOs for {contract.__name__}")
        registration_class = contract.Registration
        tokenname = contract.TOKENNAME
        address = artifacts.mainnet_addr
        for utxo in context.utxos(address):
            # validate that the output has the valid format
            if utxo.output.amount[artifacts.policy_id][tokenname] != 1:
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
                trust_datum = registration_class.from_cbor(utxo.output.datum.to_cbor())
            except pycardano.DeserializeException as e:
                _LOGGER.debug(
                    f"UTxO {utxo.input.transaction_id}#{utxo.input.index} contains malformed datum"
                )
                continue
            registered_subjects[
                trust_datum.subject.to_cbor("hex")
            ] = trust_datum.signer.to_primitive().hex()
            # TODO also fetch the metadata associated with a token

        contract_name = Path(contract.__file__).stem
        contract_data_path = data_dir / (contract_name + ".json")
        atomic_dump(
            json.dumps(registered_subjects, separators=(":", ",")), contract_data_path
        )


if __name__ == "__main__":
    main()
