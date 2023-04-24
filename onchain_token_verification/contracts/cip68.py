from dataclasses import dataclass
from typing import Dict, List, Union
from pycardano import Datum as Anything, PlutusData

FilesDetails = Dict[bytes, Anything]

Metadata = Dict[bytes, Anything]

Extra = Anything


@dataclass
class CIP68Datum(PlutusData):
    metadata: Metadata
    version: int
    extra: Extra
