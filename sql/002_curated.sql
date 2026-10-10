-- No fitted statistics, labels, or audit attributes enter this predictor view.
CREATE OR REPLACE VIEW curated.model_features_v1 AS
SELECT
    source_sha256,
    client_id,
    limit_bal,
    pay_status_2005_04,
    pay_status_2005_05,
    pay_status_2005_06,
    pay_status_2005_07,
    pay_status_2005_08,
    pay_status_2005_09,
    bill_amt_2005_04,
    bill_amt_2005_05,
    bill_amt_2005_06,
    bill_amt_2005_07,
    bill_amt_2005_08,
    bill_amt_2005_09,
    pay_amt_2005_04,
    pay_amt_2005_05,
    pay_amt_2005_06,
    pay_amt_2005_07,
    pay_amt_2005_08,
    pay_amt_2005_09,
    CASE WHEN num_nonnulls(pay_status_2005_04, pay_status_2005_05, pay_status_2005_06, pay_status_2005_07, pay_status_2005_08, pay_status_2005_09) = 6 THEN ((pay_status_2005_04 > 0)::int + (pay_status_2005_05 > 0)::int + (pay_status_2005_06 > 0)::int + (pay_status_2005_07 > 0)::int + (pay_status_2005_08 > 0)::int + (pay_status_2005_09 > 0)::int) END AS recent_delinquency_count,
    CASE WHEN num_nonnulls(pay_status_2005_04, pay_status_2005_05, pay_status_2005_06, pay_status_2005_07, pay_status_2005_08, pay_status_2005_09) = 6 THEN GREATEST(GREATEST(pay_status_2005_04, 0), GREATEST(pay_status_2005_05, 0), GREATEST(pay_status_2005_06, 0), GREATEST(pay_status_2005_07, 0), GREATEST(pay_status_2005_08, 0), GREATEST(pay_status_2005_09, 0)) END AS maximum_positive_delay,
    CASE WHEN num_nonnulls(pay_status_2005_04, pay_status_2005_05, pay_status_2005_06, pay_status_2005_07, pay_status_2005_08, pay_status_2005_09) = 6 THEN (GREATEST(pay_status_2005_07, 0) + GREATEST(pay_status_2005_08, 0) + GREATEST(pay_status_2005_09, 0)) / 3.0 - (GREATEST(pay_status_2005_04, 0) + GREATEST(pay_status_2005_05, 0) + GREATEST(pay_status_2005_06, 0)) / 3.0 END AS recent_history_delay_contrast,
    bill_amt_2005_09 / limit_bal AS latest_utilization_proxy,
    CASE WHEN num_nonnulls(bill_amt_2005_04, bill_amt_2005_05, bill_amt_2005_06, bill_amt_2005_07, bill_amt_2005_08, bill_amt_2005_09) = 6 THEN ((bill_amt_2005_04 + bill_amt_2005_05 + bill_amt_2005_06 + bill_amt_2005_07 + bill_amt_2005_08 + bill_amt_2005_09) / 6.0) / limit_bal END AS mean_utilization_proxy,
    (bill_amt_2005_09 - bill_amt_2005_04) / limit_bal AS bill_balance_change,
    CASE WHEN num_nonnulls(bill_amt_2005_04, bill_amt_2005_05, bill_amt_2005_06, bill_amt_2005_07, bill_amt_2005_08, bill_amt_2005_09) = 6 THEN sqrt((power((bill_amt_2005_04 - ((bill_amt_2005_04 + bill_amt_2005_05 + bill_amt_2005_06 + bill_amt_2005_07 + bill_amt_2005_08 + bill_amt_2005_09) / 6.0)), 2) + power((bill_amt_2005_05 - ((bill_amt_2005_04 + bill_amt_2005_05 + bill_amt_2005_06 + bill_amt_2005_07 + bill_amt_2005_08 + bill_amt_2005_09) / 6.0)), 2) + power((bill_amt_2005_06 - ((bill_amt_2005_04 + bill_amt_2005_05 + bill_amt_2005_06 + bill_amt_2005_07 + bill_amt_2005_08 + bill_amt_2005_09) / 6.0)), 2) + power((bill_amt_2005_07 - ((bill_amt_2005_04 + bill_amt_2005_05 + bill_amt_2005_06 + bill_amt_2005_07 + bill_amt_2005_08 + bill_amt_2005_09) / 6.0)), 2) + power((bill_amt_2005_08 - ((bill_amt_2005_04 + bill_amt_2005_05 + bill_amt_2005_06 + bill_amt_2005_07 + bill_amt_2005_08 + bill_amt_2005_09) / 6.0)), 2) + power((bill_amt_2005_09 - ((bill_amt_2005_04 + bill_amt_2005_05 + bill_amt_2005_06 + bill_amt_2005_07 + bill_amt_2005_08 + bill_amt_2005_09) / 6.0)), 2)) / 6.0) / limit_bal END AS bill_volatility_proxy,
    CASE WHEN num_nonnulls(pay_amt_2005_04, pay_amt_2005_05, pay_amt_2005_06, pay_amt_2005_07, pay_amt_2005_08, pay_amt_2005_09) = 6 THEN (pay_amt_2005_04 + pay_amt_2005_05 + pay_amt_2005_06 + pay_amt_2005_07 + pay_amt_2005_08 + pay_amt_2005_09) / 6.0 END AS mean_payment,
    CASE WHEN num_nonnulls(pay_amt_2005_04, pay_amt_2005_05, pay_amt_2005_06, pay_amt_2005_07, pay_amt_2005_08, pay_amt_2005_09) = 6 THEN ((pay_amt_2005_04 = 0)::int + (pay_amt_2005_05 = 0)::int + (pay_amt_2005_06 = 0)::int + (pay_amt_2005_07 = 0)::int + (pay_amt_2005_08 = 0)::int + (pay_amt_2005_09 = 0)::int) END AS zero_payment_count,
    CASE WHEN bill_amt_2005_08 > 0 AND pay_amt_2005_09 IS NOT NULL THEN pay_amt_2005_09 / bill_amt_2005_08 END AS payment_to_prior_bill_proxy,
    CASE WHEN bill_amt_2005_08 > 0 AND pay_amt_2005_09 IS NOT NULL THEN 0 ELSE 1 END AS payment_to_prior_bill_missing,
    CASE WHEN num_nonnulls(bill_amt_2005_04, bill_amt_2005_05, bill_amt_2005_06, bill_amt_2005_07, bill_amt_2005_08, bill_amt_2005_09, pay_amt_2005_04, pay_amt_2005_05, pay_amt_2005_06, pay_amt_2005_07, pay_amt_2005_08, pay_amt_2005_09) = 12 AND (GREATEST(bill_amt_2005_04, 0) + GREATEST(bill_amt_2005_05, 0) + GREATEST(bill_amt_2005_06, 0) + GREATEST(bill_amt_2005_07, 0) + GREATEST(bill_amt_2005_08, 0) + GREATEST(bill_amt_2005_09, 0)) > 0 THEN (pay_amt_2005_04 + pay_amt_2005_05 + pay_amt_2005_06 + pay_amt_2005_07 + pay_amt_2005_08 + pay_amt_2005_09) / (GREATEST(bill_amt_2005_04, 0) + GREATEST(bill_amt_2005_05, 0) + GREATEST(bill_amt_2005_06, 0) + GREATEST(bill_amt_2005_07, 0) + GREATEST(bill_amt_2005_08, 0) + GREATEST(bill_amt_2005_09, 0)) END AS aggregate_payment_balance_proxy,
    CASE WHEN num_nonnulls(bill_amt_2005_04, bill_amt_2005_05, bill_amt_2005_06, bill_amt_2005_07, bill_amt_2005_08, bill_amt_2005_09, pay_amt_2005_04, pay_amt_2005_05, pay_amt_2005_06, pay_amt_2005_07, pay_amt_2005_08, pay_amt_2005_09) = 12 AND (GREATEST(bill_amt_2005_04, 0) + GREATEST(bill_amt_2005_05, 0) + GREATEST(bill_amt_2005_06, 0) + GREATEST(bill_amt_2005_07, 0) + GREATEST(bill_amt_2005_08, 0) + GREATEST(bill_amt_2005_09, 0)) > 0 THEN 0 ELSE 1 END AS aggregate_payment_balance_missing
FROM curated.credit_clients;

CREATE OR REPLACE VIEW curated.labels AS
SELECT source_sha256, client_id, default_next_month FROM curated.credit_clients;
