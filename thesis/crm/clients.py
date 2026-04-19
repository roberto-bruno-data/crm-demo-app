import requests
import logging

class BaseCRMClient:
    def __init__(self, base_url, auth_token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/json"
        }

    def _get(self, endpoint):
        response = requests.get(
            f"{self.base_url}/{endpoint}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

class SalesforceClient(BaseCRMClient):
    def fetch_accounts(self):
        logging.info("Fetching accounts from Salesforce")
        return self._get("accounts")

class NetsuiteClient(BaseCRMClient):
    def fetch_accounts(self):
        logging.info("Fetching accounts from Netsuite")
        return self._get("accounts")
    
# sf = SalesforceClient(
#     base_url=config["salesforce"]["base_url"],
#     auth_token=config["salesforce"]["token"]
# )

# ns = NetsuiteClient(
#     base_url=config["netsuite"]["base_url"],
#     auth_token=config["netsuite"]["token"]
# )

# def make_client(client_cls, cfg):
#     return client_cls(
#         base_url=cfg["base_url"],
#         auth_token=cfg["token"]
#     )

# sf = make_client(SalesforceClient, config["salesforce"])
# ns = make_client(NetsuiteClient, config["netsuite"])

# sf_url, sf_token = get_crm_config(config, "salesforce")
# ns_url, ns_token = get_crm_config(config, "netsuite")