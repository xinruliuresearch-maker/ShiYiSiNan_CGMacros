# External Dataset Manifest

Created: 2026-06-10

This folder contains external datasets selected to enrich the CGMacros/PPGR precision nutrition project. Full inventory files are stored in:

- `outputs/dataset_search/external_dataset_inventory_2026-06-10.csv`
- `outputs/dataset_search/external_dataset_inventory_2026-06-10.json`
- `outputs/dataset_search/external_database_acquisition_and_integration_plan_2026-06-10.md`

## Downloaded or already present

| Dataset | Folder | Status |
|---|---|---|
| Stanford CGMDB | `Stanford_CGMDB` | Downloaded |
| T1D-UOM longitudinal multimodal T1D dataset | `T1D_UOM_2025` | Downloaded |
| D1NAMO diabetes glucose-food-insulin subset | `D1NAMO_T1D_GlucoseFoodInsulin` | Downloaded |
| ShanghaiT1DM and ShanghaiT2DM | `ShanghaiT1DM_T2DM` | Downloaded |
| Jaeb T1D Nutrition Dataset 2015-2016 | `Jaeb_Nutrition_T1D_2015_2016` | Downloaded |
| Jaeb healthy nondiabetic adults CGM | `Jaeb_CGMND_HealthyAdults_2017` | Downloaded |
| Jaeb healthy young children CGM | `Jaeb_CGMND_HealthyYoungChildren_2021` | Downloaded |
| OhioT1DM 2018/2020 | `OhioT1DM`, `OhioT1DM_raw` | Already present |

## Not downloaded

| Dataset | Reason | Recommended next step |
|---|---|---|
| HUPA-UCM Diabetes Dataset | Public Mendeley Data page was found, but automated file-tree download was blocked by dynamic/API access. | Download manually or with an authenticated browser session, then place files in `HUPA_UCM_Diabetes_2024`. |

## Source links

- Stanford CGMDB: https://cgmdb.stanford.edu/data/
- T1D-UOM: https://doi.org/10.5281/zenodo.15806142
- D1NAMO: https://doi.org/10.5281/zenodo.5651217
- ShanghaiT1DM/T2DM: https://doi.org/10.6084/m9.figshare.21600933.v5
- Jaeb public diabetes datasets: https://public.jaeb.org/datasets/diabetes
- OhioT1DM: https://smarthealth.cs.ohio.edu/OhioT1DM-dataset.html
- HUPA-UCM: https://doi.org/10.17632/3hbcscwz44.1
