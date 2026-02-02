import unittest

from component import Component
from db import get_connection, init_db
from events import EventBus
from services import ComponentService
from user import User


class PrototypeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.bus = EventBus()
        self.service = ComponentService(self.conn, self.bus)
        self.user = User(id=None, name="Test Engineer")

    def tearDown(self) -> None:
        self.conn.close()

    def test_add_and_list_component(self) -> None:
        cid = self.service.add_component(
            self.user,
            Component(
                id=None,
                name="GPS Module",
                description="High integrity GPS receiver module",
                status="active",
                quantity=10,
                min_quantity=2,
            ),
        )
        self.assertIsInstance(cid, int)
        self.assertGreater(cid, 0)

        comps = self.service.list_components()
        self.assertEqual(len(comps), 1)
        self.assertEqual(comps[0].name, "GPS Module")

    def test_duplicate_component_name_rejected(self) -> None:
        self.service.add_component(
            self.user,
            Component(id=None, name="Battery Pack", status="idle", quantity=5, min_quantity=1),
        )
        with self.assertRaises(ValueError):
            self.service.add_component(
                self.user,
                Component(id=None, name="Battery Pack", status="idle", quantity=5, min_quantity=1),
            )

    def test_update_status_invalid_rejected(self) -> None:
        cid = self.service.add_component(
            self.user,
            Component(id=None, name="Sensor A", status="idle", quantity=1, min_quantity=0),
        )
        with self.assertRaises(ValueError):
            self.service.update_status(self.user, cid, "broken")  # not allowed

    def test_low_stock_event_published(self) -> None:
        events = []

        def handler(event):
            events.append(event)

        self.bus.subscribe("LOW_STOCK", handler)

        cid = self.service.add_component(
            self.user,
            Component(id=None, name="Connector", status="idle", quantity=3, min_quantity=1),
        )
        # Adjust down to threshold (<= min_quantity) to trigger LOW_STOCK
        self.service.adjust_quantity(self.user, cid, -2, "Used on bench test")

        self.assertTrue(any(e.name == "LOW_STOCK" and e.payload.get("component_id") == cid for e in events))

    def test_logs_written(self) -> None:
        cid = self.service.add_component(
            self.user,
            Component(id=None, name="Actuator", status="idle", quantity=2, min_quantity=1),
        )
        self.service.update_status(self.user, cid, "active", "Installed in rig")
        self.service.adjust_quantity(self.user, cid, -1, "Consumed for build")

        rows = self.service.list_logs(component_id=cid, limit=100)
        actions = [r["action"] for r in rows]
        self.assertIn("CREATE_COMPONENT", actions)
        self.assertIn("UPDATE_STATUS", actions)
        self.assertIn("ADJUST_QUANTITY", actions)


if __name__ == "__main__":
    unittest.main(verbosity=2)

