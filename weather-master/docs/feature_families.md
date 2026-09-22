# Feature Families & Temporal Causality Architecture

**Forecast Reliability Engine** — NCMRWF / Ministry of Earth Sciences (MoES)  
**System Version**: 2.0  
**Document Classification**: Scientific & Methodological Specification  

---

## 1. Architectural Philosophy

Forecast busts in Numerical Weather Prediction arise from diverse, interacting physical mechanisms:
- Rapid convective cloudbursts driven by thermodynamic instability.
- Phase errors in synoptic baroclinic waves.
- Large-scale planetary teleconnections (MJO, ENSO, IOD).
- Local orographic blocking and coastal friction.
- Model run-to-run instability (flip-flopping).

Rather than dumping uncurated raw columns into a monolithic matrix, features are grouped into **eight modular feature families**. Each family represents an independent physical domain, carries a permanent `family_name` metadata tag, and can be isolated for ablation studies.

---

## 2. The Eight Feature Families

### 2.1 Family 1: `nwp_state_evolution`
*Focus: Direct thermodynamic and dynamic atmospheric fields from the NWP forecast.*

| Feature Name | Type | Physical Rationale |
|:---|:---|:---|
| `fcst_rainfall_mm` | Continuous | Forecast accumulated precipitation |
| `fcst_temp_2m_c` | Continuous | 2-meter air temperature |
| `fcst_mslp_hpa` | Continuous | Mean sea level pressure depression |
| `fcst_wind_850_mps` | Continuous | Low-level jet / monsoon flow speed |
| `fcst_wind_200_mps` | Continuous | Upper-tropospheric jet speed |
| `fcst_rh_700_pct` | Continuous | Mid-tropospheric moisture availability |
| `fcst_geopot_500_m` | Continuous | 500 hPa synoptic ridge/trough height |
| `fcst_cape_jkg` | Continuous | Surface-based Convective Available Potential Energy |
| `vertical_wind_shear` | Diagnostic | $\|V_{200} - V_{850}\|$ (deep-layer tropospheric shear) |
| `baroclinic_gradient_proxy` | Composite | Coupling of MSLP anomaly and vertical shear |
| `convective_vulnerability` | Composite | Normalized CAPE $\times$ mid-level relative humidity |
| `dynamic_instability_composite` | Diagnostic | Non-linear composite of MSLP depression, shear, and moisture |
| `heavy_rain_flag` | Binary | Flag indicating forecast daily rainfall $\ge 35.5$ mm |

---

### 2.2 Family 2: `uncertainty`
*Focus: Multi-member ensemble dispersion and probabilistic consensus.*

| Feature Name | Type | Physical Rationale |
|:---|:---|:---|
| `ens_spread_rainfall` | Continuous | Standard deviation across ensemble rainfall forecasts |
| `ens_spread_temp` | Continuous | Ensemble spread in 2-meter temperature |
| `ens_spread_mslp` | Continuous | Ensemble spread in sea level pressure |
| `spread_lead_interaction` | Interaction | $\text{spread} \times \text{lead\_day}$ (error compounding over horizon) |
| `spread_to_lead_ratio` | Rate | $\text{spread} / (\text{lead\_day} + 0.5)$ (normalized dispersion rate) |
| `ens_prob_rain_gt10` | Probability | Fraction of ensemble members forecasting $> 10$ mm rain |
| `ens_prob_rain_gt50` | Probability | Fraction of ensemble members forecasting $> 50$ mm rain |
| `relative_spread_ratio` | Relative | Noise-to-signal ratio $\text{spread} / (\text{fcst} + 5.0)$ |

---

### 2.3 Family 3: `recent_error`
*Focus: Systematic model bias and recent performance memory.*

| Feature Name | Lag | Description |
|:---|:---|:---|
| `recent_error_bias_30d` | $\ge 1$ day | Mean signed error $(f - o)$ over preceding 30 verified days |
| `recent_error_mae_30d` | $\ge 1$ day | Mean absolute error $\|f - o\|$ over preceding 30 verified days |
| `recent_error_bust_freq_30d` | $\ge 1$ day | Fraction of days in last 30 days that suffered a bust |
| `recent_error_mae_7d` | $\ge 1$ day | Short-term 7-day rolling MAE (synoptic regime persistence) |
| `prior_day_verified_error` | 1 day | Signed verification error for $T_{\text{init}} - 1$ day |

---

### 2.4 Family 4: `run_consistency`
*Focus: Forecast stability across consecutive NWP initialization cycles.*

| Feature Name | Formula | Meaning |
|:---|:---|:---|
| `run_to_run_rainfall_delta_mm` | $f_T(V) - f_{T-1}(V)$ | Change in predicted rainfall for target day $V$ between consecutive cycles |
| `run_to_run_abs_delta_mm` | $\|f_T(V) - f_{T-1}(V)\|$ | Absolute cycle-to-cycle forecast shift |
| `run_to_run_relative_shift` | $\frac{\|f_T - f_{T-1}\|}{\max(f_T, f_{T-1}) + 5}$ | Normalized shift ratio |
| `run_flip_flop_flag` | Binary | 1 if consecutive run change exceeds $25$ mm |
| `run_to_run_mslp_delta_hpa` | $\text{mslp}_T(V) - \text{mslp}_{T-1}(V)$ | Sea level pressure shift between cycles |

