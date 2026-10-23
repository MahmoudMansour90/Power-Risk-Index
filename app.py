"""
Power Risk Index for Data Center Construction Planning
MOCCI -- Cost pillar (industrial electricity price), real data only.

Built from the real, tested pipeline: EIA-861-derived county industrial
electricity prices (2001-2024) and a theta-model 3-year forecast
(2025-2027) with a real empirical 68% prediction interval from the actual
backtest error distribution -- not an assumed symmetric band, not a
synthetic placeholder. Reliability and Availability pillars, and a
composite Power Risk Index, are not included yet: only Cost is backed by
validated research data so far.
"""
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title='Power Risk Index for Data Center Construction Planning',
    page_icon='⚡',
    layout='wide',
)

DATA_DIR = 'data'
LAST_ACTUAL_YEAR = 2024
FORECAST_YEARS = [2025, 2026, 2027]


# ============================================================ password gate
def check_password():
    """Simple session-gated password check. The real password lives in
    Streamlit secrets (st.secrets['app_password']), never in source, so it
    is not exposed in the GitHub repo."""
    if st.session_state.get('authenticated'):
        return True

    st.markdown(
        "<h2 style='text-align:center; margin-top: 10vh;'>"
        "Power Risk Index for Data Center Construction Planning</h2>",
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        pwd = st.text_input('Password', type='password')
        submitted = st.button('Enter', width='stretch')
        if submitted:
            real_pwd = st.secrets.get('app_password')
            if real_pwd is None:
                st.error(
                    "No app_password is configured in this deployment's secrets yet. "
                    "Add app_password = \"...\" in the app's Secrets settings."
                )
            elif pwd == real_pwd:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error('Incorrect password.')
    return False


if not check_password():
    st.stop()


# ================================================================ data load
@st.cache_data
def load_data():
    actual = pd.read_parquet(f'{DATA_DIR}/actual.parquet')
    forecast = pd.read_parquet(f'{DATA_DIR}/forecast.parquet')
    county_lookup = pd.read_parquet(f'{DATA_DIR}/county_lookup.parquet')
    with open(f'{DATA_DIR}/counties_fips.json') as f:
        geo = json.load(f)
    return actual, forecast, county_lookup, geo


actual, forecast, county_lookup, geo = load_data()

# county-level "current" snapshot: last actual year + each county's own
# most recent reported price (Last_Actual_Year varies for ~20 sparse-
# reporting counties, same as the notebook's map cells)
latest_actual = (actual.sort_values('Year')
                  .drop_duplicates('FIPS', keep='last')
                  .rename(columns={'Year': 'Last_Actual_Year', 'Price_cents_kWh': 'Last_Actual_Price'}))


# ==================================================================== header
logo_col, title_col = st.columns([1, 6])
with logo_col:
    st.image('assets/mocci_logo.png', width=110)
with title_col:
    st.title('Power Risk Index for Data Center Construction Planning')
    st.caption('Missouri Consortium for Construction Innovation (MOCCI)')

st.info(
    'This release covers the **Cost pillar only** -- county-level industrial electricity '
    'price, 2001-2024 actual data with a theta-model 3-year forecast (2025-2027). '
    'Reliability, Availability, and a composite Power Risk Index are planned pillars, '
    'not yet included: no placeholder or synthetic values are shown for them.'
)

# ==================================================================== sidebar
with st.sidebar:
    st.header('County selector')
    states = sorted(county_lookup['State'].dropna().unique())
    sel_state = st.selectbox('State', states, index=states.index('MO') if 'MO' in states else 0)
    state_counties = county_lookup[county_lookup['State'] == sel_state].sort_values('County_Name')
    county_options = [f"{r.County_Name} ({r.FIPS})" for r in state_counties.itertuples()]
    sel_label = st.selectbox('County', county_options)
    sel_fips = sel_label.split('(')[-1].rstrip(')')

    st.divider()
    st.header('Map year')
    map_year = st.select_slider(
        'Year', options=list(range(2001, 2028)), value=2024,
        help='2025-2027 are theta-model forecast years, not measured actuals.',
    )


# ==================================================================== map
st.subheader(f"County-level industrial electricity price -- {map_year}"
             + (' (theta forecast)' if map_year >= 2025 else ' (actual)'))

if map_year <= LAST_ACTUAL_YEAR:
    map_df = actual[actual['Year'] == map_year][['FIPS', 'State', 'County_Name', 'Price_cents_kWh', 'Confidence_Grade']].copy()
    hover_data = {'State': True, 'County_Name': True, 'Confidence_Grade': True, 'FIPS': False}
else:
    map_df = forecast[forecast['Year'] == map_year][
        ['FIPS', 'State', 'County_Name', 'Price_cents_kWh', 'Expected_MAPE_%']
    ].copy()
    hover_data = {'State': True, 'County_Name': True, 'Expected_MAPE_%': ':.1f', 'FIPS': False}

# fixed color scale across the whole actual+forecast range, same convention
# as the notebook's map cells, so the map's colors mean the same thing no
# matter which year is selected
_all_prices = pd.concat([actual['Price_cents_kWh'], forecast['Price_cents_kWh']])
vmin, vmax = _all_prices.quantile([0.02, 0.995])

if map_df.empty:
    st.warning(f'No data available for {map_year}.')
else:
    fig_map = px.choropleth(
        map_df, geojson=geo, locations='FIPS', color='Price_cents_kWh',
        color_continuous_scale='YlOrRd', range_color=(vmin, vmax), scope='usa',
        hover_data=hover_data,
        labels={'Price_cents_kWh': 'Industrial price (cents/kWh)', 'Expected_MAPE_%': 'Backtested MAPE at horizon (%)'},
    )
    fig_map.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0),
                           coloraxis_colorbar=dict(title='cents/kWh'))
    st.plotly_chart(fig_map, width='stretch')


