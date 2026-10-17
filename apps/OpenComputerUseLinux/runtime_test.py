import contextlib
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


class FocusDetailsTests(unittest.TestCase):
    def setUp(self):
        self.runtime = load_runtime()
        self.runtime.Atspi.StateType = types.SimpleNamespace(FOCUSED="focused")

    def node(self, children=(), focused=False):
        node = mock.Mock()
        node.get_child_count.return_value = len(children)
        node.get_child_at_index.side_effect = lambda i: children[i]
        node.get_state_set.return_value.contains.side_effect = lambda s: focused
        node.get_name.return_value = "Editor"
        node.get_role_name.return_value = "text"
        node.get_interfaces.return_value = ["Text"]
        return node

    def test_summary_and_selection_share_one_focus_lookup(self):
        focused = self.node(focused=True)
        root = self.node([focused])
        self.runtime.Atspi.Text = types.SimpleNamespace(
            get_n_selections=lambda _: 1,
            get_selection=lambda _iface, index: types.SimpleNamespace(start_offset=1, end_offset=8),
            get_text=lambda _iface, start, end: "hello"[start:end],
        )
        summary, selected, truncated = self.runtime.focus_details(root)
        self.assertEqual((summary, selected, truncated), ("text Editor", "ello", False))
        root.get_child_at_index.assert_called_once_with(0)
        focused.get_state_set.assert_called_once()

    def test_node_budget_reports_incomplete_instead_of_absent(self):
        children = [self.node() for _ in range(100)]
        root = self.node(children)
        self.assertEqual(self.runtime.focus_details(root, max_nodes=3), (None, None, True))
        self.assertEqual(root.get_child_at_index.call_count, 2)

    def test_depth_budget_and_complete_absence(self):
        root = self.node([self.node([self.node(focused=True)])])
        self.assertEqual(self.runtime.focus_details(root, max_depth=1), (None, None, True))
        self.assertEqual(self.runtime.focus_details(self.node()), (None, None, False))

    def test_depth_boundary_does_not_fetch_out_of_budget_children(self):
        boundary = self.node()
        boundary.get_child_count.return_value = 100
        boundary.get_child_at_index.side_effect = None
        boundary.get_child_at_index.return_value = None
        root = self.node([boundary])
        self.assertEqual(self.runtime.focus_details(root, max_nodes=3, max_depth=1), (None, None, True))
        boundary.get_child_at_index.assert_not_called()

    def test_depth_boundary_leaf_is_complete(self):
        root = self.node([self.node()])
        self.assertEqual(self.runtime.focus_details(root, max_depth=1), (None, None, False))

    def test_focus_after_a_pruned_branch_is_still_reported(self):
        pruned = self.node([self.node()])
        focused = self.node(focused=True)
        root = self.node([pruned, focused])
        self.assertEqual(self.runtime.focus_details(root, max_depth=1), ("text Editor", None, False))
        pruned.get_child_at_index.assert_not_called()

    def test_selection_uses_standard_atspi_api_and_character_offsets(self):
        focused = self.node(focused=True)
        self.runtime.Atspi.Text = types.SimpleNamespace(
            get_n_selections=lambda _: 1,
            get_selection=lambda _iface, index: types.SimpleNamespace(start_offset=1, end_offset=4),
            get_text=lambda _iface, start, end: "a中文🙂z"[start:end],
        )
        self.assertEqual(self.runtime.focus_details(focused), ("text Editor", "中文🙂", False))
        self.assertEqual(self.runtime.focus_details(focused, text_limit=2), ("text Ed...", "中文...", False))

    def test_no_selection_does_not_fetch_a_range(self):
        selection = mock.Mock()
        self.runtime.Atspi.Text = types.SimpleNamespace(get_n_selections=lambda _: 0, get_selection=selection)
        self.assertEqual(self.runtime.focus_details(self.node(focused=True)), ("text Editor", None, False))
        selection.assert_not_called()

    def test_selection_read_failure_keeps_the_focus_summary(self):
        self.runtime.Atspi.Text = types.SimpleNamespace(
            get_n_selections=lambda _: 1,
            get_selection=mock.Mock(side_effect=RuntimeError("element became unavailable")),
        )
        self.assertEqual(self.runtime.focus_details(self.node(focused=True)), ("text Editor", None, False))

    def test_snapshot_reports_focus_budget_exhaustion(self):
        with mock.patch.object(self.runtime, "resolve_app"), \
             mock.patch.object(self.runtime, "main_window", return_value=(0, self.node())), \
             mock.patch.object(self.runtime, "extents"), \
             mock.patch.object(self.runtime, "render_tree", return_value=([], [])), \
             mock.patch.object(self.runtime, "focus_details", return_value=(None, None, True)) as focus, \
             mock.patch.object(self.runtime, "node_pid", return_value=42), \
             mock.patch.object(self.runtime, "node_name", return_value="Editor"), \
             mock.patch.object(self.runtime, "capture_window_png"):
            state = self.runtime.build_snapshot("Editor", max_tree_nodes=5, max_tree_depth=2)
        self.assertIn("incomplete", state["treeLines"][0])
        self.assertEqual(focus.call_args.args[2:], (5, 2))


