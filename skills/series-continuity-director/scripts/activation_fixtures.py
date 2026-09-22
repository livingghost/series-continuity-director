"""Construct synthetic public reference artifacts for offline tests and examples."""
from pathlib import Path
import execution_contract as c
from protocol_contract import finalize_artifact, validate_artifact


def fixture(root: Path, count: int = 2, *, board: bool = False):
    from PIL import Image
    root.mkdir(parents=True,exist_ok=True);references=[];selectors={};uses=[];inputs=[]
    for i in range(count):
        ident=f'SYN-BIND-{i+1}';character=f'SYN-CHAR-{i+1}'
        path=root/f'image-{i+1}.png'
        Image.new('RGB',(8,8),(i*50+10,40,90)).save(path)
        source={'kind':'supplied-file','reference_id':f'synthetic-image-{i+1}','resolved_path':path.name,'media_type':'image/png','sha256':c.digest(path.read_bytes())}
        transport={'resolved_path':path.name,'media_type':'image/png','sha256':source['sha256'],'derivation':{'mode':'direct'}}
        row={'binding_id':ident,'role':'identity','source':source,'transport':transport,
             'authority':{'controls':['declared identity'],'must_not_control':['background']},
             'covers':['identity'],'intended_influence':['identity'],'review_dimensions':['identity'],
             'unsupported_or_occluded_state':[],'unsupported_assumptions':[]}
        state=finalize_artifact({'artifact_type':'state-aware-reference-binding','binding_id':ident,'role':'identity','source':source,
            'character_id':character,'identity_contract_sha256':'1'*64,'era_contract_sha256':None,'appearance_variant_sha256':None,
            'state_snapshot_sha256':None,'effective_story_range':{'from_order':1,'to_order':100},'visibly_supported_state':['identity'],
            'unsupported_or_occluded_state':[],'intended_influence':['identity'],'unsupported_assumptions':[],'review_dimensions':['identity'],
            'fallback_if_unstable':'Inspect the synthetic source.','superseded_for_future_scenes':False})
        report=validate_artifact(state)
        if not report['ok']:raise ValueError(str(report['errors']))
        f=root/f'binding-{i+1}.json';f.write_bytes(c.encoded(state));selectors[ident]={'path':f.name,'sha256':c.digest(f.read_bytes())}
        references.append(row);uses.append({'reference':ident,'settles':['identity']});inputs.append({'path':path.name,'role':'reference','request_key':'referenceImages'})
    composite=None
    if board:
        canvas=Image.new('RGB',(8*count,8),'white');panels=[]
        for i,row in enumerate(references):
            with Image.open(root/row['transport']['resolved_path']) as image:canvas.paste(image,(8*i,0))
            panels.append({'semantic_role':row['role'],'source_sha256':row['source']['sha256'],'transport_sha256':row['transport']['sha256'],'box':{'x':8*i,'y':0,'width':8,'height':8}})
        path=root/'board.png';canvas.save(path);canvas.close()
        composite={'resolved_path':path.name,'media_type':'image/png','sha256':c.digest(path.read_bytes()),'panels':panels}
        inputs=[{'path':path.name,'role':'reference','request_key':'referenceImages'}]
    package=finalize_artifact({'artifact_type':'prepared-reference-set','set_id':'PRS-SYNTHETIC','transport_mode':'single-board' if board else 'multi-image',
       'target_model':'synthetic-target','reference_selection':None,'reference_selection_sha256':None,'reference_use_plan':None,'reference_use_plan_sha256':None,
       'surface_lighting_plan_sha256':None,'zero_reference_reason':None,'reference_preamble':'Synthetic explicitly scoped references.',
       'prompt_artifacts':[],'selected_references':references,'single_board':composite})
    report=validate_artifact(package)
    if not report['ok']:raise ValueError(str(report['errors']))
    (root/'package.json').write_bytes(c.encoded(package))
    activation={'activation_id':'SYN-ACTIVATION','package':'package.json','story_point':10,'uses':uses,'state_bindings':selectors}
    (root/'activation.json').write_bytes(c.encoded(activation))
    return package,activation,inputs
