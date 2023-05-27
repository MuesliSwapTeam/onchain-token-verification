import logging

from flask import Flask, request, abort, send_from_directory, send_file, jsonify, Response  # type: ignore
from flask_cors import CORS  # type: ignore
from flask_caching import Cache  # type: ignore

from .util import CONTRACTS, DATA_DIR, contract_data_path, contract_name, PURPOSES

# logger setup
_LOGGER = logging.getLogger(__name__)


# default timeout for cached value in seconds

app = Flask(__name__)
app.config.from_mapping({"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 20})
cache = Cache(app)
CORS(app)

CONTRACT_NAMES = {contract_name(contract) for contract in CONTRACTS}

#################################################################################################
#                                            Endpoints                                          #
#################################################################################################


@app.route("/<contract_name>/<purpose>")
def entity_list(contract_name, purpose):
    if contract_name not in CONTRACT_NAMES:
        return (
            f"Unknown contract name {repr(contract_name)}, choose one of {CONTRACT_NAMES}",
            404,
        )
    if purpose not in PURPOSES:
        return f"Unknown request format {repr(purpose)}, choose one of {PURPOSES}", 404
    return send_file(contract_data_path(contract_name, purpose))
