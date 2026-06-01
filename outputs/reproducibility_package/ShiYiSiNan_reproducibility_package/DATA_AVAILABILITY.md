# Data Availability

## Primary dataset: CGMacros

CGMacros is used as the primary public dataset for diet-to-postprandial-glucose modeling.
Raw CGMacros files are not redistributed in this reproducibility package.
Researchers should obtain the dataset from its original public source and place it under the local data directory expected by the preprocessing scripts.

## External validation dataset: OhioT1DM

OhioT1DM is used for lightweight external framework validation.
Raw OhioT1DM XML files are not redistributed in this package.

Expected local placement:

data/external/OhioT1DM/

The external validation script searches recursively for XML files under that folder.

## Credentials

Do not share or commit the following files:

- kaggle.json
- access_token
- .env
- API keys
- passwords
- private credentials

## Reproducibility principle

Another researcher with authorized access to the same public datasets should be able to regenerate meal-level datasets, prediction records, aggregate tables, and figures by following RUN_ORDER.md.