class RuntimeActionReadBackTests(unittest.TestCase):
    def setUp(self):
        self.runtime = load_runtime()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(self.runtime, "resolve_app"))
        self.stack.enter_context(mock.patch.object(self.runtime, "main_window", return_value=(0, object())))
        for name in ("extents", "find_element", "send_key", "send_drag", "send_mouse_click",
                     "invoke_secondary_action", "scroll_element", "insert_text", "set_element_value"):
            self.stack.enter_context(mock.patch.object(self.runtime, name))
        self.snapshot = self.stack.enter_context(mock.patch.object(self.runtime, "build_snapshot", return_value={"elements": []}))
        self.sleep = self.stack.enter_context(mock.patch.object(self.runtime.time, "sleep"))

    def test_all_actions_skip_snapshot_and_settle_when_requested(self):
        for tool, arguments in (
            ("click", {"x": 1, "y": 2}),
            ("drag", {"from_x": 1, "from_y": 2, "to_x": 3, "to_y": 4}),
            ("press_key", {"key": "Return"}),
            ("type_text", {"text": "hello"}),
            ("set_value", {"value": "hello"}),
            ("perform_secondary_action", {"action": "activate"}),
            ("scroll", {"direction": "down", "pages": 1}),
        ):
            with self.subTest(tool=tool):
                with mock.patch.object(self.runtime, "screen_point", side_effect=[(1, 2), (3, 4)]):
                    result = self.runtime.perform_operation({"tool": tool, "app": "Editor", "skip_read_back": True, **arguments})
                self.assertEqual(result, {"ok": True})
                self.snapshot.assert_not_called()
                self.sleep.assert_not_called()
        self.runtime.send_key.assert_called_once_with("Return")
        self.runtime.send_drag.assert_called_once_with(1, 2, 3, 4)
        self.runtime.insert_text.assert_called_once()

    def test_default_action_still_waits_and_returns_snapshot(self):
        result = self.runtime.perform_operation({"tool": "press_key", "app": "Editor", "key": "Return"})
        self.assertEqual(result, {"ok": True, "snapshot": {"elements": []}})
        self.sleep.assert_called_once_with(0.12)
        self.snapshot.assert_called_once_with("Editor")

    def test_explicit_observation_is_not_suppressed(self):
        result = self.runtime.perform_operation({"tool": "get_app_state", "app": "Editor", "skip_read_back": True})
        self.assertIn("snapshot", result)
        self.snapshot.assert_called_once()

    def test_action_errors_are_not_suppressed(self):
        self.runtime.send_key.side_effect = RuntimeError("input failed")
        with self.assertRaisesRegex(RuntimeError, "input failed"):
            self.runtime.perform_operation({"tool": "press_key", "app": "Editor", "key": "Return", "skip_read_back": True})
        self.snapshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
