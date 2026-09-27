#!/usr/bin/env python3
"""Expand an explicit production purpose into optional SCD stages without inventing story content."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import execution_contract as c
from protocol_contract import validate_against_schema
from operation_log import operation
ROOT=Path(__file__).resolve().parents[1]
RECIPES={
 'dialogue-scene':{'recommended':['scene-persona','story-context','performance','review-coverage'],'optional':['generation-schedule','caption-track','delivery-conform']},
 'continuous-performance':{'recommended':['story-context','performance','generation-schedule','boundary-conform','review-coverage'],'optional':['caption-track','audio-master','delivery-conform']},
 'music-led-sequence':{'recommended':['generation-schedule','music-cues','audio-master','review-coverage','delivery-conform'],'optional':['caption-track','boundary-conform']},
 'comic-page':{'recommended':['story-context','board-layout','review-coverage'],'optional':['caption-track','delivery-conform']},
 'product-film':{'recommended':['generation-schedule','review-coverage','delivery-conform'],'optional':['music-cues','audio-master','caption-track','board-layout']},
 'custom':{'recommended':[],'optional':['generation-schedule','music-cues','audio-master','caption-track','delivery-conform','boundary-conform','board-layout','blocking-preview','review-coverage']}
}
def plan(value):
    schema=c.load(ROOT/'schemas/authoring/production-recipe.schema.json');errors=validate_against_schema(value,schema)
    if errors:raise ValueError('production recipe: '+'; '.join(errors))
    base=RECIPES[value['purpose']]
    requested=set(value['optional_stages']);features=list(dict.fromkeys(base['recommended']+[x for x in base['optional'] if x in requested]))
    # Medium removes impossible defaults; it never invents required media.
    if value['medium']=='text':features=[x for x in features if x not in {'generation-schedule','audio-master','delivery-conform','boundary-conform','music-cues','board-layout','blocking-preview'}]
    return {'purpose':value['purpose'],'medium':value['medium'],'features':features,'requirements':value['requirements'],'decisions':value['decisions'],'deliverables':value['deliverables'],
            'scope':'Recipe stages are routing suggestions. They do not create a cast, plot turn, approval, canon event, or paid action.'}
def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['plan']);p.add_argument('--root',type=Path,required=True);p.add_argument('--recipe',required=True);a=p.parse_args();root=a.root.absolute()
    try:
        with operation('production_recipe.plan',root=root,arguments=vars(a)) as log:
            result=plan(c.load(c.local(root,a.recipe)));log.event('recipe_planned',features=result['features']);print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except c.EXPECTED_ERRORS as exc:print(json.dumps(c.failure(exc),ensure_ascii=False));return 1
if __name__=='__main__':
    import stdio_utf8;stdio_utf8.configure();raise SystemExit(main())
