"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"

HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_read_an_account(self):
        """It should read a single account"""
        account = self._create_accounts(1)[0]
        resp = self.client.get(
            f"{BASE_URL}/{account.id}", content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], account.name)

    def test_get_account_not_found(self):
        """It should not read an account that isn't found"""
        resp = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_an_account(self):
        """It should update an existing account"""
        account = self._create_accounts(1)[0]

        updated_data = {
            "name": "New Name",
            "address": "New Address",
            "email": "new@email.com",
            "date_joined": "2024-01-01",
            "phone_number": "0123456778"
        }

        resp = self.client.put(
            f"{BASE_URL}/{account.id}",
            json=updated_data,
            content_type="application/json"
        )

        # Check that the response status code indicates success
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Optionally, verify that the account has been updated correctly
        updated_account = Account.find(account.id)
        self.assertEqual(updated_account.name, updated_data["name"])
        self.assertEqual(updated_account.email, updated_data["email"])
        self.assertEqual(updated_account.address, updated_data["address"])

    def test_update_account_not_found(self):
        """It should not update a non-existing account"""
        updated_data = {
            "name": "New Name",
            "address": "New Address",
            "email": "new@email.com",
            "date_joined": "2024-01-01",
            "phone_number": "0123456778"
        }

        resp = self.client.put(
            f"{BASE_URL}/0",
            json=updated_data,
            content_type="application/json"
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account(self):
        """It should delete an account"""
        # Arrange: Create an account
        account = self._create_accounts(1)[0]
        account_id = account.id

        # Act: Send a DELETE request to delete the account
        response = self.client.delete(
            f"{BASE_URL}/{account_id}",
            content_type="application/json"
        )

        # Assert: Check that the response status code indicates success
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify: Check that the account is actually deleted
        deleted_account = Account.query.get(account_id)
        self.assertIsNone(deleted_account)

    def test_list_accounts(self):
        """It should list all accounts"""
        # Arrange: Create some accounts using the factory method
        num_accounts = 5
        accounts = self._create_accounts(num_accounts)

        # Act: Send a GET request to list all accounts
        response = self.client.get(BASE_URL)

        # Assert: Check that the response status code indicates success
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify: Check that the response contains all created accounts
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), num_accounts)

        # Verify that each account in the response matches the created accounts
        for i, account_data in enumerate(data):
            self.assertEqual(account_data["id"], accounts[i].id)
            self.assertEqual(account_data["name"], accounts[i].name)
            self.assertEqual(account_data["email"], accounts[i].email)
            self.assertEqual(account_data["address"], accounts[i].address)
            self.assertEqual(account_data["phone_number"], accounts[i].phone_number)
            self.assertEqual(account_data["date_joined"], str(accounts[i].date_joined))

    def test_list_accounts_empty(self):
        """It should return an empty list"""
        response = self.client.get(BASE_URL)

        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([], data)

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)

    def test_cors_security(self):
        """It should return a CORS header"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check for the CORS header
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), '*')
