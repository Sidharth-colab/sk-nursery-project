Here's a draft write-up you can drop into your GitHub repo (as a new FORECASTING.md file, or a section in your main README) or adapt for a resume/portfolio description. It's written to be honest and specific — exactly the kind of thing that holds up under interview questions.

Demand Forecasting: Model Evaluation

Problem: SKGreenary's dashboard originally used a fixed formula to suggest restock quantities — total historical sales divided by 180 days, multiplied by 7, plus a 20% buffer. This is a simple heuristic, not a learned model, and doesn't adapt to seasonality or per-plant demand patterns.

Goal: Test whether a trained regression model could produce more accurate 7-day demand forecasts than the existing heuristic.

Data & Pipeline
Reshaped the raw sales table (which only contains rows for days something sold) into a complete daily time series per plant, filling in zero-sale days.
Engineered features: 7-day and 30-day rolling demand, day of week, weekend flag, month, monsoon-season flag, category, price, and category×seasonality interaction terms (e.g. Indoor×Weekend, Outdoor/Vegetable×Monsoon).
Target: total units sold in the next 7 days per plant.
Split by date (not randomly) — trained on the first ~150 days, tested on the most recent 30 — so the model is never evaluated on data it implicitly saw during training.
Validated the pipeline on synthetic sales data with deliberately injected seasonal patterns (Indoor plants selling more on weekends, Outdoor/Vegetable plants selling more in Kerala's monsoon months), since real sales volume is currently too low to have accumulated a clear seasonal signal on its own.
Models Compared
Model	MAE
Baseline (7-day rolling average, current app logic)	0.850
Random Forest Regressor	0.936
Ridge Regression	0.911
Result

The baseline outperformed both trained models. Rather than force a "win," I investigated why: the target (units sold over the next 7 days) and the strongest baseline feature (units sold over the previous 7 days) are both 7-day sums of the same underlying series, so they're highly autocorrelated — the baseline has a structural advantage that isn't really about being a smarter model, it's a property of the target definition itself. This is a well-known challenge in short-horizon time-series forecasting: naive persistence/rolling-average baselines are notoriously hard to beat for that reason.

Conclusion

For this specific target definition (a 7-day-ahead rolling sum) and at the current data volume, a simple moving-average baseline is competitive with trained models, and the app's existing forecasting logic is a reasonable choice as-is. A fairer test of whether a learned model adds value would use a target with less structural overlap with the rolling features — e.g. predicting a single day's demand, or classifying which category will lead next week — which is a natural next step once more real sales data accumulates.
