import os
from pathlib import Path

from pycardano import (
    PaymentVerificationKey,
    PaymentSigningKey,
    Address,
    Network,
    PlutusV2Script,
)

ogmios_host = os.getenv("OGMIOS_API_HOST", "ws://localhost")
ogmios_port = os.getenv("OGMIOS_API_PORT", "1337")
ogmios_url = f"{ogmios_host}:{ogmios_port}"

network = Network.TESTNET

keys_dir = Path(__file__).parent.parent.joinpath("keys")
contract_dir = Path(__file__).parent.parent.joinpath("build")


def get_address(name) -> Address:
    with open(keys_dir.joinpath(f"{name}.addr")) as f:
        address = Address.from_primitive(f.read())
    return address


def get_contract(name) -> PlutusV2Script:
    with open(contract_dir.joinpath(name).joinpath("script.cbor")) as f:
        contract = PlutusV2Script(bytes.fromhex(f.read()))
    return contract


def get_signing_info(name):
    skey_path = str(keys_dir.joinpath(f"{name}.skey"))
    payment_skey = PaymentSigningKey.load(skey_path)
    payment_vkey = PaymentVerificationKey.from_signing_key(payment_skey)
    payment_address = Address(payment_vkey.hash(), network=network)
    return payment_vkey, payment_skey, payment_address
