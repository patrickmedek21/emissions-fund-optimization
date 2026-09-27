"""
William Geary
MATH4025
optimizer
2 April 2025
"""

# Import modules
import numpy as np
import pandas as pd

# Constants
BILLION = 1000000000
M_TON = 1000

# Optimizer class
class BudgetOptimizer:

    def __init__(self, filename):
        self.file = filename
        self.excel = pd.read_csv(filename)

        self.optimized = False

        self.egen_red = None
        self.egen_cost = None
        self.ev_red = None
        self.ev_cost = None

    def change_file(self, filename):
        self.file = filename
        self.excel = pd.read_csv(filename)

    def reduction_dfs(self, data):

        # Repeat egen column across all columns, multiply ev column across by ev count
        egen_red_matrix = np.repeat(data["egen_reduction"].values.reshape(-1, 1), len(data), axis=1)
        ev_red_matrix = np.matrix(data["ev_co2_per_dollar"]).T * np.matrix(data["ev_cost"])

        return egen_red_matrix, ev_red_matrix

    def cost_dfs(self, data):

        # Calculate all cost iterations corresponding to the CO2 reductions
        egen_cost_matrix = np.repeat(data["egen_cost"].values.reshape(-1, 1), len(data), axis=1)
        ev_cost_matrix = np.repeat(data["ev_cost"].values.reshape(1, -1), len(data), axis=0)

        return egen_cost_matrix, ev_cost_matrix

    def get_reduction_df(self, data):
        """ Create the dataframe regarding CO2 reductions at each iteration """

        # Repeat egen column across all columns, multiply ev column across by ev count
        egen_red_matrix, ev_red_matrix = self.reduction_dfs(data)

        # Calculate the total CO2 reductions at each iteration by summing the two matrices
        reduction_df = pd.DataFrame(egen_red_matrix + ev_red_matrix)

        return reduction_df

    def get_cost_df(self, data):
        """ Create the dataframe regarding costs at each iteration """

        # Calculate all cost iterations corresponding to the CO2 reductions
        egen_cost_matrix, ev_cost_matrix = self.cost_dfs(data)

        # Calculate the total cost at each iteration by summing the two matrices
        cost_df = pd.DataFrame(egen_cost_matrix + ev_cost_matrix)

        return cost_df

    def get_filtered_dfs(self, expenditure, reduction_df, cost_df):
        """ Create the reduced dataframes filtered by expenditure """

        # Filter the reduction dataframe based on all values that fall within the budget (expenditure)
        filtered_reduction_df = reduction_df.copy()
        filtered_reduction_df[cost_df > expenditure] = 0
        original_zero_rows = (reduction_df == 0).all(axis=1)
        original_zero_cols = (reduction_df == 0).all(axis=0)
        filtered_reduction_df = filtered_reduction_df.loc[
            original_zero_rows | (filtered_reduction_df.sum(axis=1) != 0),
            original_zero_cols | (filtered_reduction_df.sum(axis=0) != 0)
        ]

        # Filter the cost dataframe based on all values that fall within the budget (expenditure)
        filtered_cost_df = cost_df.copy()
        filtered_cost_df[cost_df > expenditure] = 0
        filtered_cost_df = filtered_cost_df.loc[filtered_cost_df.sum(axis=1) != 0, filtered_cost_df.sum(axis=0) != 0]

        return filtered_reduction_df, filtered_cost_df

    def optimal_vals(self, data, opt_idx):

        # Get individual matrices
        egen_red_matrix, ev_red_matrix = self.reduction_dfs(data)
        egen_cost_matrix, ev_cost_matrix = self.cost_dfs(data)

        # Detmermine optimal values
        egen_red = pd.DataFrame(egen_red_matrix).iloc[opt_idx[0], opt_idx[1]]
        egen_cost = pd.DataFrame(egen_cost_matrix).iloc[opt_idx[0], opt_idx[1]]
        ev_red = pd.DataFrame(ev_red_matrix).iloc[opt_idx[0], opt_idx[1]]
        ev_cost = pd.DataFrame(ev_cost_matrix).iloc[opt_idx[0], opt_idx[1]]

        return egen_red, egen_cost, ev_red, ev_cost

    def optimize(self, v_subsidy, expenditure, negative_reductions=True):
        """ Function to optimize expenditure spending across EVs and EGeneration sources
        expenditure: The total amount of government expenditure to be spent in billions
        v_subsidy: The per-vehicle subsidy cost used to determine EV reduction
        return: A tuple of optimized values (egen_red, ev_red, egen_cost, ev_cost) """

        # Create a copy of the data from the imported Excel file to determine EV cost column, reductions
        data = self.excel.copy(deep=True)
        data["ev_cost"] = data["ev_count"] * v_subsidy
        data["egen_reduction"] = data["egen_co2_per_dollar"] * data["egen_cost"]
        data["ev_reduction"] = data["ev_co2_per_dollar"] * data["ev_cost"]

        # Determine the reduction and cost dataframes
        reduction_df = self.get_reduction_df(data)
        cost_df = self.get_cost_df(data)

        # Obtain the filtered reduction and cost dataframes, the optimal reduction index
        filtered_reduction_df, filtered_cost_df = self.get_filtered_dfs(expenditure, reduction_df, cost_df)
        if sum(filtered_reduction_df.shape) <= 1:
            opt_idx = (0, 0)
        else:
            opt_idx = filtered_reduction_df.stack().idxmin() if negative_reductions else filtered_reduction_df.stack().idxmax()

        # Determine the optimal reductions by EGen and EV, as well as the amount spent per each
        egen_red, egen_cost, ev_red, ev_cost = self.optimal_vals(data, opt_idx)

        self.egen_red, self.egen_cost, self.ev_red, self.ev_cost = egen_red, egen_cost, ev_red, ev_cost
        self.optimized = True

        return egen_red, ev_red, egen_cost, ev_cost

    def report(self):

        # Print the associated cost and reduction by type, else print an error
        if self.optimized:

            # Determine total cost and reduction
            cost = self.egen_cost + self.ev_cost
            reduction = self.egen_red + self.ev_red

            print(f"Optimal Allocation of Funds\n"
                  f"Total Cost: ${cost:,.2f}\n"
                  f"Reduction : {reduction:,.2f} kg CO2 ({reduction / BILLION / M_TON:,.3f} Billion Metric Tons CO2)\n")

            print(f"EV  : ${self.ev_cost:,.2f} "
              f"({self.ev_red:,.2f} kg CO2 | {self.ev_red / BILLION / M_TON:,.3f} Billion Metric Tons CO2)\n"
              f"Egen: ${self.egen_cost:,.2f} "
              f"({self.egen_red:,.2f} kg CO2 | {self.egen_red / BILLION / M_TON:,.3f} Billion Metric Tons CO2)\n")
        else:
            print("To print a report, first call BudgetOptimizer.optimize(v_subsidy, expenditure)")