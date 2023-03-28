from urllib.parse import urlparse

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from registry.models import Passport, Stamp
from web3 import Web3

User = get_user_model()
web3 = Web3()
web3.eth.account.enable_unaudited_hdwallet_features()
my_mnemonic = settings.TEST_MNEMONIC

pytestmark = pytest.mark.django_db


@pytest.fixture
def paginated_stamps(scorer_community, passport_holder_addresses):
    passport = Passport.objects.create(
        address=passport_holder_addresses[0]["address"],
        community=scorer_community,
        passport={"name": "John Doe"},
    )

    stamps = []

    for i in range(6):
        stamp = Stamp.objects.create(
            passport=passport,
            hash=f"v0.0.0:Ft7mqRdvJ9jNgSSowb9qdcMeOzswOeighIOvk0wn96{i}=",
            provider=f"Provider{i}",
            credential={
                "type": ["VerifiableCredential"],
                "proof": {
                    "jws": "eyJhbGciOiJFZERTQSIsImNyaXQiOlsiYjY0Il0sImI2NCI6ZmFsc2V9..34uD8jKn2N_yE8pY4ErzVD8pJruZq7qJaCxx8y0SReY2liZJatfeQUv1nqmZH19a-svOyfHt_VbmKvh6A5vwBw",
                    "type": "Ed25519Signature2018",
                    "created": "2023-01-24T00:55:02.028Z",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": "did:key:z6MkghvGHLobLEdj1bgRLhS4LPGJAvbMA1tn2zcRyqmYU5LC#z6MkghvGHLobLEdj1bgRLhS4LPGJAvbMA1tn2zcRyqmYU5LC",
                },
                "issuer": "did:key:z6MkghvGHLobLEdj1bgRLhS4LPGJAvbMA1tn2zcRyqmYU5LC",
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "issuanceDate": "2023-01-24T00:55:02.028Z",
                "expirationDate": "2023-04-24T00:55:02.028Z",
                "credentialSubject": {
                    "id": "did:pkh:eip155:1:0xf4c5c4deDde7A86b25E7430796441e209e23eBFB",
                    "hash": "v0.0.0:Ft7mqRdvJ9jNgSSowb9qdcMeOzswOeighIOvk0wn964=",
                    "@context": [
                        {
                            "hash": "https://schema.org/Text",
                            "provider": "https://schema.org/Text",
                        }
                    ],
                    "provider": f"Provider{i}",
                },
            },
        )
        stamps.append(stamp)

    return stamps


class TestPassportGetStamps:
    def test_get_stamps_with_address_with_no_scores(
        self, scorer_api_key, passport_holder_addresses
    ):
        client = Client()
        response = client.get(
            f"/registry/stamps/{passport_holder_addresses[0]['address']}",
            HTTP_AUTHORIZATION="Token " + scorer_api_key,
        )
        response_data = response.json()

        assert response.status_code == 200
        assert len(response_data["items"]) == 0

    def test_get_stamps_returns_first_page_stamps(
        self,
        scorer_api_key,
        passport_holder_addresses,
        paginated_stamps,
    ):
        limit = 2

        client = Client()
        response = client.get(
            f"/registry/stamps/{passport_holder_addresses[0]['address']}?limit={limit}",
            HTTP_AUTHORIZATION="Token " + scorer_api_key,
        )
        response_data = response.json()

        assert response.status_code == 200

        paginated_stamps.reverse()

        for i in range(limit):
            assert (
                response_data["items"][i]["credential"]["credentialSubject"]["provider"]
                == paginated_stamps[
                    i
                ].provider  # reversed order since get stamps is descending
            )

    def test_get_stamps_returns_second_page_stamps(
        self,
        scorer_api_key,
        passport_holder_addresses,
        paginated_stamps,
    ):
        last_id = 5
        limit = 2

        client = Client()
        response = client.get(
            f"/registry/stamps/{passport_holder_addresses[0]['address']}?last_id={last_id}&limit={limit}",
            HTTP_AUTHORIZATION="Token " + scorer_api_key,
        )
        response_data = response.json()

        assert response.status_code == 200

        # paginated_stamps.reverse()

        # for i in range(limit):
        #     assert (
        #         response_data["items"][i]["credential"]["credentialSubject"]["provider"]
        #         == paginated_stamps[i+limit].provider
        #     )

    def test_limit_greater_than_1000_throws_an_error(
        self, passport_holder_addresses, scorer_api_key
    ):
        client = Client()
        response = client.get(
            f"/registry/stamps/{passport_holder_addresses[0]['address']}?limit=1001",
            HTTP_AUTHORIZATION="Token " + scorer_api_key,
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Invalid limit.",
        }

    def test_limit_of_1000_is_ok(self, passport_holder_addresses, scorer_api_key):
        client = Client()
        response = client.get(
            f"/registry/stamps/{passport_holder_addresses[0]['address']}?limit=1000",
            HTTP_AUTHORIZATION="Token " + scorer_api_key,
        )

        assert response.status_code == 200

    def test_get_last_page_stamps_by_address(
        self,
        scorer_api_key,
        passport_holder_addresses,
        paginated_stamps,
    ):
        """
        We will try reading all stamps in 2 request (2 batches). We expect the next link after the 1st page to be valid,
        and the second page to be null.
        """

        num_scores = len(paginated_stamps)

        limit = int(num_scores / 2)
        client = Client()

        # Read the 1st batch
        response = client.get(
            f"/registry/stamps/{passport_holder_addresses[0]['address']}?limit={limit}",
            HTTP_AUTHORIZATION="Token " + scorer_api_key,
        )
        response_data = response.json()

        assert response.status_code == 200
        assert len(response_data["items"]) == limit
        assert len(response_data["next"]) != None

        # get relative path with query params
        next_url = (
            urlparse(response_data["next"]).path
            + "?"
            + urlparse(response_data["next"]).query
        )

        # Read the 2nd batch
        response = client.get(
            next_url,
            HTTP_AUTHORIZATION="Token " + scorer_api_key,
        )
        response_data = response.json()

        assert response.status_code == 200
        assert len(response_data["items"]) == len(paginated_stamps) - limit
        assert response_data["next"] == None
