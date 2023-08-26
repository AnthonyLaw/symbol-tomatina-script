from flask import Flask, jsonify, request, send_from_directory
import os
import json

IMAGES_FOLDER = os.environ.get('IMAGES_FOLDER', '/art_generated')
Order_FILE = os.environ.get('ORDER_FILE', '/data/order.json')

def create_app():
	app = Flask(__name__)

	setup_error_handlers(app)

	setup_routes(app)

	return app

def setup_routes(app):
	@app.route('/api/orders', methods=['GET'])
	def get_orders():
		url_root = request.url_root

		with open(Order_FILE) as order_file:
			orders = json.load(order_file)

		for order in orders:
			art_png = order['message'].replace(',', '_') + '.png'

			order['image'] = f"{url_root}images/{art_png}"

		return jsonify(orders)

	@app.route('/images/<filename>', methods=['GET'])
	def get_image(filename):
		return send_from_directory(IMAGES_FOLDER, filename)


def setup_error_handlers(app):
	@app.errorhandler(404)
	def not_found(_):
		response = {
			'status': 404,
			'message': 'Resource not found'
		}
		return jsonify(response), 404