import requests, base64, uuid, urllib3
urllib3.disable_warnings()

creds = base64.b64encode(b'0a9b322c-a97e-490e-9ce1-5739c27c7eda:ca251a701ae441cdbd0eace87e59ddf3').decode()

# Get token
token = requests.post(
    'https://sandbox.momodeveloper.mtn.com/collection/token/',
    headers={
        'Ocp-Apim-Subscription-Key': '78b0319a9521448c9bd5890a38e62458',
        'Authorization': f'Basic {creds}',
    }, verify=False
).json()['access_token']
print('Token OK')

# Send payment
ref_id = str(uuid.uuid4())
res = requests.post(
    'https://sandbox.momodeveloper.mtn.com/collection/v1_0/requesttopay',
    headers={
        'Authorization': f'Bearer {token}',
        'Ocp-Apim-Subscription-Key': '78b0319a9521448c9bd5890a38e62458',
        'X-Reference-Id': ref_id,
        'X-Target-Environment': 'sandbox',
        'Content-Type': 'application/json',
    },
    json={
        'amount': '200',
        'currency': 'EUR',
        'externalId': 'order001',
        'payer': {'partyIdType': 'MSISDN', 'partyId': '46733123451'},
        'payerMessage': 'Schoolcamp',
        'payeeNote': 'Schoolcamp'
    }, verify=False
)
print('Status:', res.status_code)

# ✅ Safe response handling
try:
    print('Response:', res.json())
except Exception:
    print('Response: (empty body)')

# Check payment status
status_res = requests.get(
    f'https://sandbox.momodeveloper.mtn.com/collection/v1_0/requesttopay/{ref_id}',
    headers={
        'Authorization': f'Bearer {token}',
        'Ocp-Apim-Subscription-Key': '78b0319a9521448c9bd5890a38e62458',
        'X-Target-Environment': 'sandbox',
    }, verify=False
)
try:
    print('Payment Status:', status_res.json())
except Exception:
    print('Status Response: (empty body)')