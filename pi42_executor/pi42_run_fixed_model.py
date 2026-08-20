#!/usr/bin/env python3
import json,re,sys,time,urllib.request
from pathlib import Path

LABELS=("true","false","unknown","contested")

def parse_label(text):
    s=str(text).strip().lower()
    if s in LABELS:
        return s
    m=re.search(r'(?<![a-z])(true|false|unknown|contested)(?![a-z])',s)
    return m.group(1) if m else "invalid"

def post(url,payload,tries=4):
    data=json.dumps(payload).encode()
    last=None
    for i in range(tries):
        try:
            req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=180) as r:
                return json.loads(r.read())
        except Exception as e:
            last=e; time.sleep(2*(i+1))
    raise last

def main():
    if len(sys.argv)!=3:
        raise SystemExit('usage: pi42_run_fixed_model.py prompts.jsonl output.jsonl')
    inp=Path(sys.argv[1]); outp=Path(sys.argv[2]); outp.parent.mkdir(parents=True,exist_ok=True)
    rows=[json.loads(x) for x in inp.read_text().splitlines() if x.strip()]
    results=[]
    for idx,row in enumerate(rows):
        arms={}
        for arm in ('RAW','G1','G3','G5C'):
            payload={
              'model':'pi42-smollm2-360m-instruct-q4km',
              'messages':[{'role':'user','content':row['prompts'][arm]}],
              'temperature':0.0,
              'seed':4242,
              'max_tokens':8,
              'stream':False
            }
            js=post('http://127.0.0.1:9090/v1/chat/completions',payload)
            text=js['choices'][0]['message']['content']
            arms[arm]={'prediction':parse_label(text),'raw_output':text}
        results.append({'case_id':row['case_id'],'aggregate':row.get('aggregate',True),'proof_depth':row.get('proof_depth',-1),'arms':arms})
        if (idx+1)%10==0 or idx+1==len(rows): print(f'scored={idx+1}/{len(rows)}',flush=True)
    with outp.open('w') as f:
        for r in results:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
    import hashlib
    sha=hashlib.sha256(outp.read_bytes()).hexdigest()
    summary={'rows':len(results),'calls':len(results)*4,'prediction_sha256':sha,'temperature':0,'seed':4242,'max_tokens':8,'gold_labels_available_to_executor':False}
    (outp.parent/'executor_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print('PI42_MODEL_EXECUTOR='+json.dumps(summary,sort_keys=True),flush=True)
if __name__=='__main__':main()