---

### 2.5 Family 5: `seasonal_context`
*Focus: Climatological and intra-annual cyclic timing.*

| Feature Name | Formula / Value | Meaning |
|:---|:---|:---|
| `doy_sin`, `doy_cos` | $\sin / \cos(2\pi \cdot \text{DOY} / 365.25)$ | High-resolution seasonal coordinates |
| `month_sin`, `month_cos` | $\sin / \cos(2\pi \cdot \text{Month} / 12)$ | Monthly intra-annual coordinates |
| `is_monsoon_season` | Binary | 1 for active monsoon months (SW or NE regional) |
| `is_transition_window` | Binary | 1 during high-volatility transition months (May, October) |
| `days_from_june_1` | Integer | Temporal offset from nominal Indian monsoon onset |
| `climatological_season_bust_rate` | Baseline | Historical base bust rate for location in this season |

---

### 2.6 Family 6: `analog_regime`
*Focus: Empirical behavior of similar historical forecast states.*

| Feature Name | Method | Meaning |
|:---|:---|:---|
| `analog_min_distance` | $k$-NN Euclidean | State-space distance to closest historical analog |
| `analog_mean_error_mm` | Historical Top-$K$ | Average verified error of the $K$ closest historical days |
| `analog_bust_probability` | Historical Top-$K$ | Empirical bust frequency of matching analog states |
| `synoptic_regime_index` | Categorical | Synoptic state (quiescent, active monsoon, depression, etc.) |

---

### 2.7 Family 7: `spatial_ocean_large_scale`
*Focus: Planetary wave modes, oceanic heat, and tropical disturbances.*

| Feature Name | Source | Meaning |
|:---|:---|:---|
| `enso_oni` | NOAA CPC | Oceanic Niño Index (ENSO sea surface temperature anomaly) |
| `mjo_amplitude` | BoM RMM | Madden-Julian Oscillation amplitude |
| `mjo_phase` | BoM RMM | MJO Phase (1 to 8; Phases 3–5 favor Indian monsoon convection) |
| `iod_dmi` | BoM | Indian Ocean Dipole Dipole Mode Index |
| `era5_sst_c` | ERA5 / OISST | Regional ocean sea surface temperature |
| `cyclone_active_flag` | IBTrACS | 1 if active storm within 1500 km radius |
| `cyclone_proximity_index` | IBTrACS | Hyperbolic proximity index $100 / (\text{dist} + 100)$ |
| `cyclone_intensity_kt` | IBTrACS | Maximum sustained wind (kt) of nearest storm |
| `active_monsoon_teleconnection_index` | Composite | Teleconnection favorability index for heavy precipitation |

---

### 2.8 Family 8: `static_geography`
*Focus: Fixed surface boundaries and topographic complexity.*

| Feature Name | Units / Scale | Meaning |
|:---|:---|:---|
| `elevation_m` | Meters | Mean subdivision elevation above sea level |
| `dist_coast_km` | Kilometers | Geodesic distance to nearest Indian coastline |
| `land_fraction` | 0.0 – 1.0 | Land surface area fraction |
| `terrain_complexity` | 0.0 – 1.0 | Orographic variance index |
| `elevation_norm` | Normalized | Elevation / 3000 m |
| `is_coastal_zone` | Binary | 1 if within 60 km of coast |
| `is_high_mountain_barrier` | Binary | 1 if mean elevation $> 1500$ m (Himalayas / Nilgiris) |
| `terrain_type_code` | Categorical | Discrete code for canonical terrain classification |

---

## 3. Strict Temporal Causality & Leakage Prevention

### 3.1 The Timeline Rule
For a forecast initialized on date $T_{\text{init}}$ targeting valid date $T_{\text{valid}} = T_{\text{init}} + \text{lead\_day}$:
- **Permitted Inputs**: Any NWP output from the run initialized at $T_{\text{init}}$, static geography, and historical observations verified at or before $T_{\text{init}} - 1$ day.
- **Strictly Forbidden**:
  - Observations for dates $t \ge T_{\text{init}}$.
  - Error metrics from future forecast cycles.
  - Future climate indices.

### 3.2 Automated Leakage Verification (`tests/test_feature_leakage.py`)
An automated test verifies that for any record at initialization time $T_{\text{init}}$:
1. Feature values are computed using the complete dataset.
2. The dataset is truncated to remove all records with dates $> T_{\text{init}}$.
3. Feature values are recomputed on the truncated dataset.
4. The test asserts exact equality ($\Delta < 10^{-7}$) across all features.
