from pathlib import Path
import os

import opshin

# path to store temporary data
# for optimal use, mount in RAM
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR.mkdir(exist_ok=True, parents=True)

from ..contracts import (
    token_mistrust,
    authority_trust,
    token_trust,
)

CONTRACTS = [
    authority_trust,
    token_trust,
    token_mistrust,
]
CONTRACT_ARTIFACTS = [
    opshin.generate_artifacts(opshin.build(contract.__file__, force_three_params=True))
    for contract in CONTRACTS
]


def contract_name(contract):
    return Path(contract.__file__).stem


FULL_LIST = "subjects"
SIGNERS = "signers"
PURPOSES = [FULL_LIST, SIGNERS]


def contract_data_path(contract_name: str, purpose: str):
    return DATA_DIR / f"{contract_name}-{purpose}.json"
