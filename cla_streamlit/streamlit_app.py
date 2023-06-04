import pandas
import streamlit
import streamlit as st
import pandas as pd
import plotly.express as px
from google.oauth2 import service_account
from gsheetsdb import connect


def main():
    with st.sidebar:
        with st.expander("Filter"):
            filter_container = st.container()
        login_container = st.container()

    login(login_container)

    if st.session_state["authenticated"]:
        st.title("CLA Programming Grades")
    else:
        st.title("[Demo] CLA Programming Grades")

    # load data
    df = load_data()

    # filter data
    filter = create_filter(df, filter_container)
    df = load_data(filter)

    average_per_homework = calculate_hw_avg(df)
    df_by_percentage = calculate_bins(df)
    df_by_group = calculate_group_totals(df)

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

    # total points for groups
    group_totals_fig = px.bar(df_by_group, x="points", y="group", orientation='h', color="even_weighting_percentage",
                              hover_data=["score", "percentage", "even_weighting_percentage"],
                              color_continuous_scale="sunsetdark_r",
                              title="Group Totals")
    group_totals_fig.update_xaxes(range=[0, df_by_group['total_possible_points'].max()])
    group_totals_fig.update_layout(
        yaxis={"tickmode": "linear",
               "tickfont": {"size": 10}
               },
        height=800
    )
    st.plotly_chart(group_totals_fig)


def load_data(filter: dict = None) -> pandas.DataFrame:
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

    if st.session_state["authenticated"]:
        sheet_url = st.secrets["private_gsheets_url"]
    else:
        sheet_url = st.secrets["demo_private_gsheets_url"]

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
    # define the bin edges and labels
    bin_edges = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    labels = [f'{b}% - {b + 10}%' for b in bin_edges[:-1]]

    # assign bins to the 'percentage' column
    df['bin'] = pd.cut(df['percentage'], bins=bin_edges, labels=labels, include_lowest=True)

    # group by bin and count the occurrences
    df_by_percentage = df.groupby(['bin', 'homework']).size().reset_index(name='count')
    return df_by_percentage


def calculate_group_totals(df: pandas.DataFrame) -> pandas.DataFrame:
    df_by_group = df.groupby(by=['group'])[['points', 'total_possible_points', 'percentage']].sum().reset_index()
    df_by_group['even_weighting_percentage'] = round(df_by_group['percentage'] / len(df['homework'].unique()))
    df_by_group['percentage'] = round((df_by_group['points'] / df_by_group['total_possible_points']) * 100).fillna(0)
    df_by_group['score'] = df_by_group.apply(lambda row: f"{row['points']} / {row['total_possible_points']}", axis=1)
    df_by_group.sort_values(by='points', inplace=True)
    return df_by_group


def create_filter(df: pandas.DataFrame, container: streamlit.container) -> dict:
    filter = {}

    # filter for homework
    all_homework = df['homework'].unique()
    filter['homework'] = container.multiselect(label="Homework", key="homework_filter",
                                               options=all_homework, default=all_homework)

    # filter for groups
    all_groups = df['group'].unique()
    filter['group'] = container.multiselect(label="Group", key="group_filter", options=all_groups,
                                            default=all_groups)
    return filter


def check_password() -> bool:
    """Checks whether a password entered by the user is correct."""
    if st.session_state["password"] == st.secrets["password"]:
        return True
    else:
        return False


def login(container: streamlit.container):
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    login_form = container.form(key='login')
    login_form.text_input("Password", type="password", key="password")
    login_button = login_form.form_submit_button(label="Login")
    if login_button:
        st.session_state["authenticated"] = check_password()
        del st.session_state["password"]
        if st.session_state["authenticated"]:
            container.success("🎉 Login Successful")
        else:
            container.error("😔 Incorrect Password")


if __name__ == "__main__":
    st.set_page_config(page_title="CLA Streamlit", page_icon="✨", layout="wide")
    main()
