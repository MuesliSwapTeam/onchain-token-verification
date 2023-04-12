# Onchain Token Verification

This repository details a way for independent parties to voice opinions about third party tokens in a standardized way.
In particular, this service is meant to establish a shared standard on how trusted entities (such as well-known DEXs, Foundations, specialized companies) can voice opinions about the trustworthiness of a token, marking the combination of token and metadata as either verified or scam.

This enables users to rely on a short chain of trust.
They can just perform due diligence on an authority and when trusting that entity do not need to further investigate on tokens trusted by that authority.
Authorities are interested in acting truthfully to preserve their trust within the community.

Note that this also allows all token creators to place their metadata in these contracts.
They would sign the authenticity of the token with their own private key.

## Outline

The vouching system consists of two main components, which are smart contracts living on the cardano blockchain.

One smart contract is used to register public keys that are associated to a trusted authority, together with metadata about the the authority.
Authorities need to post their public key on their website or social media.
Users are required to check the correctness of this combinations.

In a second set of smart contract, authorities may place combinations of token policy ids, token names and metadata associated to the token in a single UTxO residing at this contract.
They sign this information with their private key, and smart contracts enforce that combinations may only be placed with the authorities public key attached if the signature matches.
Authorities may further revoke their placed combinations by spending the corresponding UTxO.

This set of smart contracts initially consists of two.
Each contract holds a combination of token policy id, name and metadata.
An UTxO residing at contract 1 implies that the authority that placed the UTxO verifies the token.
An UTxO residing at contract 2 implies that the authority considers this token as a scam or fake token.

This set can also be extended by two contracts with the same functionality
but addressing combinations of policy id and metadata, i.e. for verifying the authenticity of a whole NFT series or all tokens minted by a smart contract.

## Architecture

The smart contracts are designed a simple fashion:
They require a datum like the following:

```Haskell
Datum = {
   subject: (Policy ID, Asset, Pubkeyhash) -- Depending on the use case 
   signer: Pubkeyhash
}
```

Each UTxO has to be accompanied by a factory NFT with a smart contract minting factory.
This token allows only to be minted if it is sent to the smart contract and the key specified in the field `signer` signs the transaction minting the NFT (certifying trustworthiness or scamminess of the token).
The contracts allow spending a datum if the key specified in `signer` signs the transaction (revoking the certificate).
Further the contract enforces that a spend burns the above mentioned factory NFT.

