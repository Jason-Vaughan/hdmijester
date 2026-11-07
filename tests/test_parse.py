"""Parser tests for bin/hdmijester-watch, using real log lines from a Mac Studio (M1 Max).

Run: python3 -m unittest discover -s tests
"""
import importlib.machinery
import importlib.util
import pathlib
import queue
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader('hdmi_watch', str(ROOT / 'bin' / 'hdmijester-watch'))
_spec = importlib.util.spec_from_loader('hdmi_watch', _loader)
hw = importlib.util.module_from_spec(_spec)
_loader.exec_module(hw)

CED = ('2026-10-14 19:42:20.123 E  kernel[0:26f] (DCP)  [DCPAVServiceHDMI.cpp::428] DCPAV[6669] '
       'AppleDCPMCDP29XX::hdmiCharacterErrorDetectionUpdate CED error count update: [11][0][4]')
LINK = ('2026-10-14 19:42:20.100 E  kernel[0:26f] (DCP)  [DCPDP13Service.cpp::1073] DCPAV[629] '
        'AppleDCPMCDP29XX::handleIRQHDMILinkStatusChanged HDMI link status changed')
PLUG_IN = ('2026-10-14 18:54:31.963 Df WindowServer[389:1146] [com.apple.coreanimation:WindowServer] '
           'Display 1 hotplug-state 1 updating digital modes: color 0x73b00c2d0; timing 0x731004540')
PLUG_OUT = ('2026-10-14 18:54:31.978 Df WindowServer[389:1146] [com.apple.coreanimation:WindowServer] '
            'Display 1 get_hotplug_state - not active')
OTHER_DISPLAY = ('2026-10-14 18:54:31.978 Df WindowServer[389:1146] [com.apple.coreanimation:WindowServer] '
                 'Display 2 get_hotplug_state - not active')
HPD_NOCHANGE = ('2026-10-15 01:53:28.004 Df kernel[0:b33] [com.apple.coreav:default] IOAV[230] '
                'AppleATCDPAltModePort(atc2-dpphy)<0x100000363>::checkInitialHPDState_block_invoke: '
                'synthesizing message=ConfigChange: HPD 0->0')
HPD_DROP = HPD_NOCHANGE.replace('HPD 0->0', 'HPD 1->0')
SINK_OUT = ('2026-10-14 19:49:57.457 E  kernel[0:26f] (DCP)  [DCPDPService.cpp::2799] DCPAV[7564] '
            'AppleDCPMCDP29XX::handleSinkCountChanged oldCount=1 newCount=0 add=0 remove=1')
SINK_IN = SINK_OUT.replace('oldCount=1 newCount=0 add=0 remove=1', 'oldCount=0 newCount=1 add=1 remove=0')
UNSTABLE = ('2026-10-14 19:42:26.000 E  kernel[0:26f] (DCP)  [DCPDPService.cpp::625] DCPAV[6678] '
            'AppleDCPMCDP29XX::checkLinkGated ret=0x00000000 link[0]Stable=NO')
STABLE = UNSTABLE.replace('Stable=NO', 'Stable=YES')


def parse(*lines):
    """Feed lines through hw.reader() and return the events it queued."""
    hw.events = queue.Queue()
    with mock.patch.object(hw, 'poll_lines', return_value=((1.0, l) for l in lines)):
        hw.reader()
    out = []
    while not hw.events.empty():
        kind, _ts, val = hw.events.get()
        out.append((kind, val))
    return out


class ParseTests(unittest.TestCase):
    def test_ced_counts_per_lane(self):
        self.assertEqual(parse(CED), [('ced', (11, 0, 4))])

    def test_link_status_change(self):
        self.assertEqual(parse(LINK), [('linkchg', None)])

    def test_hotplug_in_and_out_for_main_display(self):
        self.assertEqual(parse(PLUG_IN, PLUG_OUT), [('hotplug', 1), ('hotplug', 0)])

    def test_dcp_sink_count_unplug_and_replug(self):
        self.assertEqual(parse(SINK_OUT, SINK_IN), [('hotplug', 0), ('hotplug', 1)])

    def test_other_display_slots_ignored(self):
        self.assertEqual(parse(OTHER_DISPLAY), [])

    def test_hpd_only_reported_on_change(self):
        self.assertEqual(parse(HPD_NOCHANGE), [])
        self.assertEqual(parse(HPD_DROP), [('hpd', '1->0')])

    def test_link_stability(self):
        self.assertEqual(parse(UNSTABLE), [('unstable', None)])
        self.assertEqual(parse(STABLE), [])

    def test_timestamp_regex_matches_compact_style(self):
        m = hw.RE_TS.match(CED)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), '2026-10-14 19:42:20.123')


class SegmentTests(unittest.TestCase):
    def test_row_rates(self):
        seg = hw.Segment('cable A')
        seg.start -= 120  # two minutes old
        seg.ced_reports = 20
        seg.lane_sum = [200, 0, 10]
        seg.lane_max = [11, 0, 4]
        label, secs, rep_min, err_min, avg0, lanes, disc, unst = seg.row()
        self.assertEqual(label, 'cable A')
        self.assertAlmostEqual(float(rep_min), 10.0, places=0)
        self.assertAlmostEqual(float(err_min), 105.0, places=0)
        self.assertEqual(avg0.strip(), '10.0')
        self.assertEqual(lanes, '11/0/4')

    def test_spark_marks_zero_as_dot(self):
        self.assertEqual(hw.spark([0, 8], 8), '·█')


# system_profiler SPDisplaysDataType excerpts. The built-in panel is always
# listed first, which is why selecting the first-named display was the bug.
SP_BUILTIN_ONLY = (
    "Graphics/Displays:\n\n"
    "    Apple M4:\n\n"
    "      Displays:\n"
    "        Color LCD:\n"
    "          Display Type: Built-in Liquid Retina Display\n"
    "          Resolution: 2880 x 1864 Retina\n"
    "          Main Display: Yes\n"
    "          Online: Yes\n"
    "          Connection Type: Internal\n"
)
SP_ONE_EXTERNAL = SP_BUILTIN_ONLY + (
    "        LG ULTRAGEAR:\n"
    "          Resolution: 3840 x 2160 (2160p/4K UHD 1 - Ultra High Definition)\n"
    "          UI Looks like: 3840 x 2160 @ 60.00Hz\n"
    "          Online: Yes\n"
)
SP_TWO_EXTERNAL = SP_ONE_EXTERNAL + (
    "        ASUS MG28U:\n"
    "          Resolution: 1080 x 1920\n"
    "          UI Looks like: 1080 x 1920 @ 30.00Hz\n"
    "          Online: Yes\n"
)


class DisplayModeTests(unittest.TestCase):
    def test_builtin_only_reports_no_external(self):
        self.assertEqual(hw._describe_displays(SP_BUILTIN_ONLY),
                         'no external display detected')

    def test_skips_builtin_and_names_external(self):
        out = hw._describe_displays(SP_ONE_EXTERNAL)
        self.assertIn('LG ULTRAGEAR', out)
        self.assertIn('60.00Hz', out)
        self.assertNotIn('Color LCD', out)

    def test_lists_every_external_not_just_first(self):
        out = hw._describe_displays(SP_TWO_EXTERNAL)
        self.assertIn('LG ULTRAGEAR', out)
        self.assertIn('ASUS MG28U', out)
        self.assertNotIn('Color LCD', out)


if __name__ == '__main__':
    unittest.main()