# ============================================================ county detail
sel_row = latest_actual[latest_actual['FIPS'] == sel_fips]
sel_name = sel_row['County_Name'].iloc[0] if not sel_row.empty else sel_fips
sel_state_name = sel_row['State'].iloc[0] if not sel_row.empty else sel_state

st.divider()
st.subheader(f"Selected county: {sel_name}, {sel_state_name}")

f_sel = forecast[forecast['FIPS'] == sel_fips].sort_values('Year')
a_sel = actual[actual['FIPS'] == sel_fips].sort_values('Year')

m1, m2, m3, m4 = st.columns(4)
if not a_sel.empty:
    last_year = int(a_sel['Year'].iloc[-1])
    last_price = a_sel['Price_cents_kWh'].iloc[-1]
    m1.metric(f'Last reported price ({last_year})', f'{last_price:.2f} ¢/kWh')
else:
    m1.metric('Last reported price', 'no data')

if not f_sel.empty:
    f2027 = f_sel[f_sel['Year'] == f_sel['Year'].max()].iloc[0]
    pct_change = (f2027['Price_cents_kWh'] / last_price - 1) * 100 if not a_sel.empty else None
    m2.metric(f"{int(f2027['Year'])} forecast", f"{f2027['Price_cents_kWh']:.2f} ¢/kWh",
              delta=f"{pct_change:+.1f}% vs last actual" if pct_change is not None else None)
    if pd.notna(f2027['Lower_CI_cents_kWh']):
        m3.metric(f"{int(f2027['CI_Level_%'])}% interval ({int(f2027['Year'])})",
                  f"{f2027['Lower_CI_cents_kWh']:.2f} - {f2027['Upper_CI_cents_kWh']:.2f} ¢/kWh")
    else:
        m3.metric('Prediction interval', 'not available',
                   help='Fewer than 8 years of actual data -- not backed by the backtest.')
    m4.metric('Backtested MAPE at 3yr', f"{f2027['Expected_MAPE_%']:.1f}%" if pd.notna(f2027['Expected_MAPE_%']) else 'n/a')
else:
    m2.metric('Forecast', 'no data')

st.caption('Trend: actual history, theta-model forecast, and the real backtest-derived prediction interval '
           '(not an assumed symmetric band -- the actual distribution of backtest errors at each horizon).')

fig_trend = go.Figure()
if not a_sel.empty:
    fig_trend.add_trace(go.Scatter(x=a_sel['Year'], y=a_sel['Price_cents_kWh'], mode='lines+markers',
                                    name='Actual', line=dict(color='#1f77b4', width=2)))
