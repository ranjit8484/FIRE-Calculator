# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from openpyxl.styles import PatternFill
import openpyxl
import math

st.set_page_config(layout="wide", page_title="Interactive FIRE Model")

# ---------------------------
# Utility helpers
# ---------------------------
def pct_to_decimal(val_pct):
    try:
        return float(val_pct) / 100.0
    except:
        return 0.0

def format_currency(x):
    if pd.isna(x):
        return ""
    return "${:,.0f}".format(x)

def build_projection(inputs):
    start_age = int(inputs["projection_start_age"])
    end_age = int(inputs["projection_end_age"])
    retirement_age = int(inputs["retirement_age"])
    ss_start_age = int(inputs["ss_start_age"])
    mortgage_end_age = int(inputs["mortgage_end_age"])

    ages = list(range(start_age, end_age + 1))
    rows = []

    portfolio = float(inputs["portfolio_at_45"])
    starting_age = int(inputs["starting_age"])
    annual_spending_today = float(inputs["annual_spending_today"])
    inflation = float(inputs["inflation"])
    annual_contribution = float(inputs["annual_contribution"])
    pre_ret_return = float(inputs["pre_ret_return"])
    post_ret_return = float(inputs["post_ret_return"])
    ss_annual_benefit = float(inputs["ss_annual_benefit"])
    ss_inflation_adjust = inputs.get("ss_inflation_adjust", True)

    # optional mortgage amortization (simple): we only model payment outflow, not balance amortization
    mortgage_payment = float(inputs["mortgage_annual_payment"]) if inputs["mortgage_balance"]>0 else 0.0

    for age in ages:
        row = {}
        row["Age"] = age
        row["Portfolio Start"] = portfolio

        # contributions before retirement only
        contrib = annual_contribution if age < retirement_age else 0.0
        row["Contribution"] = contrib

        # returns based on pre/post retirement rates applied to start of year portfolio
        ret_rate = pre_ret_return if age < retirement_age else post_ret_return
        growth = portfolio * ret_rate
        row["Growth"] = growth

        # spending: starts at retirement and inflates each year thereafter or can be modeled differently
        if age < retirement_age:
            inflated_spend = 0.0
        else:
            # inflate spending from today's spending measured at starting_age (your base)
            years_since_start = age - starting_age
            inflated_spend = annual_spending_today * ((1 + inflation) ** years_since_start)
        row["Inflated Spending"] = inflated_spend

        # Social Security: optional inflation adjustment from ss_start_age
        if age >= ss_start_age:
            if ss_inflation_adjust:
                ss = ss_annual_benefit * ((1 + inflation) ** max(0, age - ss_start_age))
            else:
                ss = ss_annual_benefit
        else:
            ss = 0.0
        row["Social Security"] = ss

        # Mortgage payment until mortgage_end_age (if mortgage_balance > 0)
        mp = mortgage_payment if (inputs["mortgage_balance"] > 0 and start_age <= age <= mortgage_end_age) else 0.0
        row["Mortgage Payment"] = mp

        # Total spending net of SS plus mortgage payments
        total_spend = inflated_spend - ss + mp
        row["Total Spending"] = total_spend

        # End of year portfolio
        end = portfolio + contrib + growth - total_spend
        row["Portfolio End"] = end

        rows.append(row)
        portfolio = end

    df = pd.DataFrame(rows)
    return df

def to_excel_with_highlight(df):
    # Write df to excel and highlight rows where Portfolio End < 0
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Projection")
        workbook = writer.book
        worksheet = writer.sheets["Projection"]

        red_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        # find column index for 'Portfolio End'
        headers = [cell.value for cell in worksheet[1]]
        try:
            pe_col_idx = headers.index("Portfolio End") + 1
        except ValueError:
            pe_col_idx = None

        for r_idx in range(2, len(df) + 2):
            if pe_col_idx:
                cell_value = worksheet.cell(row=r_idx, column=pe_col_idx).value
                try:
                    if cell_value is not None and float(cell_value) < 0:
                        for c in range(1, len(headers) + 1):
                            worksheet.cell(row=r_idx, column=c).fill = red_fill
                except:
                    pass

    processed = output.getvalue()
    return processed

