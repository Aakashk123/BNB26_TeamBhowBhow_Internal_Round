"""Reproducible calibration on procedural fixtures. Similarity remains candidate-only."""
import io
import json
import random
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, PngImagePlugin
import cv2
import imagehash
import yaml
from app.core.hashing import sha256
from app.core.pixelhash import pixel_sha256
from app.core.perceptual import hashes, distance

ROOT=Path(__file__).resolve().parents[1]


def generate(index, size=256):
    rng=np.random.default_rng(index+8042)
    pixels=np.uint8(np.clip(rng.normal(125, 38, (size,size,3)),0,255))
    image=Image.fromarray(pixels).filter(ImageFilter.GaussianBlur(1))
    draw=ImageDraw.Draw(image)
    for _ in range(15):
        x,y=map(int,rng.integers(0,size-50,2)); w,h=map(int,rng.integers(15,100,2))
        color=tuple(map(int,rng.integers(0,255,3)))
        if rng.random()<.5:draw.rectangle((x,y,min(size,x+w),min(size,y+h)),fill=color)
        else:draw.ellipse((x,y,min(size,x+w),min(size,y+h)),fill=color)
    return image


def encoded(image, fmt="PNG", **kwargs):
    stream=io.BytesIO();image.save(stream,format=fmt,**kwargs)
    return stream.getvalue()


def transforms(image):
    for q in (95,75,50):
        yield f"jpeg-{q}", Image.open(io.BytesIO(encoded(image,"JPEG",quality=q))).convert("RGB")
    for lossless in (True,False):
        yield f"webp-{lossless}",Image.open(io.BytesIO(encoded(image,"WEBP",lossless=lossless))).convert("RGB")
    for scale in (.25,.5,2):yield f"resize-{scale}",image.resize((int(image.width*scale),int(image.height*scale)))
    for crop in (.05,.15,.30):
        n=int(image.width*crop/2);yield f"crop-{crop}",image.crop((n,n,image.width-n,image.height-n))
    yield "rotate90",image.transpose(Image.Transpose.ROTATE_90)
    for blur in (.5,1,2,5,10):yield f"blur-{blur}",image.filter(ImageFilter.GaussianBlur(blur))
    for factor in (.85,1.15):
        yield f"brightness-{factor}",ImageEnhance.Brightness(image).enhance(factor)
        yield f"contrast-{factor}",ImageEnhance.Contrast(image).enhance(factor)
    yield "metadata-strip",image.copy()


def main():
    start=time.perf_counter();rng=random.Random(415)
    bases=[generate(i) for i in range(300)]
    fingerprints=[{**hashes(i),"a":str(imagehash.average_hash(i))} for i in bases]
    positive=[];per_transform={};file_hits=0;pixel_hits=0;individual={k:[] for k in ("a","d","p","w")};negative_individual={k:[] for k in individual}
    orb=cv2.ORB_create(nfeatures=128);matcher=cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    descriptors=[orb.detectAndCompute(np.array(i.convert('L')),None)[1] for i in bases]
    orb_positive=[];hash_ms=[]
    for i,image in enumerate(bases):
        metadata=PngImagePlugin.PngInfo();metadata.add_text("fixture","SIMULATED procedural fixture");raw=encoded(image,pnginfo=metadata); pixel=pixel_sha256(image)
        for name, transformed in transforms(image):
            started=time.perf_counter();fp={**hashes(transformed),"a":str(imagehash.average_hash(transformed))};hash_ms.append((time.perf_counter()-started)*1000)
            d=sorted(distance(fingerprints[i][k],fp[k]) for k in ('d','p','w'))[1]
            positive.append((i,name,d));per_transform.setdefault(name,[]).append(d)
            for k in individual:individual[k].append(distance(fingerprints[i][k],fp[k]))
            raw_output=encoded(image,"WEBP",lossless=name=="webp-True") if name.startswith("webp") else encoded(image,"JPEG",quality=int(name.split("-")[1])) if name.startswith("jpeg") else encoded(transformed)
            file_hits+=sha256(raw)==sha256(raw_output);pixel_hits+=pixel==pixel_sha256(transformed)
            desc=orb.detectAndCompute(np.array(transformed.resize((256,256)).convert('L')),None)[1]
            matches=matcher.match(descriptors[i],desc) if descriptors[i] is not None and desc is not None else []
            orb_positive.append(sum(m.distance<=40 for m in matches))
    negatives=[];orb_negatives=[]
    for _ in range(3000):
        a,b=rng.sample(range(300),2)
        for k in individual:negative_individual[k].append(distance(fingerprints[a][k],fingerprints[b][k]))
        negatives.append(sorted(distance(fingerprints[a][k],fingerprints[b][k]) for k in ('d','p','w'))[1])
        matches=matcher.match(descriptors[a],descriptors[b]) if descriptors[a] is not None and descriptors[b] is not None else []
        orb_negatives.append(sum(m.distance<=40 for m in matches))
    threshold=max(t for t in range(65) if sum(d<=t for d in negatives[:1500])/1500<=.001)
    orb_threshold=min(t for t in range(129) if sum(d>=t for d in orb_negatives[:1500])/1500<=.001)
    count=len(positive)
    single={}
    for k in individual:
        cutoff=max(t for t in range(65) if sum(d<=t for d in negative_individual[k][:1500])/1500<=.001)
        single[k]={"threshold":cutoff,"recall":sum(d<=cutoff for d in individual[k])/count,"held_out_fpr":sum(d<=cutoff for d in negative_individual[k][1500:])/1500}
    result={"individual_hashes":single,"base_images":300,"transform_pairs":count,"negative_pairs":3000,"calibration_negatives":1500,"held_out_negatives":1500,
            "candidate_threshold":threshold,"held_out_false_positive_rate":sum(d<=threshold for d in negatives[1500:])/1500,
            "candidate_recall":sum(d<=threshold for _,_,d in positive)/count,
            "file_sha256_recall":file_hits/count,"pixel_sha256_recall":pixel_hits/count,
            "median_hash_ms":float(np.median(hash_ms)),"total_seconds":time.perf_counter()-start,
            "orb_min_matches":orb_threshold,"orb_recall":sum(d>=orb_threshold for d in orb_positive)/count,
            "orb_held_out_fpr":sum(d>=orb_threshold for d in orb_negatives[1500:])/1500,
            "per_transform_recall":{name:sum(d<=threshold for d in ds)/len(ds) for name,ds in per_transform.items()},
            "watermark":{"enabled":False,"reason":"No statistically adequate 1e-6 FPR validation; not trusted or shipped enabled"},
            "limitations":"Procedural set; not representative of all real images. Point-estimate FPR is not a population guarantee. Rotation and heavy crops/degradation can fail."}
    (ROOT/'bench/results/binding.json').write_text(json.dumps(result,indent=2))
    path=ROOT/'config/trust_policy.yaml';policy=yaml.safe_load(path.read_text());policy['candidate_threshold']=threshold
    policy['derivation_threshold']=int(np.quantile([d for _,name,d in positive if name.startswith(('resize','jpeg','webp','crop'))],.995))
    path.write_text(yaml.safe_dump(policy,sort_keys=False))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