if not f_sel.empty and not a_sel.empty:
    bridge_year = pd.concat([a_sel['Year'].tail(1), f_sel['Year']])
    bridge_price = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Price_cents_kWh']])
    has_ci = f_sel['Upper_CI_cents_kWh'].notna().all() and f_sel['Lower_CI_cents_kWh'].notna().all()
    if has_ci:
        upper = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Upper_CI_cents_kWh']])
        lower = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Lower_CI_cents_kWh']])
        ci_level_label = int(round(f_sel['CI_Level_%'].iloc[0]))
        fig_trend.add_trace(go.Scatter(
            x=pd.concat([bridge_year, bridge_year[::-1]]), y=pd.concat([upper, lower[::-1]]),
            fill='toself', fillcolor='rgba(255,127,14,0.18)',
            line=dict(color='rgba(255,255,255,0)'), hoverinfo='skip',
            name=f'{ci_level_label}% prediction interval',
        ))
    fig_trend.add_trace(go.Scatter(x=bridge_year, y=bridge_price, mode='lines+markers',
                                    name='Theta forecast', line=dict(color='#ff7f0e', width=2, dash='dash')))
fig_trend.update_layout(
    xaxis_title='Year', yaxis_title='Industrial price (cents/kWh)',
    height=420, margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(orientation='h', y=1.1), hovermode='x unified',
)
st.plotly_chart(fig_trend, width='stretch')

if not f_sel.empty and (f_sel['Error_Band_Source'] == 'short_history_not_backtested').any():
    st.caption(f"Note: {sel_name} has fewer than 8 years of actual data, so this forecast is not "
               "backed by the backtest error bands/prediction interval.")


# ============================================================ comparison table
st.divider()
st.subheader('County comparison')
c1, c2 = st.columns([1, 3])
with c1:
    sort_metric = st.selectbox('Sort by', ['Last reported price (highest)', 'Last reported price (lowest)',
                                            '2027 forecast (highest)', '2027 forecast (lowest)'])
    n_show = st.slider('Counties to show', 5, 50, 15)

f_2027 = forecast[forecast['Year'] == 2027][['FIPS', 'Price_cents_kWh', 'Lower_CI_cents_kWh', 'Upper_CI_cents_kWh']]
comp = latest_actual[['FIPS', 'State', 'County_Name', 'Last_Actual_Year', 'Last_Actual_Price']].merge(
    f_2027, on='FIPS', how='left'
).rename(columns={'Price_cents_kWh': '2027 Forecast (cents/kWh)',
                   'Lower_CI_cents_kWh': '2027 Lower bound', 'Upper_CI_cents_kWh': '2027 Upper bound',
                   'State': 'State', 'County_Name': 'County', 'Last_Actual_Year': 'Last reported year',
                   'Last_Actual_Price': 'Last reported price (cents/kWh)'})

sort_col, ascending = {
    'Last reported price (highest)': ('Last reported price (cents/kWh)', False),
    'Last reported price (lowest)': ('Last reported price (cents/kWh)', True),
    '2027 forecast (highest)': ('2027 Forecast (cents/kWh)', False),
    '2027 forecast (lowest)': ('2027 Forecast (cents/kWh)', True),
}[sort_metric]

comp_display = comp.sort_values(sort_col, ascending=ascending).head(n_show).round(2)
st.dataframe(comp_display, width='stretch', hide_index=True)

st.download_button(
    'Download full county dataset (CSV)',
    comp.round(3).to_csv(index=False).encode('utf-8'),
    'power_risk_index_cost_pillar.csv', 'text/csv',
)


# ============================================================ about / methodology
with st.expander('About this data and methodology'):
    st.markdown("""
**Data source:** U.S. EIA Form 861 annual industrial electricity sales and revenue, aggregated
to county level and weighted by MWh, 2001-2024.

**Forecast model:** theta method (simple exponential smoothing blended 50/50 with a linear
trend), chosen over AR(1) and ARIMA because it does not assume mean reversion -- important
since prices have risen for 24 consecutive years and AR(1) systematically forecast declines
for the large majority of counties despite their real upward trend.

**Prediction interval:** a real empirical interval built from the actual distribution of
backtest errors (5 rolling-origin windows, 2015-2019 training cutoffs tested against the real
2020-2024 actuals) -- not an assumed symmetric band. It is currently shown at the 68% level
rather than 90%, because the wider 90% band at the 3-year horizon was found to be driven
almost entirely by the 2021-2022 energy-price-shock year rather than being representative of
typical forecast uncertainty.

**Scope:** this release covers the Cost pillar only. Reliability and Availability pillars, and
a composite Power Risk Index, are planned but not yet backed by validated research data, so
they are not shown here -- no placeholder or synthetic values are included.

**Counties with limited reporting history:** 15 counties have fewer than 8 years of actual
data and are shown without a prediction interval, since their forecast accuracy has not been
backtested. A further ~20 counties have discontinued or sparse EIA reporting in recent years;
their forecasts are still shown on their own historical timeline.
""")
