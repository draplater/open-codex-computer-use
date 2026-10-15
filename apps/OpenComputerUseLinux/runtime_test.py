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


class RuntimeSelectiveObservationTests(unittest.TestCase):
    def setUp(self):
        self.runtime = load_runtime()
        self.app = object()
        self.window = object()
        self.patches = []
        for name, value in {
            "resolve_app": self.app,
            "main_window": (0, self.window),
            "extents": {"x": 1, "y": 2, "width": 300, "height": 200},
            "node_pid": 42,
            "node_name": "Editor",
            "render_tree": ([{"index": 7}], ["tree"]),
            "focused_summary": "focus",
            "selected_text": "selection",
            "capture_window_png": "png",
        }.items():
            patch = mock.patch.object(self.runtime, name, return_value=value)
            self.patches.append(patch)
            patch.start()
            self.addCleanup(patch.stop)

    def test_defaults_still_collect_full_state(self):
        state = self.runtime.build_snapshot("Editor")
        self.assertEqual(state["elements"], [{"index": 7}])
        self.assertEqual(state["screenshotPngBase64"], "png")
        self.runtime.focused_summary.assert_called_once()
        self.runtime.selected_text.assert_called_once()

    def test_screenshot_only_skips_tree_focus_and_selection(self):
        state = self.runtime.build_snapshot("Editor", include_ax=False)
        self.assertEqual(state["screenshotPngBase64"], "png")
        self.assertEqual(state["elements"], [])
        self.assertEqual(state["treeLines"], [])
        self.assertIsNone(state["focusedSummary"])
        self.assertIsNone(state["selectedText"])
        for name in ("render_tree", "focused_summary", "selected_text"):
            getattr(self.runtime, name).assert_not_called()

    def test_ax_only_skips_capture(self):
        state = self.runtime.build_snapshot("Editor", include_screenshot=False)
        self.assertEqual(state["treeLines"], ["tree"])
        self.assertIsNone(state["screenshotPngBase64"])
        self.runtime.capture_window_png.assert_not_called()

    def test_tool_forwards_explicit_observation_flags(self):
        state = self.runtime.perform_operation({"tool": "get_app_state", "app": "Editor", "include_ax": False})
        self.assertTrue(state["ok"])
        self.runtime.render_tree.assert_not_called()

    def test_invalid_or_empty_observations_are_rejected(self):
        for flags in ({"include_ax": "false"}, {"include_screenshot": None},
                      {"include_ax": 0}, {"include_ax": False, "include_screenshot": False}):
            with self.subTest(flags=flags):
                with self.assertRaises(RuntimeError):
                    self.runtime.perform_operation({"tool": "get_app_state", "app": "Editor", **flags})
        self.runtime.resolve_app.assert_not_called()


if __name__ == "__main__":
    unittest.main()
