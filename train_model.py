"""
Trains a demand forecasting model on SKGreenary sales history and
compares it against the current average-based formula.

Run this after you have real (or simulated) sales data in the DB:
    python train_model.py
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import database


def load_daily_series():
    """
    Rebuilds a complete daily (date x plant) sales series, filling
    in zeros for days with no sale. This is required because the
    raw `sales` table only has rows for days something actually sold.
    """
    conn = database.get_db_connection()
    try:
        sales = pd.read_sql_query(
            "SELECT plant_name, quantity, sale_date FROM sales", conn
        )
        plants = pd.read_sql_query(
            "SELECT name, category, price FROM plants", conn
        )
    finally:
        database.return_connection(conn)

    if sales.empty:
        raise ValueError("No sales data found. Run simulator.py first, or wait for real sales to accumulate.")

    sales['sale_date'] = pd.to_datetime(sales['sale_date'])
    daily = sales.groupby(['plant_name', 'sale_date'])['quantity'].sum().reset_index()

    full_rows = []
    date_range = pd.date_range(daily['sale_date'].min(), daily['sale_date'].max(), freq='D')

    for plant_name in daily['plant_name'].unique():
        plant_daily = daily[daily['plant_name'] == plant_name].set_index('sale_date')
        plant_daily = plant_daily.reindex(date_range, fill_value=0)
        plant_daily['plant_name'] = plant_name
        plant_daily.index.name = 'date'
        full_rows.append(plant_daily.reset_index())

    full_df = pd.concat(full_rows, ignore_index=True)
    full_df = full_df.merge(plants, left_on='plant_name', right_on='name', how='left')
    full_df = full_df.drop(columns=['name'])
    return full_df


def engineer_features(df):
    """Adds rolling demand, calendar, and product features per plant."""
    df = df.sort_values(['plant_name', 'date']).copy()

    df['rolling_7'] = df.groupby('plant_name')['quantity'] \
        .transform(lambda s: s.rolling(7, min_periods=1).sum())
    df['rolling_30'] = df.groupby('plant_name')['quantity'] \
        .transform(lambda s: s.rolling(30, min_periods=1).sum())

    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['month'] = df['date'].dt.month

    # Target: total units sold in the NEXT 7 days for this plant
    df['target_next_7'] = df.groupby('plant_name')['quantity'] \
        .transform(lambda s: s.shift(-1).rolling(7, min_periods=7).sum())

    df = df.dropna(subset=['target_next_7'])
    df = df[df['rolling_30'].notna()]

    df = pd.get_dummies(df, columns=['category'], prefix='cat')
    return df


def time_based_split(df, test_days=30):
    """Splits by date, not randomly — model must not see future data during training."""
    cutoff = df['date'].max() - pd.Timedelta(days=test_days)
    train = df[df['date'] <= cutoff]
    test = df[df['date'] > cutoff]
    return train, test


def main():
    print("📊 Loading and reshaping sales history...")
    daily_df = load_daily_series()
    feat_df = engineer_features(daily_df)

    if len(feat_df) < 50:
        print("⚠️ Not much data yet — results will be noisy. More history will help.")

    train, test = time_based_split(feat_df, test_days=30)
    print(f"Train rows: {len(train)} | Test rows: {len(test)}")

    feature_cols = [c for c in feat_df.columns if c.startswith('cat_')] + \
        ['rolling_7', 'rolling_30', 'day_of_week', 'is_weekend', 'month', 'price']

    X_train, y_train = train[feature_cols], train['target_next_7']
    X_test, y_test = test[feature_cols], test['target_next_7']

    # --- Baseline: current app's logic (recent rolling average, carried forward) ---
    baseline_pred = X_test['rolling_7']  # "last 7 days repeats" — same spirit as the current formula
    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    baseline_rmse = np.sqrt(mean_squared_error(y_test, baseline_pred))

    # --- Model ---
    model = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42)
    model.fit(X_train, y_train)
    model_pred = model.predict(X_test)
    model_mae = mean_absolute_error(y_test, model_pred)
    model_rmse = np.sqrt(mean_squared_error(y_test, model_pred))

    print("\n📈 Results (lower is better):")
    print(f"{'':15}{'MAE':>10}{'RMSE':>10}")
    print(f"{'Baseline':15}{baseline_mae:>10.2f}{baseline_rmse:>10.2f}")
    print(f"{'RandomForest':15}{model_mae:>10.2f}{model_rmse:>10.2f}")

    improvement = (1 - model_mae / baseline_mae) * 100
    print(f"\n{'✅' if improvement > 0 else '⚠️'} Model {'beats' if improvement > 0 else 'underperforms'} baseline by {abs(improvement):.1f}%")

    joblib.dump({'model': model, 'feature_cols': feature_cols}, 'demand_model.pkl')
    print("\n💾 Saved trained model to demand_model.pkl")


if __name__ == "__main__":
    main()
