import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import chardet
from datetime import datetime

# Suppress matplotlib font warnings
import warnings
warnings.filterwarnings("ignore", message="Glyph.*missing from font.*")

# Configuration
SETTINGS = {
    "API_ENDPOINT": "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
     "API_KEY":os.getenv("AIPROXY_TOKEN"),
    "RESULTS_DIR": os.path.dirname(os.path.abspath(__file__))
}

HEADERS = {
    "Authorization": f"Bearer {SETTINGS['API_KEY']}",
    "Content-Type": "application/json"
}

# Helper to interact with AI service
def query_ai_service(prompt, details):
    try:
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": f"{prompt}\nContext:\n{details}"}]
        }
        response = requests.post(SETTINGS["API_ENDPOINT"], headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"Error with AI API: {e}")
        sys.exit(1)

# Function to identify file encoding
def determine_file_encoding(filepath):
    try:
        with open(filepath, 'rb') as file:
            raw_data = file.read()
        return chardet.detect(raw_data)['encoding']
    except Exception as error:
        print(f"Encoding detection failed: {error}")
        sys.exit(1)

# Save plot to file
def export_chart(plot, filename):
    try:
        plot.tight_layout()
        plot.savefig(os.path.join(SETTINGS["RESULTS_DIR"], filename), bbox_inches='tight')
        plot.close()
    except Exception as error:
        print(f"Error saving chart {filename}: {error}")

# Generate correlation heatmap
def create_correlation_chart(dataframe):
    numeric_data = dataframe.select_dtypes(include=['number'])
    if numeric_data.empty:
        print("No numeric columns for correlation heatmap.")
        return
    correlation_matrix = numeric_data.corr()
    print("Correlation Data:")
    print(correlation_matrix)
    plt.figure(figsize=(10, 7))
    sns.heatmap(correlation_matrix, annot=True, cmap="coolwarm", linewidths=0.5)
    plt.title("Correlation Heatmap")
    export_chart(plt, "correlation_chart.png")

# Detect and visualize outliers
def display_outliers(dataframe):
    numeric_data = dataframe.select_dtypes(include=['number'])
    if numeric_data.empty:
        print("No numeric data available for outlier detection.")
        return
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=numeric_data)
    plt.title("Outliers Visualization")
    plt.xticks(rotation=90)
    export_chart(plt, "outliers_chart.png")

# Time series visualization
def plot_time_trends(dataframe):
    if 'Date' in dataframe.columns:
        try:
            dataframe['Date'] = pd.to_datetime(dataframe['Date'])
            dataframe = dataframe.sort_values('Date')
            numeric_cols = dataframe.select_dtypes(include=['number']).columns
            if numeric_cols.empty:
                print("No numeric columns for time series.")
                return
            plt.figure(figsize=(10, 6))
            sns.lineplot(data=dataframe, x='Date', y=numeric_cols[0])
            plt.title(f"Time Trend for {numeric_cols[0]}")
            export_chart(plt, "time_trends.png")
        except Exception as error:
            print(f"Error in time series plotting: {error}")
    else:
        print("Missing 'Date' column for time series analysis.")

# Plot geographic data
def map_geographic_distribution(dataframe):
    if 'Latitude' in dataframe.columns and 'Longitude' in dataframe.columns:
        plt.figure(figsize=(10, 8))
        sns.scatterplot(
            data=dataframe, x='Longitude', y='Latitude',
            hue=dataframe.select_dtypes(include=['number']).columns[0]
        )
        plt.title("Geographic Distribution")
        export_chart(plt, "geographic_map.png")
    else:
        print("Geographic data (Latitude/Longitude) is unavailable.")

# Categorical data visualization
def visualize_categorical_data(dataframe):
    non_numeric_data = dataframe.select_dtypes(exclude=['number'])
    for column in non_numeric_data.columns:
        value_counts = dataframe[column].value_counts()
        unique_count = len(value_counts)

        def customize_labels(axis, labels, max_chars=10, rotate_labels=False):
            adjusted_labels = ["\n".join([label[i:i+max_chars] for i in range(0, len(label), max_chars)]) for label in labels]
            axis.set_xticks(range(len(adjusted_labels)))
            axis.set_xticklabels(adjusted_labels, rotation=90 if rotate_labels else 0, ha='right')

        if unique_count <= 15:
            plt.figure(figsize=(10, 6))
            ax = sns.countplot(x=column, data=dataframe, order=value_counts.index)
            customize_labels(ax, value_counts.index, max_chars=10)
            plt.title(f"Distribution of {column}")
            export_chart(plt, f"{column}_distribution.png")
        elif unique_count <= 30:
            plt.figure(figsize=(10, 6))
            ax = sns.countplot(x=column, data=dataframe, order=value_counts.index)
            customize_labels(ax, value_counts.index, max_chars=15, rotate_labels=True)
            plt.title(f"Extended Distribution of {column}")
            export_chart(plt, f"{column}_extended_distribution.png")
        else:
            top_counts = value_counts.head(15)
            bottom_counts = value_counts.tail(15)

            plt.figure(figsize=(10, 6))
            ax = sns.barplot(x=top_counts.index, y=top_counts.values)
            customize_labels(ax, top_counts.index, max_chars=15, rotate_labels=True)
            plt.title(f"Top 15 Distribution of {column}")
            export_chart(plt, f"{column}_top15_distribution.png")

            plt.figure(figsize=(10, 6))
            ax = sns.barplot(x=bottom_counts.index, y=bottom_counts.values)
            customize_labels(ax, bottom_counts.index, max_chars=15, rotate_labels=True)
            plt.title(f"Bottom 15 Distribution of {column}")
            export_chart(plt, f"{column}_bottom15_distribution.png")

# Main analysis function
def process_dataset(filepath):
    try:
        encoding = determine_file_encoding(filepath)
        dataset = pd.read_csv(filepath, encoding=encoding)
    except Exception as error:
        print(f"Error loading dataset: {error}")
        sys.exit(1)

    summary_stats = dataset.describe(include='all')
    missing_data = dataset.isna().sum()

    context_data = f"Summary statistics:\n{summary_stats}\nMissing data:\n{missing_data}"
    ai_insights = query_ai_service("Analyze this dataset and provide insights.", context_data)

    create_correlation_chart(dataset)
    display_outliers(dataset)
    plot_time_trends(dataset)
    map_geographic_distribution(dataset)
    visualize_categorical_data(dataset)

    try:
        with open(os.path.join(SETTINGS["RESULTS_DIR"], "Analysis_Report.md"), "w") as report_file:
            report_file.write("# Analysis Report\n\n")
            report_file.write(f"File: {filepath}\n\n")
            report_file.write("## Summary Statistics\n")
            report_file.write(f"{summary_stats}\n\n")
            report_file.write("## Missing Data\n")
            report_file.write(f"{missing_data}\n\n")
            report_file.write("## Insights from AI\n")
            report_file.write(f"{ai_insights}\n")
    except Exception as error:
        print(f"Error saving report: {error}")

    print("Analysis complete. Report saved to Analysis_Report.md.")

# Script entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <dataset.csv>")
        sys.exit(1)
    file_path = sys.argv[1]
    process_dataset(file_path)
