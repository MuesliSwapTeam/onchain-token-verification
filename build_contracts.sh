#! /bin/bash

set -e

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

opshin build onchain_token_verification/contracts/register_authority_trust.py --force-three-params
opshin build onchain_token_verification/contracts/register_token_trust.py --force-three-params
opshin build onchain_token_verification/contracts/register_token_mistrust.py --force-three-params
