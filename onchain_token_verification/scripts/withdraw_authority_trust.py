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
    UTxO,
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
    # Find the trust UTxO
    utxo_to_spend = None
    inlined = None
    for utxo in context.utxos(str(contract_address)):
        if (
            utxo.output.datum is not None
            and utxo.output.datum.cbor == datum.to_cbor("bytes")
            and utxo.output.amount.multi_asset.get(contract_hash) is not None
        ):
            utxo_to_spend = utxo
            inlined = True
            break
        elif (
            utxo.output.datum_hash is not None
            and utxo.output.datum_hash == datum.hash()
            and utxo.output.amount.multi_asset.get(contract_hash) is not None
        ):
            utxo_to_spend = utxo
            inlined = False
            break
    assert isinstance(utxo_to_spend, UTxO), "No script UTxOs found!"

    builder.add_script_input(
        utxo_to_spend,
        contract,
        datum=datum if not inlined else None,
        redeemer=Redeemer(NoRedeemer()),
    )
    builder.add_minting_script(
        script=contract,
        redeemer=Redeemer(NoRedeemer()),
    )
    payment_vkey, payment_skey, payment_address = get_signing_info(signer_key)
    builder.required_signers = [payment_vkey.hash()]
    builder.mint = MultiAsset.from_primitive({bytes(contract_hash): {TOKENNAME: -1}})

    # Sign the transaction
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