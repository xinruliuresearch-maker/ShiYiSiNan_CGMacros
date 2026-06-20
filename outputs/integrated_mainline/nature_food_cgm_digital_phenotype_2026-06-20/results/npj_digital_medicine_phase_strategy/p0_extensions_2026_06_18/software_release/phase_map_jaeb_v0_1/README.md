# Phase-map JAEB summary v0.1

Research software bundle for assigning a CGM summary window to a locked JAEB
glycaemic phase-map digital phenotype.

## Intended use

This package is for retrospective research, reproducibility checks, and
silent-mode workflow evaluation. It is not a standalone clinical decision
system and must not autonomously change therapy.

## Quick start

```python
import pandas as pd
from phase_map import assign_phase

df = pd.read_csv("toy_data/toy_input.csv")
assigned = assign_phase(df)
print(assigned[["participant_id", "phase_id", "phase_label_en"]])
```

## Test

```bash
python -m unittest discover -s tests
```

## Contents

- `phase_map/`: minimal assignment package.
- `schemas/`: input and output schemas.
- `toy_data/`: toy input and expected output fixtures.
- `scripts/reproduce_figures.py`: helper to rerun manuscript figure scripts from the repository root.
- `environment.yml` and `requirements.txt`: lightweight environment locks.
