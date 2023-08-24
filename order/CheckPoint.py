import json

class CheckPoint:
    def __init__(self, filename='last_check_point.json'):
        self.filename = filename

    def save_to_json(self, data):
        with open(self.filename, 'w') as file:
            json.dump(data, file)

    def get_last_check_point(self):
        with open(self.filename, 'r') as file:
            data = json.load(file)

        return data['last_offset_id']
