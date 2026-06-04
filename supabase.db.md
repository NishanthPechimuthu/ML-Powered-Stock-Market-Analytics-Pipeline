## Table `stocks`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `stock_id` | `int4` | Primary |
| `symbol` | `varchar` |  Nullable Unique |
| `company_name` | `varchar` |  Nullable |

## Table `raw_stock_prices`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int8` | Primary |
| `stock_id` | `int4` |  Nullable |
| `trade_date` | `date` |  Nullable |
| `open_price` | `numeric` |  Nullable |
| `high_price` | `numeric` |  Nullable |
| `low_price` | `numeric` |  Nullable |
| `close_price` | `numeric` |  Nullable |
| `volume` | `int8` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

## Table `stock_features`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int8` | Primary |
| `stock_id` | `int4` |  Nullable |
| `trade_date` | `date` |  Nullable |
| `daily_return` | `numeric` |  Nullable |
| `price_difference` | `numeric` |  Nullable |
| `volatility` | `numeric` |  Nullable |
| `ma_7` | `numeric` |  Nullable |
| `ma_30` | `numeric` |  Nullable |
| `capital_flow_indicator` | `numeric` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

## Table `predictions`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int8` | Primary |
| `stock_id` | `int4` |  Nullable |
| `prediction_date` | `date` |  Nullable |
| `predicted_close` | `numeric` |  Nullable |
| `model_name` | `varchar` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

## Table `anomalies`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int8` | Primary |
| `stock_id` | `int4` |  Nullable |
| `trade_date` | `date` |  Nullable |
| `anomaly_score` | `numeric` |  Nullable |
| `anomaly_flag` | `bool` |  Nullable |
| `model_name` | `varchar` |  Nullable |
| `created_at` | `timestamp` |  Nullable |