def highlight_style(df):
    # Returns a pandas Styler that highlights negative Portfolio End in red text
    def style_row(r):
        return ["background-color: #fff2cc" if (r.name and r["Portfolio End"] < 0) else "" for _ in r]
    # safer: apply per-row
    sty = df.style.apply(lambda r: ["background-color: #fff2cc" if r["Portfolio End"] < 0 else "" for _ in r], axis=1)
    # format currency columns
    for col in ["Portfolio Start", "Contribution", "Growth", "Inflated Spending", "Social Security", "Mortgage Payment", "Total Spending", "Portfolio End"]:
        if col in df.columns:
            sty = sty.format({col: "${:,.0f}"})
    sty = sty.set_properties(**{"text-align": "right"})
    return sty

# ---------------------------
# Sidebar inputs
# ---------------------------
st.sidebar.header("Inputs and Assumptions")

# personal
starting_age = st.sidebar.number_input("Your current age", value=41, min_value=18, max_value=100, step=1)
projection_start_age = st.sidebar.number_input("Projection start age (first row)", value=45, min_value=starting_age, max_value=100, step=1)
projection_end_age = st.sidebar.number_input("Projection end age", value=100, min_value=projection_start_age, max_value=120, step=1)
retirement_age = st.sidebar.number_input("Retirement age", value=60, min_value=projection_start_age, max_value=projection_end_age, step=1)

st.sidebar.subheader("Spending and contributions")
annual_spending_today = st.sidebar.number_input("Annual spending today (your target in today's dollars)", value=200000, step=1000, format="$%d")
buffer_travel_wedding = st.sidebar.number_input("Travel/wedding one-off buffer (optional)", value=0, step=500, format="$%d")
annual_contribution = st.sidebar.number_input("Annual contributions pre-retirement", value=100000, step=1000, format="$%d")

st.sidebar.subheader("Returns and inflation (enter percent as numbers, e.g., 3 for 3%)")
pre_ret_return_pc = st.sidebar.number_input("Pre-retirement return percent", value=6.0, format="%.2f")
post_ret_return_pc = st.sidebar.number_input("Post-retirement return percent", value=4.0, format="%.2f")
inflation_pc = st.sidebar.number_input("Inflation percent", value=3.0, format="%.2f")

# convert to decimals for math
pre_ret_return = pct_to_decimal(pre_ret_return_pc)
post_ret_return = pct_to_decimal(post_ret_return_pc)
inflation = pct_to_decimal(inflation_pc)

st.sidebar.subheader("Social Security")
ss_start_age = st.sidebar.number_input("SS start age", value=67, min_value=62, max_value=75, step=1)
ss_annual_benefit = st.sidebar.number_input("SS annual benefit today", value=65000, step=1000, format="$%d")
ss_inflation_adjust = st.sidebar.checkbox("Inflation adjust Social Security after start age", value=True)

st.sidebar.subheader("Mortgage")
mortgage_balance = st.sidebar.number_input("Mortgage balance", value=250000, step=1000, format="$%d")
mortgage_annual_payment = st.sidebar.number_input("Mortgage annual payment", value=30000, step=500, format="$%d")
mortgage_end_age = st.sidebar.number_input("Mortgage end age", value=55, min_value=projection_start_age, max_value=projection_end_age, step=1)

st.sidebar.subheader("Portfolio")
portfolio_at_45 = st.sidebar.number_input("Portfolio at projection start age (age {})".format(projection_start_age), value=1550000.0, step=1000.0, format="$%.2f")

st.sidebar.write("---")
st.sidebar.write("Quick scenarios")
if st.sidebar.button("Conservative preset"):
    pre_ret_return_pc = 6.0
    post_ret_return_pc = 4.0
    inflation_pc = 3.0
    annual_contribution = 100000
    portfolio_at_45 = portfolio_at_45  # unchanged
    st.experimental_rerun()

