import os

import pandas as pd
from sklearn.model_selection import train_test_split


def load_data(path: str, target_name: str):
    df = pd.read_csv(path)
    X = df.drop(target_name, axis=1)
    y = df[target_name]
    return X, y


def split_data(X, y):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return X_train, X_test, y_train, y_test


def prepare_data(path):
    data_path = os.path.join(path, "winequality-red.csv")
    train_path = os.path.join(path, "train.csv")
    test_path = os.path.join(path, "test.csv")

    data = pd.read_csv(data_path)
    train, test = train_test_split(data, test_size=0.2, random_state=42)

    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    return "Data prepared!"
