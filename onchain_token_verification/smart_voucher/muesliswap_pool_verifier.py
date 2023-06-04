from opshin.prelude import *


@dataclass()
class MintRedeemer(PlutusData):
    """
    signifies the position of the MuesliSwap pool among reference inputs
    """

    CONSTR_ID = 0

    pool_index: int


@dataclass()
class BurnRedeemer(PlutusData):
    """
    signifies the position of the MuesliSwap pool among reference inputs
    """

    CONSTR_ID = 1

    pool_index: int


# Threshold for required Lovelace
THRESHOLD = 100_000 * 1_000_000
# MS Pool Pubkey
POOL_SCRIPT_HASH = bytes.fromhex(
    "7045237d1eb0199c84dffe58fe6df7dc5d255eb4d418e4146d5721f8"
)
# MS pool nft policy
POOL_NFT_POLICYID = bytes.fromhex(
    "909133088303c49f3a30f1cc8ed553a73857a29779f6c6561cd8093f"
)


def validator(
    vouching_address: Address,
    r: Union[MintRedeemer, BurnRedeemer],
    context: ScriptContext,
):
    """
    Validates if
     - a MuesliSwap pool is among the reference inputs with at least THRESHOLD Lovelace and a token is minted to the vouching address
     - the same MuesliSwap pool  with less than THRESHOLD lovelace and the token is burned
    """
    purpose: Minting = context.purpose
    tx_info = context.tx_info

    # obtain the pool input
    ms_pool_input = tx_info.reference_inputs[r.pool_index]
    # obtain the pool size
    pool_size_ada = ms_pool_input.resolved.value[b""][b""]
    # obtain the pool nft token name
    ms_pool_nft_name = ms_pool_input.resolved.value[POOL_NFT_POLICYID].keys()[0]
    if isinstance(r, MintRedeemer):
        # check pool
        assert (
            ms_pool_input.resolved.address.payment_credential.credential_hash
            == POOL_SCRIPT_HASH
        ), "Specified wrong input, verification hash does not match"
        assert pool_size_ada >= THRESHOLD, (
            "Pool is too small, expected "
            + str(THRESHOLD)
            + " but got "
            + str(pool_size_ada)
        )
        total_outputs_to_vouching = 0
        # Check minting
        assert (
            tx_info.mint[purpose.policy_id][ms_pool_nft_name] == 1
        ), "Wrong amount of token minted"
        assert (
            sum(tx_info.mint[purpose.policy_id].values()) == 1
        ), "Minted other token than allowed nft name token"
        for o in tx_info.outputs:
            if o.address == vouching_address:
                assert (
                    sum(o.value.get(purpose.policy_id, {b"": 0}).values()) == 0
                ), "Can not send tokens anywhere other than vouching address as output"
            else:
                assert (
                    sum(o.value.get(purpose.policy_id, {b"": 0}).values()) == 1
                ), "Must send exactly one token to the vouching address"
                total_outputs_to_vouching += 1
        assert (
            total_outputs_to_vouching == 1
        ), "Must send exactly one token to the vouching address"
    elif isinstance(r, BurnRedeemer):
        assert (
            tx_info.mint[purpose.policy_id][ms_pool_nft_name] == -1
        ), "Wrong amount of token burned"
        assert (
            sum(
                [
                    sum(o.value.get(purpose.policy_id, {b"": 0}).values())
                    for o in tx_info.outputs
                ]
            )
            == 0
        ), "Can not send tokens anywhere as output"
        assert (
            ms_pool_input.resolved.address.payment_credential.credential_hash
            == POOL_SCRIPT_HASH
        ), "Specified wrong input, verification hash does not match"
        assert pool_size_ada < THRESHOLD, (
            "Pool is too large, expected not more than "
            + str(THRESHOLD)
            + " but got "
            + str(pool_size_ada)
        )

    else:
        assert False, "Wrong redeemer"