if st.sidebar.button("Aggressive preset"):
    pre_ret_return_pc = 8.0
    post_ret_return_pc = 5.0
    inflation_pc = 2.5
    annual_contribution = 150000
    st.experimental_rerun()

# pack inputs dict
inputs = dict(
    starting_age = starting_age,
    projection_start_age = projection_start_age,
    projection_end_age = projection_end_age,
    retirement_age = retirement_age,
    annual_spending_today = annual_spending_today,
    inflation = inflation,
    annual_contribution = annual_contribution,
    pre_ret_return = pre_ret_return,
    post_ret_return = post_ret_return,
    ss_start_age = ss_start_age,
    ss_annual_benefit = ss_annual_benefit,
    ss_inflation_adjust = ss_inflation_adjust,
    mortgage_balance = mortgage_balance,
    mortgage_annual_payment = mortgage_annual_payment,
    mortgage_end_age = mortgage_end_age,
    portfolio_at_45 = portfolio_at_45,
)

# ---------------------------
# Basic validation
# ---------------------------
if retirement_age < projection_start_age:
    st.sidebar.error("Retirement age must be >= projection start age")
    st.stop()

if projection_end_age < projection_start_age:
    st.sidebar.error("Projection end age must be >= projection start age")
    st.stop()

# ---------------------------
# Model build and UI layout
# ---------------------------
df = build_projection(inputs)

# left: table, right: charts and KPIs
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Year by year projection")
    st.write("Tip: change assumptions on the left. All currency fields are shown as dollars.")
    styled = highlight_style(df)
    st.dataframe(styled, height=650)

    excel_bytes = to_excel_with_highlight(df)
    st.download_button("Download projection as Excel", excel_bytes, file_name="fire_projection.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with col2:
    st.header("Charts and key metrics")

    # portfolio path chart with negative shading
    ages = df["Age"].to_numpy()
    portfolio_start = df["Portfolio Start"].to_numpy()
    portfolio_end = df["Portfolio End"].to_numpy()

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(ages, portfolio_start / 1e6, marker="o", label="Portfolio Start (millions)", linewidth=2)

    # shade negative regions on portfolio_start (start of year)
    # find segments where portfolio_start < 0
    negative_mask = portfolio_start < 0
    if negative_mask.any():
        # For visual clarity, fill between for negative portions
        ax.fill_between(ages, portfolio_start / 1e6, 0, where=negative_mask, interpolate=True, color="salmon", alpha=0.5, label="Negative balance")

    ax.set_xlabel("Age")
    ax.set_ylabel("Portfolio Start (Millions)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    st.pyplot(fig)

    # key summary metrics
    last_row = df.iloc[-1]
    current_portfolio = df.iloc[0]["Portfolio Start"]
    ending_portfolio = last_row["Portfolio End"]
    peak = df["Portfolio End"].max()
    min_end = df["Portfolio End"].min()
    negative_rows = df[df["Portfolio End"] < 0]

    st.subheader("Quick summary")
    st.metric(label=f"Portfolio at age {int(df.iloc[0]['Age'])}", value=f"${int(current_portfolio):,}")
    st.metric(label=f"Portfolio at age {int(df.iloc[-1]['Age'])}", value=f"${int(ending_portfolio):,}")
    st.write(f"Peak portfolio in projection: {format_currency(peak)}")
    st.write(f"Lowest portfolio in projection: {format_currency(min_end)}")
    if not negative_rows.empty:
        first_neg_age = int(negative_rows.iloc[0]["Age"])
        st.error(f"Portfolio becomes negative at age {first_neg_age}")
    else:
        st.success("Portfolio stays positive through projection end age")

st.markdown("---")
st.write("Model notes")
st.write(
    """
    • Spending is modeled to start at retirement age and is inflated from today's spending each year using the inflation rate input.
    • Social Security can be inflation-adjusted after the chosen start age.
    • Mortgage is represented as a constant annual payment until mortgage end age. The balance is not amortized in detail here.
    • Contributions stop at retirement age.
    • Pre-retirement and post-retirement return rates are applied to the start-of-year portfolio.
    """
)
