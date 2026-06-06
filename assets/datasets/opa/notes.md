# OPA Dataset Notes

Dataset: Object Placement Assessment Dataset (OPA)

Purpose:

- Provide reference samples for object-placement scoring.
- Support baseline scoring, RGB vs RGB+mask comparison, and small-subset validation.

Local layout:

```text
assets/datasets/opa/
|-- raw/          # ignored, original downloaded data
|-- downloads/    # ignored, archives or temporary downloads
|-- samples/      # small selected examples if needed
`-- splits/       # small CSV split/index files
```

To fill in after download:

| Field | Value |
|---|---|
| Source URL | https://github.com/bcmi/Object-Placement-Assessment-Dataset-OPA |
| Download date | 2026-06-06 |
| Commit/version | `f0743e9` local shallow clone in `external/Object-Placement-Assessment-Dataset-OPA` |
| Contains composite images | Yes, in full `OPA.rar` dataset |
| Contains masks | Yes, masks are stored with `mask_` prefix |
| Contains labels/scores | Yes, labels are encoded in CSVs and composite filenames |
| License/citation | Cite OPA paper from repository README |

## Local Preparation Status

Reference repositories:

| Repository | Local path | Commit |
|---|---|---|
| libcom | `external/libcom` | `fe5b5b1` |
| Object-Placement-Assessment-Dataset-OPA | `external/Object-Placement-Assessment-Dataset-OPA` | `f0743e9` |
| TopNet-Object-Placement | `external/TopNet-Object-Placement` | `b167473` |

Weights:

| File | Local path | Size | SHA256 |
|---|---|---:|---|
| OPA_checkpoints.zip | `models/opa/OPA_checkpoints.zip` | 83,074,662 bytes | `0E1FBF473D0678CCFBC9F6A0F97DA52D6C6E03B641B874032C3D10B61BE901AF` |
| simopa.pth | `models/opa/OPA_checkpoints/checkpoints/simopa.pth` | 44,801,231 bytes | `882CBB6607D43D8D17DAFBA5B37596F5CD1B92E01D67A0CF0044E793D98D68C7` |
| simopa_ext.pth | `models/opa/OPA_checkpoints/checkpoints/simopa_ext.pth` | 44,805,709 bytes | `BF798E11DC053A272F49D09B0070D249A6D8CAC1AB2E656F4C300D107843D90E` |

The SimOPA weights have also been copied to:

```text
external/Object-Placement-Assessment-Dataset-OPA/eval_opascore/checkpoints/
models/libcom/pretrained_models/SimOPA.pth
```

Implementation note:

- `libcom` is cloned locally and has an `OPAScoreModel` wrapper.
- Importing the libcom top-level package pulls many non-mainline modules such as harmonization and diffusion dependencies.
- For the first stable baseline, SmartPlace uses the OPA repository's direct `eval_opascore/simopa.py` model class through `experiments/opa_baseline/run_simopa_smoke.py`.
- This keeps the model evidence focused on OPA scoring and avoids unnecessary dependency risk.

Full dataset:

- User downloaded and extracted the full OPA dataset to `assets/datasets/opa/raw/new_OPA`.
- Local structure contains `background/`, `foreground/`, `composite/`, `train_set.csv`, and `test_set.csv`.
- File count: 156,896 files, including 156,894 `.jpg` files and 2 CSV files.
- `test_set.csv` and `train_set.csv` use fields: `fg_id,bg_id,position,scale,label,img_name,mask_name`.

Smoke audit:

- Script: `experiments/opa_baseline/audit_opa_dataset.py`
- Split: `test`
- Output: `assets/datasets/opa/splits/smoke_100.csv`
- Audit table: `report/tables/opa_sample_audit.csv`
- Result: 100 usable samples, 50 positive and 50 negative.
