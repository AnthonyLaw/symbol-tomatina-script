import json
from binascii import hexlify, unhexlify
from collections import namedtuple

from symbolchain.CryptoTypes import Hash256
from symbolchain.nem.Network import Address as NemAddress
from symbolchain.symbol.Network import Network, NetworkTimestamp

from client.BasicClient import BasicClient


class SymbolClient(BasicClient):
	"""Async client for connecting to a NEM node."""

	async def height(self):
		"""Gets current blockchain height."""

		return int(await self.get('chain/info', 'height'))

	async def announce(self, transaction_payload):
		"""Announces serialized transaction."""

		return await self.put('transactions', transaction_payload)

	async def node_time(self):
		"""Gets node time."""

		timestamps = await self.get('node/time', 'communicationTimestamps')
		return NetworkTimestamp(int(timestamps['receiveTimestamp']))

	async def node_network(self):
		"""Gets node network."""

		if not self.network:
			network_identifier = await self.get('node/info', 'networkIdentifier')
			self.network = Network.TESTNET if 152 == network_identifier else Network.MAINNET

		return self.network

	async def transaction_statuses(self, transaction_hashes_payload):
		"""Gets the statuses of the specified transactions."""

		return await self.post('transactionStatus', transaction_hashes_payload)

	async def outgoing_transactions(self, optin_signer_public_key, start_id=None):
		"""Gets outgoing transactions of the specified account."""

		url_path = f'transactions/confirmed?signerPublicKey={optin_signer_public_key}&embedded=true&fromHeight=2&pageSize=100'
		if start_id:
			url_path += f'&offset={start_id}'

		transactions = await self.get(url_path, 'data')
		return transactions

	async def incoming_transfer_transactions(self, recipient_address, from_height=707104, sort='asc', start_id=None):
		"""Gets incoming transactions of the specified account."""

		url_path = f'transactions/confirmed?recipientAddress={recipient_address}&embedded=true&fromHeight={from_height}&pageSize=100&order={sort}&type=16724'
		if start_id:
			url_path += f'&offset={start_id}'

		transactions = await self.get(url_path, 'data')
		return transactions

	async def transaction_confirmed(self, transaction_hash):
		"""Gets a confirmed transaction."""

		url_path = f'transactions/confirmed/{transaction_hash}'
		return await self.get(url_path, None)

	async def transactions_confirmed(self, transaction_hashes_payload):
		"""Gets a confirmed transactions."""

		return await self.post('transactions/confirmed', transaction_hashes_payload)

	async def currency_mosaic_id(self):
		"""Gets the currency mosaic id from the network."""

		if not self._network_properties:
			self._network_properties = await self.get('network/properties', 'chain')

		formatted_currency_mosaic_id = self._network_properties['currencyMosaicId']
		return int(formatted_currency_mosaic_id.replace('\'', ''), 16)
