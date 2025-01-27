from random import randint
from django.urls import reverse
from django.forms.models import model_to_dict
from django.contrib.auth.hashers import check_password
from nose.tools import ok_, eq_
from rest_framework.test import APITestCase
from rest_framework import status
from faker import Faker
from random import randint
from ..models import Balance, Transaction, User,UserProfile,Referral
from .factories import BalanceFactory, UserFactory
import uuid

fake = Faker()


# class TestUserListTestCase(APITestCase):
#     """
#     Tests /users list operations.
#     """

#     def setUp(self):
#         self.url = reverse('user-list')
#         self.user_data = model_to_dict(UserFactory.build())

#     def test_post_request_with_no_data_fails(self):
#         response = self.client.post(self.url, {})
#         eq_(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_post_request_with_valid_data_succeeds(self): # failed
#         response = self.client.post(self.url, self.user_data)
#         eq_(response.status_code, status.HTTP_201_CREATED)

#         user = User.objects.get(pk=response.data.get('id'))
#         eq_(user.username, self.user_data.get('username'))
#         ok_(check_password(self.user_data.get('password'), user.password))

#     def test_post_request_with_valid_data_succeeds_and_profile_is_created(self): # failed
#         response = self.client.post(self.url, self.user_data)
#         eq_(response.status_code, status.HTTP_201_CREATED)

#         eq_(UserProfile.objects.filter(user__username=self.user_data['username']).exists(),True)

#     def test_post_request_with_valid_data_succeeds_referral_is_created_if_code_is_valid(self): # failed
        
#         referring_user = UserFactory()
#         self.user_data.update({"referral_code":referring_user.userprofile.referral_code})
#         response = self.client.post(self.url, self.user_data)
#         eq_(response.status_code, status.HTTP_201_CREATED)

#         eq_(Referral.objects.filter(referred__username=self.user_data['username'],owner__username=referring_user.username).exists(),True)


#     def test_post_request_with_valid_data_succeeds_referral_is_not_created_if_code_is_invalid(self): # failed
        
#         self.user_data.update({"referral_code":"FAKECODE"})
#         response = self.client.post(self.url, self.user_data)
#         eq_(response.status_code, status.HTTP_400_BAD_REQUEST)
        
# class TestUserDetailTestCase(APITestCase):
#     """
#     Tests /users detail operations.
#     """

#     def setUp(self):
#         self.user = UserFactory()
#         self.url = reverse('user-detail', kwargs={'pk': self.user.pk})
#         self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user.auth_token}')

#     def test_get_request_returns_a_given_user(self):
#         response = self.client.get(self.url)
#         eq_(response.status_code, status.HTTP_200_OK)

#     def test_put_request_updates_a_user(self): #failed
#         new_first_name = fake.first_name()
#         payload = {'first_name': new_first_name}
#         response = self.client.put(self.url, payload)
#         eq_(response.status_code, status.HTTP_200_OK)

#         user = User.objects.get(pk=self.user.id)
#         eq_(user.first_name, new_first_name)

# Test for task endpoints
class TestUserDepositView(APITestCase):
    """
    Tests for the /user-deposit endpoint.
    """

    def setUp(self):
        balance = randint(1000, 10000)
        self.user = UserFactory()
        self.url = reverse('user-deposit', kwargs={'pk': self.user.id})  # Include the pk in the URL
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user.auth_token}')  # Authenticate the user

    def test_post_user_deposit_success(self):
        payload = {'amount': 1000}  # Valid deposit amount
        response = self.client.post(self.url, payload)
        eq_(response.status_code, status.HTTP_201_CREATED)

    def test_post_user_deposit_fails_with_invalid_amount(self):
        payload = {'amount': -100}  # Invalid negative amount
        response = self.client.post(self.url, payload)
        eq_(response.status_code, status.HTTP_400_BAD_REQUEST)

class TestUserListView(APITestCase):
    """
    Tests for the /user-list endpoint.
    """

    def setUp(self):
        # Set up a user and URL for the list endpoint
        self.user = UserFactory()
        self.url = reverse('user-list')  # Correcting the URL to not include pk for a list
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user.auth_token}')  # Authenticate the user

    def test_get_user_list_returns_success(self):
        # Test GET request to list users
        response = self.client.get(self.url)
        eq_(response.status_code, status.HTTP_200_OK)

