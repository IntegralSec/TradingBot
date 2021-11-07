import requests

base_uri = "https://testnet.bitmex.com/api/v1"

def get_contracts():
    request_uri = base_uri + "/instrument/active"
    response_object = requests.get(request_uri)
    print(response_object.status_code)
    contracts = []
    for instrument in response_object.json():
        contracts.append(instrument['symbol'])
    return contracts



