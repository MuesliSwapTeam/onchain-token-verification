from onchain_token_verification.contracts.cip68 import *
from onchain_token_verification.contracts.util import *


@dataclass()
class Registration(PlutusData):
    subject: Token
    signer: PubKeyHash
    metadata: Union[CIP68Datum, Nothing]


TOKENNAME = b"trusted"


def validator(datum: Registration, _r: NoRedeemer, ctx: ScriptContext) -> None:
    purpose = ctx.purpose
    if isinstance(purpose, Minting):
        own_addr = own_address(purpose.policy_id)
        pid = purpose.policy_id
    elif isinstance(purpose, Spending):
        assert (
            datum.signer in ctx.tx_info.signatories
        ), "Designated signer is not present in signatories"
        own_addr = resolve_spent_utxo(ctx.tx_info.inputs, purpose).address
        pid = policy_id_from_address(own_addr)
    else:
        assert False, "Wrong purpose"
    for utxo in ctx.tx_info.outputs:
        # - minted and existing tokens are sent to the correct contract
        # since the contract also runs this check when trying to spend,
        # if the tokens are not sent to the contract, they need to be burned
        if utxo.value.get(pid, {b"": 0}).get(TOKENNAME, 0) > 0:
            assert utxo.address == own_addr, "Sending tokens to wrong address"
        # - locking to the contract has the required signer
        if utxo.address == own_addr:
            tx_out_attached = utxo.datum
            if isinstance(tx_out_attached, SomeOutputDatumHash):
                # this cast does not but going on to treat the resulting object with the new type
                out_datum: Registration = ctx.tx_info.data.get(
                    tx_out_attached.datum_hash, Nothing()
                )
            elif isinstance(tx_out_attached, SomeOutputDatum):
                out_datum: Registration = tx_out_attached.datum
            else:
                assert False, "Outputs to contract address need a datum"
            assert (out_datum.signer in ctx.tx_info.signatories) or (
                out_datum.signer in ctx.tx_info.mint.keys()
            ), "Designated signer is not present in signatories or minting scripts"