Arbitrary metadata about the token may be attached to the transaction as transaction metadata.
We suggest to attach a key value map in metadata field 7457 that corresponds to the key value mapping defined in [CIP 26](https://cips.cardano.org/cips/cip26/).

## Use cases

As this information is on-chain there are a variety of use cases for verification knowledge.

DEXs may use this information to let users choose trusted entities, then display tokens as verified or scam based on the decisions of these entities.
The same goes for user wallets.

Arbitrage traders may require in their trades the verification UTxO as a reference UTxO.

## Smart Authorities

As this information is handled on-chain we can even introduce smart authorities.
For example "proof of liquidity" - a smart contract signs a verification transaction for a specific token as long as a pool on a DEX with sufficient liquidity is included in the transaction as reference UTxO. It may revoke the certificate again when the pool at the same DEX has fallen below the target liquidity.

## Concrete Examples

The following examples are a rough sketch on how to register with the `cardano-cli`.
More sophisticated and easy to use tools can and will be developed, but this is used as a reference implementation.

The following contracts are used (certificate addr | certificate addr reference tx | factory policy id | factory policy id reference tx):

 - Registration as an authority: `addr001` | ref001 | `000001` | refmint000001
 - Certificate of trust for token: `addr002` | ref001 | `000002` | refmint000002
 - Certificate of mistrust for token: `addr003` | ref003 | `000003` | refmint00003

> Note: These values are not set yet, as this is a first draft of the proposal and subject to change

### Registering as an entity

#### Using PyCardano

We provide some simple scripts to register using a PyCardano script.

```bash
$ pip install -r requirements.txt
$ bash build_contracts.sh
$ python3 -m onchain_token_verification.scripts.create_key_pair owner
$ # make sure to fund the script address in keys/owner.addr before running the next command
$ python3 -m onchain_token_verification.scripts.register_authority_trust owner owner
```

#### Using the Cardano-CLI

First, generate a key pair as an entity.

```bash
cardano-cli address key-gen --verification-key-file payment.vkey --signing-key-file payment.skey
```

Extract the public key hash from this key pair.

```bash
cardano-cli address key-hash --payment-verification-key-file payment.vkey
```

Generate the datum to register. Open the file `registration_datum.txt` and insert the following.

```json
{
   "constructor": 0,
   "fields": [
      {
         "bytes": "1d2dd8c9dd700f975941b79d0bcc92585f83b76539b4e516461c80a8"
      },
      {
         "bytes": "1d2dd8c9dd700f975941b79d0bcc92585f83b76539b4e516461c80a8"
      }
   ]
}
```

Replace `1d2dd8c9dd700f975941b79d0bcc92585f83b76539b4e516461c80a8` with the output of the previous step.


Also create `redeemer.txt` with the following content.

```json
{
   "constructor": 0,
   "fields": [
   ]
}
```

Next, generate the transaction that will place your registration at the registration contract. This will involve minting a factory NFT that certifies that you really own the secret key corresponding to the specified public key.

You may spend arbitrary ADA from an address you own and use it to fund this transaction.
Set the following parameters to a UTxO and address you own
```bash
txhash=33834bf7bbd8e51b926ed210bfbb89d55ed8e18ed016bc1b9a6a7f33ead40d97 # replace with your own
txix=0 # replace with your own
address=addr1qygv3nf035y5y5ds0nd6s7fmxljqyhatdhsmyk8w4lhl2qeyl52kwxsh5wfx3darrc4xwql43ylj2n29dpq3xg46a6ms04gmcx # replace with your own
```

Then build the transaction

```bash
cardano-cli transaction build \
 --mainnet
 --tx-in $txhash#$txix \
 --tx-out addr001+1500000+"1 00001.666163746f7279" \
 --datum-embed-file registration_datum.txt \
 --mint "1 00001.666163746f7279" \
 --mint-tx-in-reference refmint000001 \
 --mint-plutus-script-v2 \
 --mint-reference-tx-in-redeemer-file redeemer.txt \
 --policy-id 00001 \
 --required-signer payment.skey
 --out-file matx.raw
```

> If you want to add your website, add as metadata a key value map at metadata index specified above

Sign this transaction both with `payment.skey` and the key used to fund the transaction.
Then submit it to the blockchain.

```bash
cardano-cli transaction sign --tx-body-file matx.raw --signing-key-file payment.skey --out-file matx.signed
cardano-cli transaction submit --tx-file matx.signed --mainnet
```

### Certifying trust for a token

Use the pubkeyhash that you generated in the previous step for your entity in these steps as well.
Generate the datum to register. Open the file `trust_datum.txt` and insert the following.

```json
{
   "constructor": 0,
   "fields": [
      {
         "constructor": 0,
         "fields": [
            {
              "bytes": "8a1cfae21368b8bebbbed9800fec304e95cce39a2a57dc35e2e3ebaa"
            },
            {
              "bytes": "4d494c4b"
            }
         ]
      },
      {
         "bytes": "1d2dd8c9dd700f975941b79d0bcc92585f83b76539b4e516461c80a8"
      }
   ]
}
```

Replace `1d2dd8c9dd700f975941b79d0bcc92585f83b76539b4e516461c80a8` with the value you inserted in the 
registration datum in the previous step.
This example registers your trust for [the `MILK` token](https://cardanoscan.io/token/8a1cfae21368b8bebbbed9800fec304e95cce39a2a57dc35e2e3ebaa.4d494c4b).
Replace `8a1cfae21368b8bebbbed9800fec304e95cce39a2a57dc35e2e3ebaa` with the policy ID of the token that you want
to verify.
Replace `4d494c4b` with the hex-encoded token name of the token you want to verify (in CardanoScan, it is shown next to the ASCII encoded token name).

Re-use the `redeemer.txt` from the previous step.

Next, generate the transaction that will place your registration at the registration contract. This will involve minting a factory NFT that certifies that you really own the secret key corresponding to the specified public key.

You may spend arbitrary ADA from an address you own and use it to fund this transaction.
Set the following parameters to a UTxO and address you own
```bash
txhash=33834bf7bbd8e51b926ed210bfbb89d55ed8e18ed016bc1b9a6a7f33ead40d97 # replace with your own
txix=0 # replace with your own
address=addr1qygv3nf035y5y5ds0nd6s7fmxljqyhatdhsmyk8w4lhl2qeyl52kwxsh5wfx3darrc4xwql43ylj2n29dpq3xg46a6ms04gmcx # replace with your own
```

Then build the transaction

```bash
cardano-cli transaction build \
 --mainnet
 --tx-in $txhash#$txix \
 --tx-out addr001+1500000+"1 00002.666163746f7279" \
 --datum-embed-file trust_datum.txt \
 --mint "1 00002.666163746f7279" \
 --mint-tx-in-reference refmint000001 \
 --mint-plutus-script-v2 \
 --mint-reference-tx-in-redeemer-file redeemer.txt \
 --policy-id 00002 \
 --required-signer payment.skey
 --out-file matx.raw
```

> If you want to add token metadata, add metadata as specified in [CIP 25](https://cips.cardano.org/cips/cip25/) to your transaction

Sign this transaction both with `payment.skey` and the key used to fund the transaction.
Finally submit and you are done!
```bash
cardano-cli transaction sign --tx-body-file matx.raw --signing-key-file payment.skey --out-file matx.signed
cardano-cli transaction submit --tx-file matx.signed --mainnet
```

## How does this compare to other approaches to storing token metadata?


There have been attempts at collecting the data off-chain in the [cardano-token-registry](https://github.com/cardano-foundation/cardano-token-registry) standardized in [CIP 26](https://cips.cardano.org/cips/cip26/).

Benefits of this approach are:

 - low financial effort at getting registered
 - human-in-the-loop control over registry (although not enacted)

Drawbacks:

 - relies on GitHub and the Cardano Foundation to operate
 - gives no way for a third party to store opinions about tokens
 - ambiguous in case of tokens with smart contract minting policies

There are also [CIP 25](https://cips.cardano.org/cips/cip25/) that standardizes storage of metadata together with token mints

Benefits

 - does not rely on centralized infrastructure

Drawbacks

 - easy to abuse, no human-in-the-loop for controlling
 - gives no way for a third party to store opinions about tokens

Hence neither of these approaches is suitable for a registry that allows independent parties to voice any opinions about tokens owned by third parties, at least not without much effort.

## Building the Contracts

Make sure that you have Python3.8 installed locally.
You can build a contracts using the attached build script

```bash
cd contracts
bash build_contracts.sh
```

You can find more information about the opshin programming language in the [opshin language](https://github.com/OpShin/opshin)
repository.