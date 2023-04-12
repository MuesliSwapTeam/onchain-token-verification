from opshin.prelude import *


def policy_id_from_address(address: Address) -> PolicyId:
    # obtain the policy id for which this contract can validate minting/burning, based on the contract address
    return address.payment_credential.credential_hash


def own_address(own_policy_id: PolicyId) -> Address:
    # obtain the contract address for which this contract can validate spending, based on the policy id
    return Address(ScriptCredential(own_policy_id), NoStakingCredential())
