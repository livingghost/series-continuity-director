#!/usr/bin/env python3
"""Four-clock constraints, real audiovisual rendering and extraction tests."""
from pathlib import Path
import copy
import importlib.util
import tempfile
import unittest
import execution_contract as c
import timed_sequence as t
import timed_test_support

ROOT=Path(__file__).resolve().parents[1]
class TimedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.plan=timed_test_support.inputs(self.root)
    def check(self):return t.validate_plan(self.root,self.plan)
    def test_no_story_or_cast_is_required(self):self.assertEqual(self.check()['output_frames'],48)
    def test_hold_without_change_is_valid(self):
        self.plan['placements'][1]['video']['x']=[0,0];self.plan['cues'][0]['action']='Hold the declared arrangement.';self.check()
    def test_story_clock_is_not_seconds(self):
        self.plan['clocks'][0]['kind']='story'
        with self.assertRaises(ValueError):self.check()
    def test_frames_need_explicit_rate(self):
        self.plan['clocks'][1]['rate']=None
        with self.assertRaises(ValueError):self.check()
    def test_source_range_must_exist(self):
        self.plan['placements'][2]['source']['end']=4
        with self.assertRaises(ValueError):self.check()
    def test_rate_and_edit_duration_match(self):
        self.plan['placements'][2]['rate']=2
        with self.assertRaises(ValueError):self.check()
    def test_source_content_is_pinned(self):
        (self.root/'signal.wav').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.check()
    def test_still_has_no_fictitious_source_duration(self):
        self.plan['placements'][0]['source']={'clock':'signal-source','start':0,'end':2}
        with self.assertRaises(ValueError):self.check()
    def test_missing_actual_sound_is_not_passed(self):
        self.plan['placements'][0]['audio']={'gain':1}
        with self.assertRaises(ValueError):self.check()
    def test_invalid_frame_grid(self):
        self.plan['output']['duration']=2.01
        with self.assertRaises(ValueError):self.check()
    def test_cue_overlap_is_measured(self):
        first=self.plan['cues'][0];second=copy.deepcopy(first);second['id']='response';second['span']={'clock':'movement','start':20,'end':48}
        self.plan['cues'].append(second);self.plan['cue_links'].append({'cue':'response','placements':['moving'],'relation':'reference','limitations':['Proxy only.']})
        self.plan['constraints']=[{'first':'traverse','relation':'overlaps','second':'response'}];self.check()
        self.plan['constraints'][0]['relation']='finishes-before'
        with self.assertRaises(ValueError):self.check()
    def test_omission_is_explicit_not_fake_realization(self):
        self.plan['cue_links'][0].update(placements=[],relation='omitted',limitations=['The action is omitted; only its result will be shown.']);self.check()
    def test_unexplained_omission_is_not_accepted(self):
        self.plan['cue_links'][0].update(placements=[],relation='omitted',limitations=[])
        with self.assertRaises(ValueError):self.check()
    def test_empty_black_sequence_is_not_aesthetic_error(self):
        self.plan.update(assets=[],cues=[],constraints=[],placements=[],cue_links=[])
        result=t.render_files(self.root,self.plan,self.root/'black.mp4');self.assertEqual(result['planned']['output_frames'],48)
    def test_actual_audio_video_and_run_completion(self):
        spec=importlib.util.spec_from_file_location('timed_example',ROOT/'examples/timed-production/run_example.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        result=module.run(self.root/'actual');self.assertTrue(result['ok']);self.assertTrue(result['measurements']['different_frame_pixels'])
    def test_frame_and_audio_extract_bounds(self):
        t.render_files(self.root,self.plan,self.root/'fixture.mp4');digest=c.digest(c.read(self.root/'fixture.mp4'))
        with self.assertRaises(ValueError):t.extract(self.root,'fixture.mp4',digest,'bad.png',start=2)
        with self.assertRaises(ValueError):t.extract(self.root,'fixture.mp4',digest,'bad.wav',start=0,end=3)
        with self.assertRaises(ValueError):t.extract(self.root,'fixture.mp4','a'*64,'bad.png',start=0)
    def test_render_does_not_overwrite(self):
        (self.root/'existing.mp4').write_bytes(b'retain')
        with self.assertRaises(FileExistsError):t.render_files(self.root,self.plan,self.root/'existing.mp4')
        self.assertEqual((self.root/'existing.mp4').read_bytes(),b'retain')

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
