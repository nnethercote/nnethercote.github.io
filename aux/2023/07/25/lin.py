#! /usr/bin/env python3

import matplotlib.pyplot as plt  # To visualize
import pandas as pd
import numpy as np
import sklearn
import sys
from sklearn import linear_model

if len(sys.argv) != 2:
    sys.exit("usage: lin.py <data-file>")

print("Reading", sys.argv[1], end="\n")
data = pd.read_csv(sys.argv[1], sep="\s+")

# Adjust these to analyze different columns.
#x = pd.DataFrame(data.iloc[:, 1:-4])
x = pd.DataFrame(data.iloc[:, 1:-4])
y = pd.DataFrame(data.iloc[:, -4])

print("inputs")
print(x, end="\n\n")

print("outputs")
print(y, end="\n\n")

model = linear_model.LinearRegression(fit_intercept=False, positive=True).fit(x, y)

print("r^2", model.score(x,y))
print("intercept", model.intercept_)
print("coef", model.coef_)
print()

y_pred = model.predict(x)

# Only works when a single nput column is being analyzed.
plt.scatter(x, y)
plt.plot(x, y_pred, color="red")
plt.show()
