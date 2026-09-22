# Target Formulation & Bust Definition Specification

**Forecast Reliability Engine** — NCMRWF / Ministry of Earth Sciences (MoES)  
**System Version**: 2.0  
**Document Classification**: Scientific & Methodological Specification  

---

## 1. Problem Formulation & Meteorological Context

In medium-range Numerical Weather Prediction (NWP), defining what constitutes a **"forecast bust"** is non-trivial. A single static threshold across India (e.g. $> 50$ mm error) fails scientifically because:
- In the **Thar Desert (West Rajasthan)**, a 30 mm error represents an entire season's precipitation (catastrophic forecast failure).
- In the **Western Ghats (Konkan & Goa)** during peak SW monsoon, climatological rainfall frequently exceeds $80\text{--}120$ mm/day, making a 30 mm error a typical minor discrepancy.
- Forecast skill naturally decays over the 10-day horizon (Day 1 error distribution is inherently narrower than Day 10).

Therefore, the **Forecast Reliability Engine** establishes a conditioned, tail-risk bust definition tailored to local climatology, season, and forecast horizon.

---

## 2. Primary Bust Definition: Location × Season × Lead 90th Percentile

For each forecast verification record with deterministic forecast $f$ and IMD gridded observation $o$:
$$\text{forecast\_error} = f - o, \quad \text{abs\_error} = |f - o|$$

### 2.1 Formulation
A forecast event at location $L$, season $S$, and forecast lead day $D \in \{1, \dots, 10\}$ is defined as a **bust** if its absolute error exceeds the 90th percentile of errors historically observed under those exact conditions:

$$\text{is\_bust} = \begin{cases} 
1 & \text{if } \text{abs\_error} > T_{L, S, D} \\
0 & \text{otherwise}
\end{cases}$$

where:
$$T_{L, S, D} = \max\Big(\text{Quantile}_{90}\big(\{ \text{abs\_error}_{i} \mid i \in (L, S, D)_{\text{train}} \}\big), \; 5.0\text{ mm}\Big)$$

The $5.0$ mm floor prevents flag generation in hyper-arid winter periods where trivial 1–2 mm errors might otherwise cross the 90th percentile.

### 2.2 Strict Training-Only Zero-Leakage Guarantee
- **Rule**: $T_{L, S, D}$ is calculated **exclusively on historical training data** via `BustThresholdEngine.fit(train_df)`.
- **Enforcement**: When evaluating test or validation splits, `transform()` uses the frozen training thresholds. The test set error distribution **never** influences the threshold.

---

## 3. Alternative & Complementary Target Formulations

In addition to the primary tail-risk threshold, three operational targets are computed:

### 3.1 IMD Categorical Miss (`is_category_miss`)
IMD partitions daily rainfall into six standard warning categories:
1. `no_rain`: $0.0 \le r < 2.5$ mm
2. `light`: $2.5 \le r < 15.6$ mm
3. `moderate`: $15.6 \le r < 64.5$ mm
4. `heavy`: $64.5 \le r < 115.5$ mm
5. `very_heavy`: $115.5 \le r < 204.5$ mm
6. `extremely_heavy`: $r \ge 204.5$ mm

An event is flagged with `is_category_miss = 1` if:
$$|\text{cat\_idx}(f) - \text{cat\_idx}(o)| \ge 2$$
*(e.g., forecasting "Light" when "Heavy" or "Very Heavy" occurs).*

### 3.2 Magnitude-Relative Error (`is_magnitude_bust`)
Significant hydrological impacts occur when absolute error is both substantial in magnitude and large relative to the event:
$$\text{abs\_error} > 25.0\text{ mm} \quad \text{AND} \quad \text{abs\_error} > 0.8 \times \max(f, o)$$

### 3.3 Extreme Convective Miss & False Alarm (`is_extreme_miss`, `is_extreme_false_alarm`)
- **Missed Extreme**: Observed rainfall $\ge 115.5$ mm (IMD Very Heavy/Extremely Heavy) but NWP forecast $< 35.5$ mm (missed flood signal).
- **Extreme False Alarm**: NWP predicted $\ge 115.5$ mm but observed $< 15.6$ mm (wasted evacuation resources).

---

## 4. Spatial Displacement & Neighbourhood Tolerance

### 4.1 The Double-Penalty Problem
Monsoon depressions and tropical systems can possess accurate thermodynamic intensity but suffer a small spatial phase shift ($50\text{--}150$ km). Traditional point-wise evaluation penalizes this as two separate busts (a false alarm in the predicted region and a miss in the adjacent receiving region).

### 4.2 Spatial Neighbourhood Relaxation (`src/target/spatial_tolerance.py`)
Using the topological adjacency matrix across all 32 IMD subdivisions:
1. `neighbourhood_obs_max_mm`: $\max_{j \in \{i\} \cup \mathcal{N}(i)} o_j$
2. `is_displacement_candidate`: Flags events where the local cell experienced a bust ($f_i \ge 15$ mm), but a contiguous neighbor $j \in \mathcal{N}(i)$ recorded $|o_j - f_i| \le \max(15, 0.35 f_i)$.
3. `is_neighbourhood_bust`: Relaxed bust indicator set to 0 if the rainband was successfully predicted within the immediate spatial neighbourhood.

---

## 5. Stratified Diagnostics & Sample Adequacy

To prevent misleading conclusions drawn on small subsets:
- Stratified breakdowns are computed by **Lead Day (1–10)**, **Season**, **Subdivision**, and **Synoptic Regime**.
- **Sample Adequacy Invariant**: Any stratum with fewer than **30 positive bust events** ($N_{\text{bust}} < 30$) is explicitly flagged with `sample_status: "INSUFFICIENT_SAMPLE_SIZE (<30 busts)"`.

---

## 6. Official Verification Metrics

Evaluation follows WMO guidelines implemented in `src/evaluation/metrics.py`:
- **Brier Skill Score (BSS)**: Compares calibrated bust probability against static climatology.
- **Reliability Diagram & Expected Calibration Error (ECE)**: Verifies that when confidence is 80%, the forecast is reliable 80% of the time.
- **Critical Success Index (CSI) & Equitable Threat Score (ETS)**: Evaluates skill on rare events with random-hit correction.
