"""Build unedited reference/app pairs; no automatic visual PASS or masking."""
import argparse,base64,hashlib,html,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--capture-root',type=Path,default=ROOT/'test-results');parser.add_argument('--output',type=Path,default=ROOT/'.tmp/continuum-comparisons');args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True);(out/'references').mkdir(exist_ok=True);(out/'actual').mkdir(exist_ok=True)
    design=ROOT/'docs/design/continuum-v1';manifest=json.loads((design/'asset-manifest.json').read_text());assets={a['id']:a for a in manifest['assets']}
    for identity,a in assets.items():
        encoded=re.search(r'data:image/png;base64,([^"\s]+)',(design/a['path']).read_text()).group(1);data=base64.b64decode(encoded)
        assert len(data)==a['bytes'] and hashlib.sha256(data).hexdigest()==a['sha256']
        (out/'references'/f'{identity}.png').write_bytes(data)
    rows=[]
    for surface in ('local','pages'):
        for identity,name,region in [('UI-01','home-1448-A','Home/header/navigation/composer'),('UI-02','evidence-1448','Reading with connected evidence'),('UI-03','source-1448-scrolled','Source drill-in and return'),('M-01','home-1448-A','Orb derivative in Home'),('M-02','home-1448-B','Receiver derivative in Home')]:
            matches=sorted(p for p in args.capture_root.glob(f'continuum-visual-{surface}*/{name}.png'))
            row={'reference_id':identity,'surface':surface,'region':region,'expected':'Adopted reference at original dimensions; supported synthetic semantics only','actual':'Capture available' if matches else 'MISSING_CAPTURE','severity':'REQUIRES_HUMAN_VISUAL_REVIEW','cause':'Different original synthetic prose and supported feature set; geometric companion derivative','fallback':'No appearance PASS inferred from tests or pixel score','accepted_by':None,'reference':f'references/{identity}.png','actual_path':None}
            if matches:
                dest=f'actual/{surface}-{identity}.png';shutil.copyfile(matches[0],out/dest);row.update(actual_path=dest,actual_sha256=hashlib.sha256((out/dest).read_bytes()).hexdigest())
            rows.append(row)
    (out/'comparison-index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    body=['<!doctype html><meta charset="utf-8"><title>Continuum actual/reference review</title><style>body{font:16px/1.6 system-ui;margin:24px;background:#eef3fc;color:#172448}.pair{display:flex;gap:20px;overflow:auto;padding:16px;background:white}figure{margin:0;flex:none}img{display:block;max-width:none}h2{margin-top:48px}p{max-width:1000px}</style><h1>Unedited actual browser / unchanged approved reference</h1><p>Original dimensions, no masks or image replacement. Scroll horizontally to inspect each pair. These captures show provider-free original synthetic fixtures. Passing tests, screenshots and image preference do not prove HCL efficacy. Human region-level review remains required; missing captures remain unverified.</p>']
    for row in rows:
        body.append(f'<h2>{html.escape(row["surface"]+" / "+row["reference_id"]+" / "+row["region"])}</h2><div class="pair"><figure><figcaption>Unchanged approved reference</figcaption><img src="{row["reference"]}"></figure>')
        body.append(f'<figure><figcaption>Actual app capture</figcaption><img src="{row["actual_path"]}"></figure>' if row['actual_path'] else '<p>MISSING CAPTURE / NOT VERIFIED</p>');body.append('</div>')
    (out/'index.html').write_text(''.join(body));print(json.dumps({'pairs':len(rows),'available':sum(bool(r['actual_path']) for r in rows),'visual_acceptance':'REQUIRES_HUMAN_REVIEW'}))
if __name__=='__main__':main()
