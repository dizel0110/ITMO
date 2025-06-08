import json
import os

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from config import config


def save_model(model, path):
    joblib.dump(model, path)


def load_model(path):
    model = joblib.load(path)
    return model


def save_metrics(metrics, path):
    with open(path, "w") as f:
        json.dump(metrics, f)


def train(model_path, data_path):
    train_path = os.path.join(data_path, "train.csv")

    df_train = pd.read_csv(train_path)
    X_train = df_train.drop("quality", axis=1)
    y_train = df_train["quality"]

    model = LogisticRegression(
        random_state=config["random_state"],
        max_iter=config["logistic_regression"]["max_iter"],
        solver=config["logistic_regression"]["solver"],
        penalty=config["logistic_regression"]["penalty"],
        class_weight=config["logistic_regression"]["class_weight"],
    )
    model.fit(X_train, y_train)
    save_model(model, model_path)


def test(model_path, data_path, metrics_path, taska=None):
    test_path = os.path.join(data_path, "test.csv")

    model = load_model(model_path)
    df_test = pd.read_csv(test_path)
    X_test = df_test.drop("quality", axis=1)
    y_test = df_test["quality"]

    y_pred = model.predict(X_test)
    y_score = model.predict_proba(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")
    roc_auc = roc_auc_score(y_test, y_score, multi_class="ovo")

    if taska is not None:
        logger = taska.get_logger()
        logger.report_single_value(name="Accuracy", value=accuracy)
        logger.report_single_value(name="F1_score", value=f1)
        logger.report_single_value(name="ROC_AUC", value=roc_auc)

    print(f"Accuracy: {accuracy:.3f}")
    print(f"F1: {f1:.3f}")
    print(f"RocAuc: {roc_auc:.3f}")

    metrics = {"Accuracy": accuracy, "F1": f1, "RocAuc": roc_auc}
    new_metrics_path = os.path.join(metrics_path, "new_metrics.json")
    save_metrics(metrics, new_metrics_path)

    return metrics


def check_metrics(metrics_path):
    new_metrics_path = os.path.join(metrics_path, "new_metrics.json")
    metrics_path = os.path.join(metrics_path, "metrics.json")

    with open(new_metrics_path, "r") as file:
        new_metrics = json.load(file)
    with open(metrics_path, "r") as file:
        metrics = json.load(file)

    if new_metrics["RocAuc"] > metrics["RocAuc"]:
        save_metrics(new_metrics, metrics_path)
        return True

    else:
        return False
