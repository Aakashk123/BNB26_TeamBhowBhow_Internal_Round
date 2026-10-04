# Benchmark results

Actual measured output is stored in `bench/results/`. Thresholds are calibrated from 1,500 negative pairs and evaluated against a separate 1,500 negative pairs. All base images are procedural fixtures; they are not a universal image distribution.

## Binding experiment

300 originals; 6600 transformations; 3,000 negative pairs. Median four-hash computation: 4.65 ms/image. Runtime: 176.78 seconds.

| Transform | Candidate recall |
|---|---:|
| jpeg-95 | 100.00% |
| jpeg-75 | 100.00% |
| jpeg-50 | 100.00% |
| webp-True | 100.00% |
| webp-False | 100.00% |
| resize-0.25 | 100.00% |
| resize-0.5 | 100.00% |
| resize-2 | 100.00% |
| crop-0.05 | 100.00% |
| crop-0.15 | 100.00% |
| crop-0.3 | 9.00% |
| rotate90 | 0.00% |
| blur-0.5 | 100.00% |
| blur-1 | 100.00% |
| blur-2 | 100.00% |
| blur-5 | 100.00% |
| blur-10 | 100.00% |
| brightness-0.85 | 100.00% |
| contrast-0.85 | 100.00% |
| brightness-1.15 | 100.00% |
| contrast-1.15 | 100.00% |
| metadata-strip | 100.00% |

File SHA-256 recall: 0.00%. Canonical pixel SHA-256 recall: 9.09%. These low transformation recall figures are expected: cryptographic hashes are exact bindings, not approximate recovery methods.

Median d/p/w candidate cutoff: 19 Hamming bits. Held-out false positives: 0.00% observed. Zero observed false positives in 1,500 trials is not proof of zero population error, nor a rigorous upper bound of 0.1%.

## Negative results

90° rotation failed. A 30% crop had poor recall. ORB exceeded the target held-out FPR at its calibrated threshold. Surviving evidence, not recovered appearance, must determine the provenance result. Progressive blur at sigma 0.5, 1, 2, 5 and 10 is included; a procedural image remaining similar under blur does not establish authentic origin.

## Experimental watermark

Mean PSNR: 44.01 dB. 100 positive pairs after JPEG q75 and 50% resize; 100 negatives. The trial cannot establish FPR <= 1e-6. No threshold is promoted to production and no watermark can create a cryptographic binding.

## Origin evidence

A deliberately naive approved-signature-only baseline classifies 7/20 cases correctly. The full engine classifies 20/20. The authorized signer who lies without corroboration is incorrectly trusted by the baseline but remains SELF_ASSERTED under the full policy. These are synthetic adversarial evidence cases, not a measured real-world fraud detection rate.

## Graph performance

A synthetic 200-node, 199-edge unverified graph rendered in 803 ms and opened the evidence drawer in 153 ms in the recorded headless Chromium test. This fixture measures rendering only and does not represent authenticated provenance. Comparative D3/Cytoscape timings were not collected.
