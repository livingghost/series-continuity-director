#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(HERE))
import execution_contract as c
import media_evidence
import generation_schedule, audio_master, caption_track, delivery_conform, review_coverage
import boundary_conform, music_cues, production_recipe, board_layout, production_graph, blocking_preview, comparison_plan

class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='scd-upgrade-')
        self.root=Path(self.tmp.name)
        (self.root/'media').mkdir();(self.root/'plans').mkdir();(self.root/'captions').mkdir()
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg:self.skipTest('ffmpeg unavailable')
        self.master=self.root/'media/master.mp4'
        cmd=[ffmpeg,'-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=black:s=64x64:r=24:d=2','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2','-shortest','-c:v','libx264','-pix_fmt','yuv420p','-r','24','-c:a','aac','-ar','48000','-ac','1','-y',str(self.master)]
        subprocess.run(cmd,check=True,timeout=20)
        self.sha=c.digest(c.read(self.master))
        self.media=media_evidence.inspect(self.master,c.read(self.master))
        self.audio_index=next(s['index'] for s in self.media['streams'] if s['codec_type']=='audio')
    def tearDown(self):self.tmp.cleanup()
    def write(self,name,value):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return p
    def test_generation_recipe_graph_and_previews(self):
        schedule={
          'purpose':'three short shots','lane':'independent-shots','edit_clock':{'unit':'frames','rate':{'numerator':24,'denominator':1}},'target_edit_span':{'start':0,'end':144},
          'surface':{'model':'fixture','service':'synthetic','operation':'video','input_mode':'text'},
          'generation_duration':{'kind':'discrete','values':[4,8],'minimum':None,'maximum':None,'step':None},
          'reference_contract':{'maximum':2,'roles':['identity','first-frame','last-frame'],'exclusive_role_sets':[['first-frame','last-frame']]},
          'units':[{'id':f's{i+1}','edit':{'start':i*48,'end':(i+1)*48},'generation_seconds':4,'source_use':{'start':0,'end':2},'playback_rate':1,'pre_handle':0,'post_handle':0,'reference_roles':[],'cues':[],'limitations':[]} for i in range(3)],
          'cost_conditions':['provider cost follows generated seconds, not edit seconds'],'assumptions':[],'unresolved':[]}
        report=generation_schedule.validate(schedule);self.assertEqual(report['status'],'structurally-feasible');self.assertEqual(report['planned_generation_seconds'],12.0);self.assertEqual(report['edit_seconds'],6.0)
        recipe={'purpose':'music-led-sequence','medium':'video','requirements':['preserve selected score'],'optional_stages':['caption-track'],'decisions':['cue adoption'],'deliverables':['delivery-master']}
        self.assertIn('audio-master',production_recipe.plan(recipe)['features'])
        graph={'purpose':'fixture','nodes':[{'id':'gen','operation':'generate','depends_on':[],'effect':'external-write','authority_scopes':['submit'],'cost':{'status':'bounded','amount':1,'currency':'USD'},'state':'complete'},{'id':'finish','operation':'edit','depends_on':['gen'],'effect':'local','authority_scopes':[],'cost':{'status':'not-applicable','amount':None,'currency':None},'state':'planned'}],'limitations':[]}
        self.assertEqual(production_graph.check(graph)['ready_nodes'],['finish'])
        board={'purpose':'planning','width':320,'height':180,'background':'#ffffff','units':[{'id':'panel-1','source':None,'bounds':{'x':0,'y':0,'width':160,'height':180},'label':'planned','include_annotation_in_model_input':False}],'limitations':[]}
        bp=self.root/'board.svg';self.assertEqual(board_layout.build_svg(self.root,board,bp)['status'],'pass')
        block={'width':320,'height':180,'camera':{'label':'eye-level','notes':[]},'objects':[{'id':'a','shape':'ellipse','x':40,'y':60,'width':50,'height':90,'knowledge':'declared','label':'subject'},{'id':'b','shape':'rect','x':170,'y':80,'width':40,'height':40,'knowledge':'assumed','label':'prop proxy'}],'limitations':['proxy only']}
        out=self.root/'blocking.svg';self.assertEqual(blocking_preview.build(block,out)['status'],'pass')
        evidence=self.root/'plans/temporal.json';evidence.write_text('{}\n',encoding='utf-8');esha=c.digest(c.read(evidence))
        comparison={'purpose':'fixture comparison','strategy':'end-to-end','cases':[{'id':'case','origin':'constructed-case','origin_note':'synthetic fixture','inputs':['media/master.mp4'],'criteria':[{'id':'technical','dimension':'delivery','kind':'technical','text':'measured output'}]}],'conditions':[{'id':'a','description':'fixture A'}],'trials':[{'id':'trial-a','case':'case','condition':'a','run':None,'candidate':None,'measurements':None,'temporal_evidence':[{'path':'plans/temporal.json','sha256':esha}],'audio_evidence':[],'delivery_evidence':[],'cost':{'status':'not-applicable','amount':None,'currency':None}}]}
        self.assertEqual(comparison_plan.check(self.root,comparison)['status'],'pass')
    def test_audio_captions_delivery_review_and_boundary(self):
        copied=self.root/'media/master-copy.mp4';copied.write_bytes(c.read(self.master));copysha=c.digest(c.read(copied))
        ap={'source':{'path':'media/master.mp4','sha256':self.sha,'stream_index':self.audio_index},'output':{'path':'media/master-copy.mp4','sha256':copysha,'stream_index':self.audio_index},'preservation':'decoded-samples-preserve','allowed_operations':['remux'],'processing_graph':[{'id':'copy','operation':'remux','input':'source','output':'output','lossy_encode':False}],'limitations':[]}
        self.assertEqual(audio_master.check(self.root,ap)['status'],'pass')
        cp={'source_master':{'path':'media/master.mp4','sha256':self.sha},'language':'ja','direction':'ltr','purpose':'exact-spoken-dialogue','clock':{'unit':'frames','rate':{'numerator':24,'denominator':1}},'cues':[{'id':'line-1','start':12,'end':36,'speaker':'a','text':'テストです。','source_line':{'document':'narrative/dialogue.md','id':'line-1'},'word_timing':None}],'style':{'font':None,'size':None,'margin_x':24,'margin_y':24,'max_lines':2},'delivery_modes':['sidecar'],'limitations':[]}
        srt=self.root/'captions/ja.srt';self.assertEqual(caption_track.compile_sidecar(self.root,cp,srt,'srt')['status'],'pass');srtsha=c.digest(c.read(srt))
        prof={'purpose':'fixture','source':{'path':'media/master.mp4','sha256':self.sha},'video':{'width':64,'height':64,'fps':{'numerator':24,'denominator':1},'codec':'h264','pixel_format':'yuv420p'},'duration':{'minimum':1.9,'maximum':2.1,'exact_frames':48},'audio':{'required':True,'codec':'aac','sample_rate':48000,'channels':1},'sidecars':[{'path':'captions/ja.srt','sha256':srtsha}],'limitations':[]}
        self.assertEqual(delivery_conform.check(self.root,prof)['status'],'pass')
        cov={'artifact':{'path':'media/master.mp4','sha256':self.sha},'requirements':[{'id':'full','kind':'full-playback','start':0,'end':1.9,'criterion':'full motion and sound'}],'observations':[{'id':'obs','start':0,'end':2.0,'method':'full-playback','result':'pass','note':'synthetic fixture inspected'}],'limitations':[]}
        self.assertEqual(review_coverage.check(self.root,cov)['status'],'pass')
        reg=self.root/'asset-registry.md';reg.write_text(f'''# Fixture\n\n### V01 - master\n- type: video media\n- role: scene/edit\n- status: accepted\n- file: media/master.mp4\n- SHA-256: {self.sha}\n- derived from:\n''',encoding='utf-8')
        boundary={'registry':'asset-registry.md','asset_id':'V01','source':{'path':'media/master.mp4','sha256':self.sha},'boundary':'exit','time_seconds':1.5,'window_seconds':0.25,'purpose':'continuation','limitations':[]}
        self.assertEqual(boundary_conform.check(self.root,boundary)['status'],'pass')
        analysis=music_cues.analyze(self.root,'media/master.mp4',self.sha,self.audio_index);self.assertEqual(analysis['source']['sha256'],self.sha)
    def test_cli_operation_log(self):
        plan={'purpose':'edit only','lane':'edit-existing-media','edit_clock':{'unit':'seconds','rate':None},'target_edit_span':{'start':0,'end':2},'surface':{'model':'none','service':'local','operation':'edit','input_mode':'media'},'generation_duration':{'kind':'not-applicable','values':[],'minimum':None,'maximum':None,'step':None},'reference_contract':{'maximum':0,'roles':[],'exclusive_role_sets':[]},'units':[{'id':'u','edit':{'start':0,'end':2},'generation_seconds':None,'source_use':None,'playback_rate':1,'pre_handle':0,'post_handle':0,'reference_roles':[],'cues':[],'limitations':[]}],'cost_conditions':[],'assumptions':[],'unresolved':[]}
        p=self.write('plans/schedule.json',plan)
        run=subprocess.run([sys.executable,str(HERE/'generation_schedule.py'),'check','--root',str(self.root),'--plan','plans/schedule.json'],capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        logs=list((self.root/'logs/operations').rglob('operation.json'));self.assertEqual(len(logs),1)
        data=json.loads(logs[0].read_text(encoding='utf-8'));self.assertEqual(data['command'],'generation_schedule.check')

if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    unittest.main(verbosity=2)
