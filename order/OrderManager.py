import json
from enum import Enum

class OrderStatus(str, Enum):
    PENDING_IMAGE_CONTAINER = "pending_image_container"
    PENDING_SETTLEMENT = "pending_settlement"
    COMPLETED = "completed"

class OrderManager:
	def __init__(self, filename='order.json'):
		self.filename = filename

	def load_from_json(self):
		try:
			with open(self.filename, 'r') as file:
				if not file.read(1):  # Check if the file is empty by reading the first character
					return []
				file.seek(0)  # Reset file pointer back to the beginning
				return json.load(file)
		except FileNotFoundError:
			return []

	def add_order(self, order_info):
		orders = self.load_from_json()

		# Auto-increment order_id based on the last order's ID
		order_id = orders[-1]["order_id"] + 1 if orders else 1
		order_info["order_id"] = order_id

		orders.append(order_info)
		self.save_to_json(orders)
		return order_id  # Return the new order's ID for confirmation or further use

	def update_order(self, order_id, updated_order_info):
		orders = self.load_from_json()
		for order in orders:
			if order["order_id"] == order_id:
				order.update(updated_order_info)
				self.save_to_json(orders)
				return True
		return False

	def save_to_json(self, data):
		with open(self.filename, 'w') as file:
			json.dump(data, file, indent='\t')

	def get_order(self, order_id):
		orders = self.load_from_json()
		for order in orders:
			if order["order_id"] == order_id:
				return order
		return None  # Order not found

	def total_orders(self):
		orders = self.load_from_json()
		return len(orders)

	def get_pending_image_mosaic_orders(self):
		orders = self.load_from_json()
		return [order for order in orders if order["order_status"] == OrderStatus.PENDING_IMAGE_CONTAINER]

	def get_pending_settlement_orders(self):
		orders = self.load_from_json()
		return [order for order in orders if order["order_status"] == OrderStatus.PENDING_SETTLEMENT]
