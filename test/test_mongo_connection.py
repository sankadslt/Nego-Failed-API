import unittest

from utils.mongo_connection import MongoConnection


class TestMongoConnection(unittest.TestCase):
    def test_get_db_uses_configured_database_name_without_querying_server(self):
        connection = MongoConnection(
            uri="mongodb://localhost:27017",
            db_name="unit_test_db",
        )

        self.assertEqual(connection.get_db().name, "unit_test_db")


if __name__ == "__main__":
    unittest.main()
