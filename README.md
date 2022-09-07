# Correlation flow
===================

In your `.bashrc` please do:
```
export PATH="/path/to/correlation_flow/bin":$PATH
export PATH="/path/to/correlation_flow/finta_test_retest_evaluation:$PATH"
```

Create a new virtualenv with `python3.8`:
```
virtualenv env --python=python3.8
pip install -r requirements.txt
```

Please clone [tractometry_flow-minimal](https://github.com/fdumais/tractometry_flow-minimal) and [registration_flow](https://github.com/scil-vital/registration_flow)

Launch the command:

```
finta_test_retest.sh -i inputs/ -t /path/to/tractometry_flow-minimal -r /path/to/registration_flow -c /path/to/correlation_flow -s config_tr_example.json -b config_rbx_atlas_v10.json -o out_folder -n NUM_PROCESSES -a /path/to/mni_masked.nii.gz
```

Requirements
------------

* https://github.com/fdumais/tractometry_flow-minimal
* https://github.com/scil-vital/registration_flow


