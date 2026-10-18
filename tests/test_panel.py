import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('panel', ROOT / 'scripts/parse_panel.py')
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)

class PanelTests(unittest.TestCase):
    def test_example(self):
        records = panel.parse((ROOT / 'examples/panel-on.hex').read_text())
        self.assertEqual([r['offset'] for r in records], [0, 9, 17])
        self.assertEqual([r['delay_ms'] for r in records], [0, 120, 20])
        self.assertEqual(records[0]['payload'], [0x3a, 0x77])

    def test_big_endian_length(self):
        r = panel.parse('39 01 00 00 00 01 00 ' + 'ab ' * 256)[0]
        self.assertEqual(r['length'], 256)
        self.assertEqual(len(r['payload']), 256)

    def test_metadata_and_unknown_type_preserved(self):
        r = panel.parse('fe 00 02 01 07 00 02 aa bb')[0]
        self.assertEqual((r['type'], r['last'], r['channel'], r['ack']), (254, 0, 2, 1))
        self.assertEqual(r['kind'], 'unknown_preserved')

    def test_generic_is_not_dcs(self):
        self.assertEqual(panel.parse('29 01 00 00 00 00 01 ab')[0]['kind'], 'generic_long_write')

    def test_dts(self):
        self.assertEqual(panel.parse('qcom,mdss-dsi-on-command = [05 01 00 00 00 00 01 11];')[0]['payload'], [17])

    def test_invalid(self):
        for text in ['', 'gg', '05 01', '05 01 00 00 00 00 02 11', '[00] [01]', '0x05']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                panel.parse(text)

    def test_padding_preserved(self):
        self.assertEqual(panel.parse('05 01 00 00 00 00 02 11 00')[0]['payload'], [17, 0])

    def test_c_output(self):
        c = panel.render_c(panel.parse('05 01 00 00 78 00 01 11'))
        self.assertIn('.delay_ms = 120', c)
        self.assertIn('0x11', c)
        self.assertNotIn('mipi_dsi_dcs_cmd', c)

if __name__ == '__main__':
    unittest.main()
