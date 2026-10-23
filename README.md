# Power Risk Index for Data Center Construction Planning

MOCCI -- interactive county-level Cost pillar explorer, built on real EIA-861-derived
industrial electricity prices (2001-2024) and a theta-model 3-year forecast (2025-2027)
with a real empirical prediction interval. Reliability, Availability, and a composite
Power Risk Index are planned but not included yet -- no placeholder or synthetic data
is shown for them.

## What's in this folder

- `app.py` -- the Streamlit app
- `data_prep.py` -- regenerates the files in `data/` from the pipeline's real outputs
  (run this again whenever the underlying price panel or forecast is refreshed)
- `data/` -- the static data snapshot the app actually loads (parquet files + county
  boundary geometry, bundled locally so the deployed app doesn't depend on an external
  URL at runtime)
- `assets/mocci_logo.png` -- the MOCCI logo shown in the header
- `.streamlit/secrets.toml.example` -- template for the password secret (see below)
- `requirements.txt`

## Password protection

The app is gated by a single shared password, checked against `st.secrets["app_password"]`.
The real password is never stored in this folder or in source control -- only
`secrets.toml.example` (a template) is included.

**Local run:** copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and put
a real password in it. That file is already in `.gitignore`, so it won't get committed.

**Streamlit Community Cloud:** you do not need a `secrets.toml` file in the repo at all.
After deploying, go to the app's **Settings -> Secrets** in the Streamlit dashboard and
paste:
```
app_password = "your real password here"
```
Save, and the app will pick it up automatically (no redeploy needed).

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository and push everything in this folder to it (the `data/`
   folder, logo, and all).
2. Go to https://share.streamlit.io/ and connect your GitHub account.
3. Select the repository, branch, and `app.py` as the main file, then deploy.
4. Set the password in the app's Secrets (see above) before sharing the link.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Updating the data later

When the forecast or price panel is refreshed (e.g. after a new EIA data year becomes
available), re-run the notebook's pipeline to produce an updated
`county_price_forecast_3yr_theta.csv` and panel export, point `data_prep.py` at the new
files, and re-run it:

```
python3 data_prep.py
```

Then commit the updated `data/*.parquet` files and push -- Streamlit Community Cloud
redeploys automatically on a new commit. (A fully automatic EIA-refresh pipeline, using
only the EIA's final/approved data rather than preliminary releases, is a separate,
not-yet-built feature.)
