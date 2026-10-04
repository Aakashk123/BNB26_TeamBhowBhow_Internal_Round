import json
from pathlib import Path
import numpy as np
from PIL import ImageFilter
from app.core.watermark import embed,score
from bench.binding_bench import generate,encoded
from PIL import Image
import io


def main():
    key=b'PUBLIC-EXPERIMENT-KEY-DO-NOT-REUSE';psnr=[];scores=[];negative=[]
    for i in range(100):
        base=generate(i);marked=embed(base,key)
        mse=float(np.mean((np.asarray(base,dtype=float)-np.asarray(marked,dtype=float))**2))
        psnr.append(10*np.log10(255**2/mse))
        transformed=Image.open(io.BytesIO(encoded(marked,'JPEG',quality=75))).resize((128,128))
        scores.append(score(transformed,key));negative.append(score(generate(i+1000),key))
    result={'experimental':True,'enabled':False,'positive_pairs':100,'negative_pairs':100,'mean_psnr_db':float(np.mean(psnr)),
            'minimum_positive_score':float(min(scores)),'maximum_negative_score':float(max(negative)),
            'decision':'REJECT production enablement: sample size cannot establish FPR <= 1e-6; no detector thresholds promoted'}
    root=Path(__file__).resolve().parents[1];(root/'bench/results/watermark.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':main()
