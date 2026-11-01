"""Train every ML model in order. CLI: python -m failover.ml.train_all  (make train)"""
import os

from failover.ml import data_metropt, train_fault_clf

if __name__ == "__main__":
    train_fault_clf.main()
    if os.path.exists(data_metropt.RAW_CSV):  # real-data parts need the setup download
        from failover.ml import external_test, fit_air_params, train_anomaly, train_leak, train_leak_v2
        fit_air_params.main()
        train_anomaly.main()
        train_leak.main()
        train_leak_v2.main()
        external_test.main()
    else:
        print("data/raw/metropt3.csv missing: skipping MetroPT-3 fit and anomaly detector")
