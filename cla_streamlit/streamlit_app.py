import pandas
import streamlit as st
import pandas as pd
import plotly.express as px
from google.oauth2 import service_account
from gsheetsdb import connect

def main():
    st.title("CLA Programming Groups Grade Analysis")

    # load data
    df = load_data('group_totals.csv')

    # filter data
    filter = create_filter(df)
    df = load_data('group_totals.csv', filter)

    average_per_homework = calculate_hw_avg(df)
    df_by_percentage = calculate_bins(df)

    # metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Graded", df.shape[0])
    with col2:
        st.metric("Pass", (df['percentage'] >= 50).sum())
    with col3:
        st.metric("Fail", (df['percentage'] < 50).sum())
    with col4:
        average_percentage = df['percentage'].mean()
        if pd.isna(average_percentage):
         average_percentage = 0
        st.metric("Average", f"{int(round(average_percentage))} %")

    col1, col2 = st.columns(2, gap="medium")

    # percentage per homework group
    with col1:
        hw_groups_percentage_fig = px.line(df, x="homework", y="percentage", color="group",
                                           title="Percentage for programming groups per homework")
        st.plotly_chart(hw_groups_percentage_fig, use_container_width=True)

    # average per homework
    with col2:
        hw_average_fig = px.line(average_per_homework, x="homework", y="mean_percentage",
                                 title="Mean percentage across groups for each homework")
        st.plotly_chart(hw_average_fig, use_container_width=True)

    # bins
    bin_fig = px.bar(df_by_percentage, x="bin", y="count", color="homework",
                     title="Counts for programming groups in percentage bins")
    st.plotly_chart(bin_fig, use_container_width=True)

def load_data(csv_file: str, filter: dict = None) -> pandas.DataFrame:
    # establish google service account credentials
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )
    conn = connect(credentials=credentials)

    # query private google sheet with grades
    def run_query(query):
        rows = conn.execute(query, headers=1)
        rows = rows.fetchall()
        return rows

    sheet_url = st.secrets["private_gsheets_url"]
    rows = run_query(f'SELECT * FROM "{sheet_url}"')

    # convert rows to dataframe
    df = pd.DataFrame(rows)
    df = df.astype({'homework': str, 'group': str, 'points': float, 'total_possible_points': float})
    df['mark_date'] = pd.to_datetime(df['mark_date'], format='%Y-%m-%dT%H:%M:%S')

    # remove test programming group and group without bonus points
    df.drop(df.loc[df['group'] == "programmiergruppe00"].index, inplace=True)
    df.drop(df.loc[df['group'] == "programmiergruppekeinebonuspunkte"].index, inplace=True)

    # calculate percentage grade for each homework submission
    df['percentage'] = (df["points"] / df["total_possible_points"]) * 100
    df['percentage'] = df['percentage'].round()

    # apply filter
    if filter:
        df.drop(df[~df['homework'].isin(filter['homework'])].index, inplace=True)
        df.drop(df[~df['group'].isin(filter['group'])].index, inplace=True)
    return df


def calculate_hw_avg(df: pandas.DataFrame) -> pandas.DataFrame:
    average_per_homework = df.groupby('homework')['percentage'].mean().reset_index()
    average_per_homework.rename(columns={'percentage': "mean_percentage"}, inplace=True)
    return average_per_homework


def calculate_bins(df: pandas.DataFrame) -> pandas.DataFrame:
    # Define the bin edges and labels
    bin_edges = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    labels = [f'{b}% - {b + 10}%' for b in bin_edges[:-1]]

    # Assign bins to the 'percentage' column
    df['bin'] = pd.cut(df['percentage'], bins=bin_edges, labels=labels, include_lowest=True)

    # Group by bin and count the occurrences
    df_by_percentage = df.groupby(['bin', 'homework']).size().reset_index(name='count')
    return df_by_percentage


def create_filter(df: pandas.DataFrame) -> dict:
    with st.sidebar:
        st.header("Filter")
        filter = {}

        # filter for homework
        with st.expander("Homework"):
            all_homework = df['homework'].unique()
            filter['homework'] = st.multiselect(label="Homework", key="homework_filter",
                                                options=all_homework, default=all_homework)

        # filter for groups
        with st.expander("Group"):
            all_groups = df['group'].unique()
            filter['group'] = st.multiselect(label="Programming Groups", key="group_filter", options=all_groups,
                                             default=all_groups)
    return filter


if __name__ == "__main__":
    st.set_page_config(page_title="CLA Streamlit", page_icon="✨", layout="wide")
    main()
