""" Registers a new authority for signatures, signed with the given key """

import click
from pycardano import (
    OgmiosChainContext,
    Address,
    TransactionBuilder,
    TransactionOutput,
    plutus_script_hash,
    Redeemer,
    MultiAsset,
    Value,
    PlutusV2Script,
)

from onchain_token_verification.utils import (
    get_address,
    get_signing_info,
    network,
    ogmios_url,
    get_contract,
)
from onchain_token_verification.contracts.register_authority_trust import (
    Registration,
    NoRedeemer,
    TOKENNAME,
)


@click.command()
@click.argument("signer_key")
@click.argument("authority_key")
def main(signer_key: str, authority_key: str):
    # Load chain context
    context = OgmiosChainContext(ogmios_url, network=network)

    # Load script info
    contract: PlutusV2Script = get_contract("register_authority_trust")
    contract_hash = plutus_script_hash(contract)
    contract_address = Address(contract_hash, network=network)

    # Get payment address
    signer_key_address: Address = get_address(signer_key)
    authority_key_address: Address = get_address(authority_key)

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(signer_key_address)
    datum = Registration(
        authority_key_address.payment_part.to_primitive(),
        signer_key_address.payment_part.to_primitive(),
    )
    # Flat attach 2 ADA, next to the minted NFT proving signature rights
    amount = 2000000
    builder.add_minting_script(
        script=contract,
        redeemer=Redeemer(NoRedeemer()),
    )
    builder.mint = MultiAsset.from_primitive({bytes(contract_hash): {TOKENNAME: 1}})
    builder.add_output(
        TransactionOutput(
            address=contract_address,
            amount=Value(coin=amount, multi_asset=builder.mint),
            datum=datum,
        )
    )

    # Sign the transaction
    payment_vkey, payment_skey, payment_address = get_signing_info(signer_key)
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx.to_cbor())

    print(f"transaction id: {signed_tx.id}")
    print(f"Cardanoscan: https://preview.cardanoscan.io/transaction/{signed_tx.id}")


if __name__ == "__main__":
    main()