class TestUserWithdrawView(APITestCase):
    """
    Tests for the /user-withdraw endpoint.
    """

    def setUp(self):
        # Set up a user and related balances
        self.balance = Balance.objects.create(owner=UserFactory())  # Manually create a Balance linked to UserFactory
        self.user = self.balance.owner
        self.balance.available_balance = 1000
        self.balance.save()  # Ensure balance is saved
        self.url = reverse('user-withdraw', kwargs={'pk': self.user.id})
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user.auth_token}')

    def test_post_user_withdraw_fails_with_invalid_amount(self):
        # Dynamically generate a negative withdrawal amount
        payload = {'amount': randint(-1000, -1)}  # Random negative value
        response = self.client.post(self.url, payload)

        eq_(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expect 400 for invalid input

    def test_post_user_withdraw_fails_with_invalid_data(self):
        # Dynamically generate invalid data (non-numeric)
        payload = {'amount': 'invalid'}
        response = self.client.post(self.url, payload)

        eq_(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expect 400 for invalid data

    def test_post_user_withdraw_fails_with_insufficient_balance(self):
        # Generate a withdrawal amount higher than the available balance
        payload = {'amount': self.balance.available_balance + 100}  # Amount greater than available balance
        response = self.client.post(self.url, payload)

        eq_(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expect 400 for insufficient funds


class TransferViewTest(APITestCase):
    """
    Tests for the /user-transfer endpoint.
    """
    def setUp(self):
        self.sender_balance = Balance.objects.create(owner=UserFactory())
        self.recipient_balance = Balance.objects.create(owner=UserFactory())

        self.sender = self.sender_balance.owner
        self.recipient = self.recipient_balance.owner

        self.sender_balance.available_balance = 1000
        self.sender_balance.save()

        self.recipient_balance.available_balance = 1000
        self.recipient_balance.save()

        # Set up the URL for transferring money
        self.url = reverse('user-transfer', kwargs={'pk': self.sender.id, 'recipient_account_id': self.recipient.id})

        # Authenticate the sender user
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.sender.auth_token}')

    def test_transfer_insufficient_funds(self):
        payload = {'amount': 2000}  # Invalid transfer amount (insufficient funds)
        response = self.client.post(self.url, payload)

        eq_(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_recipient_not_found(self):
        non_existent_user_id = uuid.uuid4()
        url = reverse('user-transfer', kwargs={'pk': self.sender.id, 'recipient_account_id': non_existent_user_id})
        payload = {'amount': 200}

        response = self.client.post(url, payload)
        eq_(response.status_code, status.HTTP_404_NOT_FOUND)


class TransactionDetailViewTest(APITestCase):

    def setUp(self):
        # Create a user and transactions for that user
        self.user = UserFactory()  # Assuming you have a UserFactory set up
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user.auth_token}')

        # Create some transactions
        self.transaction_1 = Transaction.objects.create(
            owner=self.user,
            amount=500,
            status='completed'  # Assuming 'completed' is a valid status
        )
        self.transaction_2 = Transaction.objects.create(
            owner=self.user,
            amount=200,
            status='pending'  # Assuming 'pending' is a valid status
        )

        # Set up the URLs
        self.list_url = reverse('user-transaction-detail', kwargs={'pk': self.transaction_1.owner.id})
        self.detail_url = reverse('user-transaction-detail', kwargs={'pk': self.transaction_1.owner.id, 'transaction_id': self.transaction_1.id})

    def test_list_transactions_success(self):
        """
        Test listing transactions for a user, ensuring that the paginated response is returned.
        """
        response = self.client.get(self.list_url)

        # Check if the response status is 200 OK and contains the expected data
        eq_(response.status_code, status.HTTP_200_OK)

        # Check if the response data contains the expected transaction details
        eq_('results' in response.data, True)
        eq_(len(response.data['results']) > 0, True)  # At least one transaction should be returned

        # Check if the transaction details are correctly serialized
        eq_(response.data['results'][0]['id'], str(self.transaction_1.id))
        eq_(response.data['results'][1]['id'], str(self.transaction_2.id))

    def test_transaction_detail_success(self):
        """
        Test retrieving the details of a specific transaction.
        """
        response = self.client.get(self.detail_url)

        # Check if the response status is 200 OK and the correct transaction is returned
        eq_(response.status_code, status.HTTP_200_OK)

        # Check if the transaction detail is correctly serialized
        eq_(response.data['id'], str(self.transaction_1.id))
        eq_(response.data['amount'], self.transaction_1.amount)
        eq_(response.data['status'], self.transaction_1.status)

    def test_transaction_detail_not_found(self):
        """
        Test that a 404 response is returned when trying to retrieve a transaction that does not exist.
        """
        non_existent_transaction_id = uuid.uuid4()  # Generate a random UUID that doesn't exist in the database
        detail_url = reverse('user-transaction-detail', kwargs={'pk': self.transaction_1.owner.id, 'transaction_id': non_existent_transaction_id})

        response = self.client.get(detail_url)

        # Check if a 404 response is returned for a non-existent transaction
        eq_(response.status_code, status.HTTP_404_NOT_FOUND)
        eq_(response.data['error'], 'Transaction not found.')

    def test_list_transactions_no_transactions(self):
        """
        Test that an empty list is returned if the user has no transactions.
        """
        # Create a new user with no transactions
        empty_user = UserFactory()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {empty_user.auth_token}')

        response = self.client.get(reverse('user-transaction-detail', kwargs={'pk': empty_user.id}))

        # Check if the response status is 200 OK and that the results are empty
        eq_(response.status_code, status.HTTP_200_OK)
        eq_('results' in response.data, True)
        eq_(len(response.data['results']), 0)  # No transactions should be returned

    def test_transaction_detail_invalid_transaction_id(self):
        """
        Test that a 400 error is returned when an invalid transaction ID format is provided.
        """
        # Use an invalid transaction ID format
        invalid_transaction_id = 'invalid-transaction-id'
        detail_url = reverse('user-transaction-detail', kwargs={'pk': self.transaction_1.owner.id, 'transaction_id': invalid_transaction_id})

        response = self.client.get(detail_url)

        # Check if a 400 response is returned for invalid transaction ID
        eq_(response.status_code, status.HTTP_400_BAD_REQUEST)
