import importlib.util
import pathlib
import sys
import types
import unittest
from unittest import mock


class FakeText:
    @staticmethod
    def get_character_count(_interface):
        return 5

    @staticmethod
    def get_text(_interface, _start, _end):
        return "hello"


class FakeEditableText:
    @staticmethod
    def insert_text(_interface, _offset, _text, _length):
        return True

    @staticmethod
    def set_text_contents(_interface, _text):
        return True


def load_runtime():
    gi = types.ModuleType("gi")
    gi.require_version = lambda *_args: None
    repository = types.ModuleType("gi.repository")
    repository.Atspi = types.SimpleNamespace(
        Text=FakeText,
        EditableText=FakeEditableText,
    )
    repository.Gdk = types.SimpleNamespace()
    gi.repository = repository

    runtime_path = pathlib.Path(__file__).with_name("runtime.py")
    spec = importlib.util.spec_from_file_location("open_computer_use_linux_runtime", runtime_path)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(
        sys.modules,
        {"gi": gi, "gi.repository": repository},
    ):
        spec.loader.exec_module(module)
    return module


class InterfaceOnlyAccessible:
    def __init__(self, interfaces):
        self.interfaces = interfaces

    def get_interfaces(self):
        return self.interfaces

    def get_text_iface(self):
        return self

    def get_editable_text_iface(self):
        return self

    def get_child_count(self):
        return 0


class RuntimeInterfaceDetectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = load_runtime()

    def test_text_value_uses_accessible_interfaces(self):
        node = InterfaceOnlyAccessible(["Accessible", "Text"])

        self.assertEqual(self.runtime.text_value(node), "hello")

    def test_insert_text_uses_accessible_interfaces(self):
        node = InterfaceOnlyAccessible(["Accessible", "Text", "EditableText"])

        self.assertTrue(self.runtime.insert_text(node, "hello"))

    def test_set_value_uses_accessible_interfaces(self):
        node = InterfaceOnlyAccessible(["Accessible", "Text", "EditableText"])

        self.assertTrue(self.runtime.set_element_value(node, "hello"))


class FakeKeySynthType:
    PRESS = "PRESS"
    RELEASE = "RELEASE"
    PRESSRELEASE = "PRESSRELEASE"
    SYM = "SYM"
    STRING = "STRING"
    LOCKMODIFIERS = "LOCKMODIFIERS"
    UNLOCKMODIFIERS = "UNLOCKMODIFIERS"


class FakeModifierType:
    SHIFT = 0
    CONTROL = 2
    ALT = 3
    META3 = 6


KEYSYMS = {"Return": 0xFF0D, "Tab": 0xFF09, "Down": 0xFF54}


class RuntimeKeyTests(unittest.TestCase):
    def setUp(self):
        self.runtime = load_runtime()
        self.events = []
        self.runtime.Atspi = types.SimpleNamespace(
            KeySynthType=FakeKeySynthType,
            ModifierType=FakeModifierType,
            generate_keyboard_event=lambda value, text, synth: self.events.append(
                (value, text, synth)
            ),
        )
        self.runtime.Gdk = types.SimpleNamespace(
            # Like GDK, unknown names map to VoidSymbol rather than 0.
            keyval_from_name=lambda name: KEYSYMS.get(name, 0xFFFFFF),
            unicode_to_keyval=lambda codepoint: codepoint,
        )

    def test_named_key_is_sent_as_keysym(self):
        self.runtime.send_key("Enter")

        self.assertEqual(self.events, [(0xFF0D, None, "SYM")])

    def test_modifiers_are_held_around_the_key(self):
        self.runtime.send_key("ctrl+shift+Tab")

        mask = (1 << FakeModifierType.CONTROL) | (1 << FakeModifierType.SHIFT)
        self.assertEqual(
            self.events,
            [
                (mask, None, "LOCKMODIFIERS"),
                (0xFF09, None, "SYM"),
                (mask, None, "UNLOCKMODIFIERS"),
            ],
        )

    def test_modified_character_is_sent_as_keysym(self):
        self.runtime.send_key("ctrl+a")

        mask = 1 << FakeModifierType.CONTROL
        self.assertEqual(self.events[1], (ord("a"), None, "SYM"))
        self.assertEqual(self.events[0], (mask, None, "LOCKMODIFIERS"))

    def test_modified_punctuation_is_sent_as_keysym(self):
        self.runtime.send_key("ctrl+/")

        self.assertEqual(self.events[1], (ord("/"), None, "SYM"))

    def test_unknown_key_name_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.runtime.send_key("NoSuchKey")

        self.assertEqual(self.events, [])

    def test_plain_character_is_typed(self):
        self.runtime.send_key("a")

        self.assertEqual(self.events, [(0, "a", "STRING")])

    def test_unknown_modifier_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.runtime.send_key("hyper+a")

        self.assertEqual(self.events, [])


