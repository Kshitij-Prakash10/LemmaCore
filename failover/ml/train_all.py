"""Train every ML model in order. CLI: python -m failover.ml.train_all  (make train)"""
from failover.ml import train_fault_clf

if __name__ == "__main__":
    train_fault_clf.main()
