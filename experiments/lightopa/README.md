# LightOPA Lightweight Baselines

This directory trains small 4-channel CNNs as lightweight OPA scoring baselines.
They are model-level comparison points, not replacements for the main SimOPA scorer.

Input:

```text
composite RGB image + foreground mask -> 4 x 128 x 128 tensor
```

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\lightopa\train_lightopa_tiny.py
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\lightopa\train_lightopa_residual.py
python experiments\lightopa\compare_lightopa_models.py
```

Outputs:

```text
report/tables/lightopa_tiny_metrics.csv
report/tables/lightopa_residual_metrics.csv
report/tables/lightopa_model_comparison.csv
report/logs/lightopa_tiny_training.txt
report/logs/lightopa_residual_training.txt
report/logs/lightopa_model_comparison.txt
models/lightopa/tiny_lightopa_smoke.pth
models/lightopa/residual_lightopa_smoke.pth
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
- Model: `residual-lightopa-cnn-v1`
- Parameters: `1,113,377`
- Training subset: 3,000 balanced OPA train samples
- Validation subset: 600 balanced OPA test samples
- Best epoch: `2`
- Validation accuracy at threshold 0.5: `0.6717`
- ROC-AUC: `0.7084`
- Best-threshold balanced accuracy: `0.6817`
- Average validation inference time: `11.50 ms/sample`

Interpretation:

- This gives SmartPlace real trained lightweight baselines, which strengthens the model-side story beyond `simopa-lite` candidate-budget serving.
- The residual baseline improves over the tiny baseline on this validation subset: accuracy rises from `0.65` to `0.6717`, and ROC-AUC rises from `0.6761` to `0.7084`.
- Both models are intentionally small and trained on small subsets, so their quality is not expected to match SimOPA.
- The stable project line remains `simopa-worker`; these experiments are evidence for future stronger LightOPA models such as ResNet18 or MobileNet.
