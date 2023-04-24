import json

import opshin.util
import uplc.ast
from pycardano import RawCBOR, Datum, PlutusData

from .contracts.cip68 import CIP68Datum, Extra, Metadata


def json_to_extra(d: dict) -> Extra:
    return RawCBOR(opshin.util.data_from_json(d).to_cbor())


def json_to_metadata(d: dict) -> Metadata:
    return PlutusData.from_json(
        Metadata, {"map": [{"k": k.hex(), "v": v} for k, v in d.items()]}
    )


def json_to_cip68(d: dict) -> CIP68Datum:
    return CIP68Datum(
        json_to_metadata(d["metadata"]),
        d["version"],
        json_to_extra(d["extra"]),
    )


def extra_to_json(d: Datum) -> dict:
    return PlutusData.to_primitive(d)


def metadata_to_json(d: Metadata) -> dict:
    d_dict = json.loads(PlutusData.to_json(d))
    return {bytes.fromhex(kv["k"]["bytes"]).decode("utf8"): kv["v"] for kv in d_dict["map"]}


def cip68_to_json(d: CIP68Datum) -> dict:
    return {
        "metadata": metadata_to_json(d.metadata),
        "version": d.version,
        "extra": uplc.ast.data_from_cbortag(d.extra.data).to_json(),
    }
