import argparse
import asyncio
import json

from client.SymbolClient import SymbolClient
from symbolchain.CryptoTypes import PrivateKey
from symbolchain.facade.SymbolFacade import SymbolFacade

from order.OrderManager import OrderManager, OrderStatus
from TomatoProcess import TomatoProcess


async def main():
	parser = argparse.ArgumentParser(description='process tomation nft order')
	parser.add_argument('--symbol-node', help='Symbol node url', default='http://wolf.importance.jp:3000')
	parser.add_argument('--network', help='NEM and Symbol network', choices=['testnet', 'mainnet'], default='mainnet')
	parser.add_argument('--order-address', help='address receive order transaction')
	parser.add_argument('--private-key', help='private key of the account to use for NFT creation')
	parser.add_argument('--order-file', help='path to save order file', default='data/order.json')
	parser.add_argument('--dry-run', help='print transactions without sending', action='store_true')

	args = parser.parse_args()

	client = SymbolClient(args.symbol_node)
	facade = SymbolFacade(args.network)

	private_key = PrivateKey(args.private_key)
	key_pair = facade.KeyPair(private_key)

	native_mosaic_id = await client.currency_mosaic_id()

	print('processing settlement')

	order_manager = OrderManager(args.order_file)

	pending = order_manager.get_pending_settlement_orders()

	if len(pending) == 0:
		print('No pending settlement')
		return

	print(f'found {len(pending)} pending settlement')

	confirmed_orders = []

	for order in pending:
		order_id = order['order_id']
		image_container_hash = order['image_container_hash']

		payload = {"hashes": [image_container_hash]}

		client_response = await client.transaction_statuses(payload)

		if 0 == len(client_response):
			continue

		all_confirmed = all(status['group'] == 'confirmed' for status in client_response)

		if all_confirmed:
			confirmed_orders.append(order_id)

	if len(confirmed_orders) == 0:
		print('settlement have not confirm yet')
		return
	else:
		print(f'found {len(confirmed_orders)} settlement confirmed')

	tomato_process = TomatoProcess(client, args.network, key_pair)

	network_time = await client.node_time()
	network_time = network_time.add_hours(2)

	for order_id in confirmed_orders:
		order_info = order_manager.get_order(order_id)
		paid_amount = order_info['paid']
		nft_mosaic_id = int(order_info['mosaic_id'] , 16)  # convert hex to bytes
		mosaic_hash = order_info['mosaic_hash']
		image_hash = order_info['image_hash']
		image_container_hash = order_info['image_container_hash']
		buyer_address = order_info['buyer_address']

		mosaic_metadata = {
			"rootTransactionHash": image_container_hash,
			"name":f'Tomatina NFT #{order_id}',
		}

		# total transaction fee = mosaic creation fee + mosaic_hash tx fee + image_hash tx fee
		total_fee = await tomato_process.get_total_transaction_fees([mosaic_hash, image_container_hash] + image_hash)

		# mosaic creation fee
		mosaic_creation_fee = 50000000

		# fee for metadata info, and return remain balance
		settlement_fee = 52800

		remain_balance = paid_amount - (total_fee + mosaic_creation_fee + settlement_fee)

		# NFT mosaic + remain balance
		mosaics = [
			{
				'mosaic_id': nft_mosaic_id,
				'amount': 1
			},
			{
				'mosaic_id': native_mosaic_id,
				'amount': remain_balance
			}
		]

		transaction_hash = await tomato_process.process_settlement(
			network_time,
			nft_mosaic_id,
			json.dumps(mosaic_metadata),
			mosaics,
			buyer_address,
			args.dry_run)

		order_manager.update_order(order_id, {
			'settlement_hash': transaction_hash,
			"order_status": OrderStatus.COMPLETED
		})

if '__main__' == __name__:
	asyncio.run(main())
