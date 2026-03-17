

# first-time bootstrap


The real first-time path, step by step, is this.

Step 1: authenticate once without KSeF token. In practice, that means the XAdES branch: `POST /auth/challenge`, build and sign `AuthTokenRequest` XML, `POST /auth/xades-signature`, then check `GET /auth/{referenceNumber}` with the returned `authenticationToken`, and finally call `POST /auth/token/redeem` to obtain `accessToken` and `refreshToken`. The spec states that `/auth/{referenceNumber}` and `/auth/token/redeem` use the temporary `AuthenticationToken` returned when authentication was started, and that redeem returns the real `accessToken` and `refreshToken`.

Step 2: once you have a normal authenticated session, call `POST /tokens`. This endpoint is Bearer-protected, so it can only be called after you already have an access token. The spec says this endpoint “zwraca token, który może być użyty do uwierzytelniania się w KSeF,” that the token is returned only once, and that it becomes usable only when its status changes to `Active`. It also says token generation is allowed only in NIP or internal identifier context, and you cannot assign permissions you do not already have.

A typical `POST /tokens` request looks like this:

```json
{
  "permissions": ["InvoiceRead", "InvoiceWrite"],
  "description": "Wystawianie i przeglądanie faktur."
}
```

and the API returns something like:

```json
{
  "referenceNumber": "20251010-EC-1DCE3E3000-12ECB5B36E-45",
  "token": "20251010-EC-1DCE3E3000-12ECB5B36E-45|internalId-5265877635-12345|..."
}
```

The important detail is that this token value is shown only once. If you do not store it at creation time, you will not be able to reconstruct it later from the status endpoint.

Step 3: poll or check token status. The spec exposes `GET /tokens/{referenceNumber}` and token listing under `GET /tokens`. The token is not immediately guaranteed usable; it starts being usable only when its status becomes `Active`. The status example shown in the spec includes states like `Pending`, so your code should not assume instant readiness.

That gives you the bootstrap path:

```text
no token yet
  |
  +--> XAdES login
         |
         +--> POST /auth/challenge
         +--> POST /auth/xades-signature
         +--> GET  /auth/{referenceNumber}
         +--> POST /auth/token/redeem
         |
         +--> accessToken
                |
                +--> POST /tokens
                +--> GET /tokens/{referenceNumber} until Active
                +--> save KSeF token securely
```

After that, your normal reusable KSeF-token login becomes:

Step 4: fetch a fresh challenge with `POST /auth/challenge`. You already did this part. The response includes `challenge`, `timestamp`, and `timestampMs`.

Step 5: obtain the MF public key certificate from `GET /security/public-key-certificates`. The spec says this endpoint returns public keys used to encrypt data sent to KSeF; the example shows usages including `KsefTokenEncryption`, which is the one relevant here.

Step 6: build the plaintext exactly as:

```text
<your_ksef_token>|<timestampMs>
```

For your example challenge, the plaintext would be conceptually:

```text
YOUR_PREVIOUSLY_GENERATED_KSEF_TOKEN|1773687072470
```

Then encrypt that plaintext with RSA-OAEP using SHA-256 and the MF public key for `KsefTokenEncryption`.

Step 7: send `POST /auth/ksef-token` with JSON like this:

```json
{
  "challenge": "20260316-CR-40BA6D6000-05D3D602B8-7E",
  "contextIdentifier": {
    "type": "Nip",
    "value": "YOUR_NIP"
  },
  "encryptedToken": "BASE64_OR_EXPECTED_ENCRYPTED_VALUE"
}
```

The endpoint then returns `202 Accepted` with a `referenceNumber` and an `authenticationToken`.

Step 8: poll `GET /auth/{referenceNumber}` using Bearer authentication with that temporary `authenticationToken`. This is not yet your final access token; it is the operation token for the authentication process itself.

Step 9: when authentication status is successful, call `POST /auth/token/redeem`, again with Bearer authentication using the same temporary `authenticationToken`. That returns the real `accessToken` and `refreshToken` for normal API use. The spec also states that redeem can only be done once.

So the complete steady-state token login is:

```text
have KSeF token
  |
  +--> POST /auth/challenge
  +--> GET /security/public-key-certificates
  +--> encrypt "token|timestampMs"
  +--> POST /auth/ksef-token
  +--> GET /auth/{referenceNumber}
  +--> POST /auth/token/redeem
  +--> accessToken / refreshToken
```

For your specific question, the direct answer is:

```text
You are here now:
POST /auth/challenge  -> OK

Next step?
Not /auth/ksef-token, because you do not yet have a KSeF token.

Correct next step:
bootstrap once via XAdES
-> get accessToken
-> POST /tokens
-> wait for token Active
-> then future logins can use /auth/ksef-token
```

So the current challenge you showed is not enough to proceed today unless you already have a stored KSeF token from an earlier generation. If not, discard this attempt and do a one-time bootstrap via XAdES, then generate the reusable KSeF token.

The implementation consequence for your FastAPI app is straightforward: make XAdES a bootstrap/admin flow and KSeF token the daily runtime flow.