class HiddenDetailsTests(unittest.TestCase):
    def setUp(self):
        self.runtime = load_runtime()
        self.runtime.Atspi.StateType = types.SimpleNamespace(SHOWING="showing")

    def node(self, showing):
        node = mock.Mock()
        node.get_name.return_value = "Menu"
        node.get_role_name.return_value = "menu"
        node.get_child_count.return_value = 0
        node.get_state_set.return_value.contains.return_value = showing
        return node

    def test_hidden_record_retains_identity_and_skips_expensive_properties(self):
        node = self.node(False)
        with mock.patch.object(self.runtime, "relative_frame") as geometry, \
             mock.patch.object(self.runtime, "element_value") as value, \
             mock.patch.object(self.runtime, "action_names") as actions:
            record = self.runtime.record_for(node, 7, [0, 3], None, lightweight_hidden=True)
        self.assertEqual((record["index"], record["runtimeId"], record["name"]), (7, [0, 3], "Menu"))
        self.assertTrue(record["detailsOmitted"])
        for query in (geometry, value, actions):
            query.assert_not_called()
        node.get_toolkit_name.assert_not_called()
        node.get_accessible_id.assert_not_called()

    def test_default_and_unknown_or_showing_state_keep_full_details(self):
        for enabled, showing in ((False, False), (True, True), (True, None)):
            with self.subTest(enabled=enabled, showing=showing):
                node = self.node(showing)
                with mock.patch.object(self.runtime, "relative_frame", return_value=None), \
                     mock.patch.object(self.runtime, "accessible_id", return_value="id"), \
                     mock.patch.object(self.runtime, "element_value", return_value="value"), \
                     mock.patch.object(self.runtime, "action_names", return_value=["open"]):
                    record = self.runtime.record_for(node, 0, [0], None, lightweight_hidden=enabled)
                self.assertNotIn("detailsOmitted", record)
                self.assertEqual((record["value"], record["actions"]), ("value", ["open"]))
                if not enabled:
                    node.get_state_set.assert_not_called()

    def test_hidden_parent_does_not_prune_visible_menu_children_or_renumber(self):
        parent = self.node(False)
        child = self.node(True)
        parent.get_child_count.return_value = 1
        parent.get_child_at_index.return_value = child
        with mock.patch.dict(self.runtime.os.environ, {"OPEN_COMPUTER_USE_LINUX_LIGHTWEIGHT_HIDDEN": "1"}), \
             mock.patch.object(self.runtime, "relative_frame", return_value=None), \
             mock.patch.object(self.runtime, "accessible_id", return_value="id"), \
             mock.patch.object(self.runtime, "element_value", return_value="value"), \
             mock.patch.object(self.runtime, "action_names", return_value=[]):
            records, lines = self.runtime.render_tree(parent, None, [0])
        self.assertEqual([r["index"] for r in records], [0, 1])
        self.assertTrue(records[0]["detailsOmitted"])
        self.assertNotIn("detailsOmitted", records[1])
        self.assertIn("hidden details omitted", lines[0])
        self.assertEqual(records[1]["runtimeId"], [0, 0])


if __name__ == "__main__":
    unittest.main()
