#! /bin/bash

set -e

# Build vouching contracts
opshin build any onchain_token_verification/contracts/authority_trust.py --force-three-params
opshin build any onchain_token_verification/contracts/token_trust.py --force-three-params
opshin build any onchain_token_verification/contracts/token_mistrust.py --force-three-params

# Build smart voucher
opshin build mint onchain_token_verification/smart_voucher/muesliswap_pool_verifier.py $(python3 -m onchain_token_verification.contract_address token_trust)
