# SaMa

The first working feature is candidate-profile validation. It has no runtime
dependencies and is implemented in `app/profile/model.py`.

Run the test suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

The synthetic example payload is at `data/examples/candidate-profile.json`.
