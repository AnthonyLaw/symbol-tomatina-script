import argparse
import asyncio
import os

from binascii import unhexlify
from client.SymbolClient import SymbolClient
from symbolchain.CryptoTypes import PrivateKey, PublicKey
from symbolchain.facade.SymbolFacade import SymbolFacade

from order.CheckPoint import CheckPoint
from order.OrderManager import OrderManager, OrderStatus
from TomatoProcess import TomatoProcess
from generator import generate_images_nft


async def main():
	parser = argparse.ArgumentParser(description='process tomation nft order')
	parser.add_argument('--symbol-node', help='Symbol node url', default='http://wolf.importance.jp:3000')
	parser.add_argument('--network', help='NEM and Symbol network', choices=['testnet', 'mainnet'], default='mainnet')
	parser.add_argument('--order-address', help='address receive order transaction')
	parser.add_argument('--private-key', help='private key of the account to use for NFT creation')
	parser.add_argument('--check-point-file', help='check point file', default='data/last_check_point.json')
	parser.add_argument('--order-file', help='order file', default='data/order.json')
	parser.add_argument('--art-generated-path', help='path to save image file', default='art_generated')
	parser.add_argument('--dry-run', help='print transactions without sending', action='store_true')

	args = parser.parse_args()

	client = SymbolClient(args.symbol_node)
	facade = SymbolFacade(args.network)

	private_key = PrivateKey(args.private_key)
	key_pair = facade.KeyPair(private_key)

	print(f'network: {args.network}')

	print('Checking for new orders')

	currency_mosaic_id = await client.currency_mosaic_id()

	native_mosaic_id = hex(currency_mosaic_id)[2:].upper()
	order_payment = 70000000

	check_point = CheckPoint(args.check_point_file)
	last_check_point = check_point.get_last_check_point()

	if not last_check_point:
		last_check_point = None

	transactions = await client.incoming_transfer_transactions(recipient_address=args.order_address, start_id=last_check_point)

	if (len(transactions) == 0):
		print('No new order')
		return

	print(f'found {len(transactions)} transactions')

	orders = []

	print(f'found {len(orders)} orders')

	for transaction in transactions:
		if 'message' not in transaction['transaction']:
			continue

		mosaics = transaction['transaction']['mosaics']

		if len(mosaics) == 0:
			continue

		mosaic = mosaics[0]
		if native_mosaic_id == mosaic['id'] and int(mosaic['amount']) >= order_payment:
			message = transaction['transaction']['message']
			buyer_address = facade.network.public_key_to_address(PublicKey(transaction['transaction']['signerPublicKey']))

			hash_value = transaction['meta'].get('hash', transaction['meta'].get('aggregateHash', None))
			print(f"New order: address: {buyer_address} tx: {hash_value}")

			orders.append((unhexlify(message).decode('utf8').replace('\x00', ''), str(hash_value), str(buyer_address), int(mosaic['amount'])))

	network_time =  await client.node_time()
	network_time = network_time.add_hours(2)

	order_manager = OrderManager(args.order_file)

	for order in orders:
		tomato_process = TomatoProcess(client, args.network, key_pair)

		numbers_list = [int(x)+1 for x in order[0].split(',')]

		# message format example: 1,1,1,1,1,1
		# image name format example: Arm Left_1.png (1-9)

		arm_left = f'art_source/arm-left/Arm Left_{numbers_list[0]}.png'
		arm_right = f'art_source/arm-right/Arm Right_{numbers_list[1]}.png'
		body = f'art_source/body/body.png'
		eyes = f'art_source/eyes/Eyes_{numbers_list[2]}.png'
		feet = f'art_source/legs/feet_{numbers_list[3]}.png'
		mouth = f'art_source/mouth/Mouth-{numbers_list[4]}.png'
		stem = f'art_source/stem/stem-{numbers_list[5]}.png'

		# generate image name: 1_1_1_1_1_1.png
		output_filename = f'{args.art_generated_path}' + '/' +order[0].replace(',', '_') + '.png'

		generate_images_nft([
			feet,
			body,
			arm_left,
			arm_right,
			eyes,
			mouth,
			stem
		], output_filename)

		image_size = os.path.getsize(output_filename)

		# create mosaic
		create_mosaic_hash, mosaic_id = await tomato_process.create_mosaic(network_time, 1, args.dry_run)

		# upload image to chain
		image_transaction_hash = await tomato_process.process_upload_to_chain(network_time, output_filename, args.dry_run)

		order_manager.add_order({
			"message": order[0],
			"order_hash": order[1],
			"buyer_address": order[2],
			"paid": order[3],
			"mosaic_hash": create_mosaic_hash,
			"mosaic_id": mosaic_id,
			"image_hash": image_transaction_hash,
			"image_size": image_size,
			"image_container_hash": "",
			"settlement_hash": "",
			"order_status": OrderStatus.PENDING_IMAGE_CONTAINER
		})

	check_point.save_to_json({'last_offset_id': transactions[-1]["id"]})

if '__main__' == __name__:
	asyncio.run(main())
