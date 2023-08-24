import argparse
import asyncio
import yaml

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
	parser.add_argument('--dry-run', help='print transactions without sending', action='store_true')

	args = parser.parse_args()

	client = SymbolClient(args.symbol_node)
	facade = SymbolFacade(args.network)

	private_key = PrivateKey(args.private_key)
	key_pair = facade.KeyPair(private_key)

	print('processing image container')

	order_manager = OrderManager('data/order.json')

	pending = order_manager.get_pending_image_mosaic_orders()

	if len(pending) == 0:
		print('No pending image container')
		return

	print(f'found {len(pending)} pending image container')

	confirmed_orders = []

	for order in pending:
		order_id = order['order_id']
		image_hash = order['image_hash']
		mosaic_hash = order['mosaic_hash']

		txes = image_hash + [mosaic_hash]

		payload = {"hashes": txes}

		client_response = await client.transaction_statuses(payload)

		if 0 == len(client_response) or len(txes) != len(client_response):
			continue

		all_confirmed = all(status['group'] == 'confirmed' for status in client_response)

		if all_confirmed:
			confirmed_orders.append(order_id)

	if len(confirmed_orders) == 0:
		print('image container have not confirm yet')
		return
	else:
		print(f'found {len(confirmed_orders)} image container confirmed')

	tomato_process = TomatoProcess(client, args.network, key_pair)

	network_time = await client.node_time()
	network_time = network_time.add_hours(2)

	for order_id in confirmed_orders:
		order_info = order_manager.get_order(order_id)
		garush_meta = {
			'type': 'garush',
			'version': 1,
			'name': f'Tomatina 2023 Art #{order_id}',
			'size': order_info['image_size'],
			'parser': 'generic',
			'mime': 'image/png',
			'userData': {
				'mosaicId': order_info['mosaic_id']
			}
		}

		garush_meta_yaml_string = yaml.dump(garush_meta, indent=4, default_flow_style=False)

		image_hashes_string = ','.join(order_info['image_hash'])

		image_container_hash = await tomato_process.process_image_container(network_time, garush_meta_yaml_string, image_hashes_string, args.dry_run)

		order_manager.update_order(order_id, {
			'image_container_hash': image_container_hash,
			"order_status": OrderStatus.PENDING_SETTLEMENT
		})

		print(f'processed order: {order_id}')
		print(f'image_container_hash: {image_container_hash}')

if '__main__' == __name__:
	asyncio.run(main())
