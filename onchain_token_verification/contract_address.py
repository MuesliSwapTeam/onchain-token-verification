from typing import Union, Optional, Dict

import click
import pycardano
from opshin.ledger.api_v2 import (
    SomeStakingCredential,
    NoStakingCredential,
    StakingPtr,
    StakingHash,
    PubKeyCredential,
    ScriptCredential,
    StakingCredential,
    LowerBoundPOSIXTime,
    NegInfPOSIXTime,
    FalseData,
    FinitePOSIXTime,
    PosInfPOSIXTime,
    TrueData,
    UpperBoundPOSIXTime,
    POSIXTimeRange,
    PubKeyHash,
    ValidatorHash,
    Address,
)

from .utils import get_contract


def to_staking_credential(
    sk: Union[
        pycardano.VerificationKeyHash,
        pycardano.ScriptHash,
        pycardano.PointerAddress,
        None,
    ]
):
    try:
        return SomeStakingCredential(to_staking_hash(sk))
    except NotImplementedError:
        return NoStakingCredential()


def to_staking_hash(
    sk: Union[
        pycardano.VerificationKeyHash, pycardano.ScriptHash, pycardano.PointerAddress
    ]
):
    if isinstance(sk, pycardano.PointerAddress):
        return StakingPtr(sk.slot, sk.tx_index, sk.cert_index)
    if isinstance(sk, pycardano.VerificationKeyHash):
        return StakingHash(PubKeyCredential(sk.payload))
    if isinstance(sk, pycardano.ScriptHash):
        return StakingHash(ScriptCredential(sk.payload))
    raise NotImplementedError(f"Unknown stake key type {type(sk)}")


def to_wdrl(wdrl: Optional[pycardano.Withdrawals]) -> Dict[StakingCredential, int]:
    if wdrl is None:
        return {}

    def m(k: bytes):
        sk = pycardano.Address.from_primitive(k).staking_part
        return to_staking_hash(sk)

    return {m(key): val for key, val in wdrl.to_primitive().items()}


def to_valid_range(validity_start: Optional[int], ttl: Optional[int], posix_from_slot):
    if validity_start is None:
        lower_bound = LowerBoundPOSIXTime(NegInfPOSIXTime(), FalseData())
    else:
        start = posix_from_slot(validity_start) * 1000
        lower_bound = LowerBoundPOSIXTime(FinitePOSIXTime(start), TrueData())
    if ttl is None:
        upper_bound = UpperBoundPOSIXTime(PosInfPOSIXTime(), FalseData())
    else:
        end = posix_from_slot(ttl) * 1000
        upper_bound = UpperBoundPOSIXTime(FinitePOSIXTime(end), TrueData())
    return POSIXTimeRange(lower_bound, upper_bound)


def to_pubkeyhash(vkh: pycardano.VerificationKeyHash):
    return PubKeyHash(vkh.payload)


def to_payment_credential(
    c: Union[pycardano.VerificationKeyHash, pycardano.ScriptHash]
):
    if isinstance(c, pycardano.VerificationKeyHash):
        return PubKeyCredential(PubKeyHash(c.payload))
    if isinstance(c, pycardano.ScriptHash):
        return ScriptCredential(ValidatorHash(c.payload))
    raise NotImplementedError(f"Unknown payment key type {type(c)}")


def to_address(a: pycardano.Address):
    return Address(
        to_payment_credential(a.payment_part),
        to_staking_credential(a.staking_part),
    )


@click.command()
@click.argument("contract_key")
def main(contract_key: str):
    contract = get_contract(contract_key)
    contract_addr = pycardano.Address(payment_part=pycardano.script_hash(contract))
    print(to_address(contract_addr).to_json())


if __name__ == "__main__":
    main()
