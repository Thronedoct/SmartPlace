# Packaged Demo Cases

This directory contains the five built-in Web demo cases used by SmartPlace:

```text
opa_test_001
opa_test_002
opa_test_006
opa_test_052
opa_test_059
```

Each case keeps only three small files:

```text
background.jpg
foreground.jpg
mask.jpg
```

These files are copied from the local OPA dataset so the Web demo can load built-in cases without requiring the full `assets/datasets/opa/raw/new_OPA/` dataset. The full raw dataset is still needed only for rerunning large OPA evaluations or retraining LightOPA.
