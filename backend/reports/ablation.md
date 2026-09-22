# Feature Family Ablation Study

This report details the incremental skill added by each feature family, proving the integrated model beats simple baselines.

| Run                                          |   Features |   PR-AUC |   ROC-AUC |   Brier |
|:---------------------------------------------|-----------:|---------:|----------:|--------:|
| Full Integrated Model                        |         60 |   0.7947 |    0.9571 |  0.0422 |
| Full Model WITHOUT nwp_state_evolution       |         47 |   0.7788 |    0.9520 |  0.0440 |
| Full Model WITHOUT uncertainty               |         52 |   0.7351 |    0.9385 |  0.0485 |
| Full Model WITHOUT recent_error              |         55 |   0.7956 |    0.9575 |  0.0422 |
| Full Model WITHOUT run_consistency           |         55 |   0.7947 |    0.9571 |  0.0422 |
| Full Model WITHOUT seasonal_context          |         52 |   0.7626 |    0.9494 |  0.0458 |
| Full Model WITHOUT analog_regime             |         56 |   0.7964 |    0.9557 |  0.0421 |
| Full Model WITHOUT spatial_ocean_large_scale |         51 |   0.7897 |    0.9568 |  0.0425 |
| Full Model WITHOUT static_geography          |         52 |   0.7706 |    0.9523 |  0.0450 |
| Baseline: Uncertainty Only                   |          8 |   0.5546 |    0.9054 |  0.0654 |
| Uncertainty + nwp_state_evolution            |         21 |   0.6736 |    0.9304 |  0.0546 |
| Uncertainty + recent_error                   |         13 |   0.6335 |    0.9252 |  0.0569 |
| Uncertainty + run_consistency                |         13 |   0.5546 |    0.9054 |  0.0654 |
| Uncertainty + seasonal_context               |         16 |   0.7432 |    0.9454 |  0.0470 |
| Uncertainty + analog_regime                  |         12 |   0.6697 |    0.9314 |  0.0550 |
| Uncertainty + spatial_ocean_large_scale      |         17 |   0.5172 |    0.9015 |  0.0833 |
| Uncertainty + static_geography               |         16 |   0.6004 |    0.9115 |  0.0621 |
