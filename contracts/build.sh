#! /bin/bash

set -e

python3.8 -m venv venv
pip install -r requirements.txt

opshin build src/register_authority_trust.py --force-three-params
opshin build src/register_token_trust.py --force-three-params
opshin build src/register_token_mistrust.py --force-three-params
