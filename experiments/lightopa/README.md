# LightOPA Tiny Baseline

This experiment trains a small 4-channel CNN as a lightweight OPA scoring baseline.
It is a model-level comparison point, not a replacement for the main SimOPA scorer.

Input:

```text
composite RGB image + foreground mask -> 4 x 128 x 128 tensor
```

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\lightopa\train_lightopa_tiny.py
```

Outputs:

```text
report/tables/lightopa_tiny_metrics.csv
report/logs/lightopa_tiny_training.txt
models/lightopa/tiny_lightopa_smoke.pth
```

Current result:

- Model: `tiny-lightopa-cnn-v1`
- Parameters: `79,425`
- Training subset: 2,000 balanced OPA train samples
- Validation subset: 500 balanced OPA test samples
- Best epoch: `3`
- Validation accuracy at threshold 0.5: `0.65`
- ROC-AUC: `0.6761`
- Best-threshold balanced accuracy: `0.664`
- Average validation inference time: `12.36 ms/sample`

Interpretation:

- This gives SmartPlace a real trained lightweight baseline, which strengthens the model-side story beyond `simopa-lite` candidate-budget serving.
- The tiny CNN is intentionally small and only trained on a small subset, so its quality is not expected to match SimOPA.
- The stable project line remains `simopa-worker`; this experiment is evidence for a future stronger LightOPA model such as ResNet18 or MobileNet.
