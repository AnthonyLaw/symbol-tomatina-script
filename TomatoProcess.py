from symbolchain.CryptoTypes import PublicKey
from symbolchain.facade.SymbolFacade import SymbolFacade
from symbolchain.symbol.IdGenerator import generate_mosaic_id
from symbolchain.sc import Amount

import json
import random

from PIL import Image
import io

class TomatoProcess:
	def __init__(self, client, network, key_pair):
		self.client = client
		self.key_pair = key_pair
		self.network = network

	@staticmethod
	def _image_to_bytes(image_path):
		with Image.open(image_path) as img:
			with io.BytesIO() as output:
				img.save(output, format=img.format)
				return output.getvalue()

	@staticmethod
	def _chunk_data(data, chunk_size=1024):
		return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

	async def create_mosaic(self, deadline, supply, is_dry_run):
		facade = SymbolFacade(self.network)

		signer_address = facade.network.public_key_to_address(self.key_pair.public_key)
		nonce = random.randint(0, 1000000000)
		mosaic_id = generate_mosaic_id(signer_address, nonce)

		mosaic_definition_transaction = facade.transaction_factory.create_embedded({
			'type': 'mosaic_definition_transaction_v1',
			'signer_public_key': self.key_pair.public_key,
			'duration': 0,
			'nonce': nonce,
			'flags': 'transferable',
			'divisibility': 0
		})

		mosaic_supply_change_transaction = facade.transaction_factory.create_embedded({
			'type': 'mosaic_supply_change_transaction_v1',
			'signer_public_key': self.key_pair.public_key,
			'action': 'increase',
			'mosaic_id': mosaic_id,
			'delta': supply
		})

		embedded_transactions = [mosaic_definition_transaction, mosaic_supply_change_transaction]

		aggregate_transaction = facade.transaction_factory.create({
				'type': 'aggregate_complete_transaction_v2',
				'signer_public_key': self.key_pair.public_key,
				'deadline': deadline.timestamp,
				'transactions_hash': facade.hash_embedded_transactions(embedded_transactions),
				'transactions': embedded_transactions
		})

		aggregate_transaction.fee = Amount(100 * aggregate_transaction.size)

		signature = facade.sign_transaction(self.key_pair, aggregate_transaction)

		transaction_hash = facade.hash_transaction(aggregate_transaction)

		json_payload = facade.transaction_factory.attach_signature(aggregate_transaction, signature)

		transaction_hash = facade.hash_transaction(aggregate_transaction)

		print(f'announcing mosaic creation transaction: {transaction_hash}')

		if not is_dry_run:
			await self.client.announce(json.loads(json_payload))

		return str(transaction_hash), hex(mosaic_id)

	async def process_upload_to_chain(self, deadline, image_url, is_dry_run):
		image_bytes = self._image_to_bytes(image_url)
		chunks = self._chunk_data(image_bytes)

		facade = SymbolFacade(self.network)

		nft_storage_address = facade.network.public_key_to_address(PublicKey('295118813BDE3CCA141AD0AF6DE596BA37FB68FAC1E3FAFF4C794A2443EE910D'))

		transfer_txs = []

		for chunk in chunks:
			transfer_transaction = facade.transaction_factory.create_embedded({
				'type': 'transfer_transaction_v1',
				'signer_public_key': self.key_pair.public_key,
				'recipient_address': nft_storage_address,
				'mosaics': [],
				'message': chunk
			})

			transfer_txs.append(transfer_transaction)

		# Split the transactions into chunks of 100 (for inner txs)
		prepare_tx = self._chunk_data(transfer_txs, 100)

		transaction_hashes = []

		for tx in prepare_tx:
			embedded_transactions = tx

			aggregate_transaction = facade.transaction_factory.create({
					'type': 'aggregate_complete_transaction_v2',
					'signer_public_key': self.key_pair.public_key,
					'deadline': deadline.timestamp,
					'transactions_hash': facade.hash_embedded_transactions(embedded_transactions),
					'transactions': embedded_transactions,
			})

			aggregate_transaction.fee = Amount(100 * aggregate_transaction.size)

			signature = facade.sign_transaction(self.key_pair, aggregate_transaction)

			json_payload = facade.transaction_factory.attach_signature(aggregate_transaction, signature)

			transaction_hash = facade.hash_transaction(aggregate_transaction)

			print(f'announcing storage image on chain transaction: {transaction_hash}')
			if not is_dry_run:
				await self.client.announce(json.loads(json_payload))

			transaction_hashes.append(str(transaction_hash))

		return transaction_hashes

	async def process_image_container(self, deadline, garush_meta, image_hashes, is_dry_run):
		facade = SymbolFacade(self.network)

		nft_folder_address = facade.network.public_key_to_address(PublicKey('9135DC8F377740631CB8B2F26235D533F06294751A398F9B45B0CD20920C82CD'))

		transfer_transaction_garush_meta = facade.transaction_factory.create_embedded({
			'type': 'transfer_transaction_v1',
			'signer_public_key': self.key_pair.public_key,
			'recipient_address': nft_folder_address,
			'mosaics': [],
			'message': b'\0' + f"{garush_meta}".encode()
		})

		transfer_transaction_image_container = facade.transaction_factory.create_embedded({
			'type': 'transfer_transaction_v1',
			'signer_public_key': self.key_pair.public_key,
			'recipient_address': nft_folder_address,
			'mosaics': [],
			'message': b'\0' + f"{image_hashes}".encode()
		})

		embedded_transactions = [transfer_transaction_garush_meta, transfer_transaction_image_container]

		aggregate_transaction = facade.transaction_factory.create({
				'type': 'aggregate_complete_transaction_v2',
				'signer_public_key': self.key_pair.public_key,
				'deadline': deadline.timestamp,
				'transactions_hash': facade.hash_embedded_transactions(embedded_transactions),
				'transactions': embedded_transactions,
		})

		aggregate_transaction.fee = Amount(100 * aggregate_transaction.size)

		signature = facade.sign_transaction(self.key_pair, aggregate_transaction)

		json_payload = facade.transaction_factory.attach_signature(aggregate_transaction, signature)

		transaction_hash = facade.hash_transaction(aggregate_transaction)

		print(f'announcing image container on chain transaction: {transaction_hash}')
		if not is_dry_run:
			await self.client.announce(json.loads(json_payload))

		return str(transaction_hash)

	async def process_settlement(self, deadline, nft_mosaic_id, mosaic_metadata, mosaics, buyer_address, is_dry_run):
		facade = SymbolFacade(self.network)

		signer_address = facade.network.public_key_to_address(self.key_pair.public_key)

		# create mosaic metadata
		mosaic_metadata_transaction = facade.transaction_factory.create_embedded({
			'type': 'mosaic_metadata_transaction_v1',
			'signer_public_key': self.key_pair.public_key,
			'target_address': signer_address,
			'target_mosaic_id': nft_mosaic_id,
			'scoped_metadata_key': int.from_bytes(b'tomatina', byteorder='little'),
			'value_size_delta': len(mosaic_metadata),
			'value': mosaic_metadata,
		})

		# create mosaic transfer include NFT and remaining balance
		transfer_transaction_mosaic = facade.transaction_factory.create_embedded({
			'type': 'transfer_transaction_v1',
			'signer_public_key': self.key_pair.public_key,
			'recipient_address': buyer_address,
			'mosaics': mosaics,
			'message': b'\0Thank you for your purchase!'
		})

		embedded_transactions = [mosaic_metadata_transaction, transfer_transaction_mosaic]

		aggregate_transaction = facade.transaction_factory.create({
				'type': 'aggregate_complete_transaction_v2',
				'signer_public_key': self.key_pair.public_key,
				'deadline': deadline.timestamp,
				'transactions_hash': facade.hash_embedded_transactions(embedded_transactions),
				'transactions': embedded_transactions
		})

		aggregate_transaction.fee = Amount(100 * aggregate_transaction.size)

		signature = facade.sign_transaction(self.key_pair, aggregate_transaction)

		transaction_hash = facade.hash_transaction(aggregate_transaction)

		json_payload = facade.transaction_factory.attach_signature(aggregate_transaction, signature)

		transaction_hash = facade.hash_transaction(aggregate_transaction)

		print(f'announcing settlement transaction: {transaction_hash}')

		if not is_dry_run:
			await self.client.announce(json.loads(json_payload))

		return str(transaction_hash)

	async def get_total_transaction_fees(self, transaction_hashes):
		transaction_hashes_payload = {"transactionIds": transaction_hashes}

		response = await self.client.transactions_confirmed(transaction_hashes_payload)

		fees = 0

		for transaction in response:
			fees += int(transaction['transaction']['maxFee'])

		return fees
