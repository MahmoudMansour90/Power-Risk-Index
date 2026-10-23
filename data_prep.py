"""
Builds the static data snapshot the Streamlit app ships with.

Run this locally (with the real pipeline outputs available) whenever the
underlying price panel or forecast is refreshed. It does NOT re-run the
theta backtest/forecast itself -- it takes the already-produced,
already-tested outputs (panel_long and the theta production forecast CSV,
exactly as built by the notebook's CELL 8 and forecasting CELL 3) and
packages them into the compact files app.py actually loads at runtime.

Inputs expected (same shape as the real notebook's in-memory objects):
  - panel_long  : Industrial_Price_Panel_Long_*.xlsx  (FIPS, State,
                  County_Name, Year, Ind_Price_cents_kWh, Confidence_Grade, ...)
  - forecast_df : county_price_forecast_3yr_theta.csv  (FIPS, State,
                  County_Name, Forecast_Year, Forecast_Price_cents_kWh,
                  Lower_CI_cents_kWh, Upper_CI_cents_kWh, CI_Level_%,
                  Expected_MAPE_%, Error_Band_Source)

Outputs (written to ./data/):
  - actual.parquet     : one row per county-year, actual prices
  - forecast.parquet   : one row per county-forecast_year, theta forecast + CI
  - county_lookup.parquet : one row per county (FIPS, State, County_Name) --
                            the full set of counties the app's dropdowns can reach
  - counties_fips.json : county boundary geometry (downloaded once, bundled
                          locally so the deployed app doesn't depend on an
                          external URL at runtime)
"""
import json
import urllib.request
import pandas as pd

PANEL_LONG_PATH = '/home/claude/pipeline_data/Industrial_Price_Panel_Long_2009_2024.xlsx'
FORECAST_CSV_PATH = '/home/claude/forecast_study/county_price_forecast_3yr_theta.csv'
GEOJSON_URL = 'https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json'

OUT_DIR = '/home/claude/streamlit_app/data'


def main():
    panel_long = pd.read_excel(PANEL_LONG_PATH)
    panel_long['FIPS'] = panel_long['FIPS'].astype(str).str.extract(r'(\d+)')[0].str.zfill(5)

    forecast_df = pd.read_csv(FORECAST_CSV_PATH, dtype={'FIPS': str})

    actual = panel_long[['FIPS', 'State', 'County_Name', 'Year',
                          'Ind_Price_cents_kWh', 'Confidence_Grade', 'Total_MWh']].copy()
    actual = actual.rename(columns={'Ind_Price_cents_kWh': 'Price_cents_kWh'})

    forecast = forecast_df[['FIPS', 'State', 'County_Name', 'Forecast_Year', 'Years_Ahead',
                             'Forecast_Price_cents_kWh', 'Lower_CI_cents_kWh', 'Upper_CI_cents_kWh',
                             'CI_Level_%', 'Expected_MAPE_%', 'Error_Band_Source']].copy()
    forecast = forecast.rename(columns={'Forecast_Price_cents_kWh': 'Price_cents_kWh',
                                         'Forecast_Year': 'Year'})

    county_lookup = (actual.sort_values('Year').drop_duplicates('FIPS', keep='last')
                     [['FIPS', 'State', 'County_Name']]
                     .sort_values(['State', 'County_Name']).reset_index(drop=True))

    actual.to_parquet(f'{OUT_DIR}/actual.parquet', index=False)
    forecast.to_parquet(f'{OUT_DIR}/forecast.parquet', index=False)
    county_lookup.to_parquet(f'{OUT_DIR}/county_lookup.parquet', index=False)

    print(f"actual.parquet:        {len(actual):,} rows, {actual['FIPS'].nunique():,} counties")
    print(f"forecast.parquet:      {len(forecast):,} rows")
    print(f"county_lookup.parquet: {len(county_lookup):,} counties")

    with urllib.request.urlopen(GEOJSON_URL, timeout=30) as r:
        geo = json.loads(r.read().decode())
    with open(f'{OUT_DIR}/counties_fips.json', 'w') as f:
        json.dump(geo, f)
    print(f"counties_fips.json:    {len(geo['features']):,} county features")


if __name__ == '__main__':
    main()
