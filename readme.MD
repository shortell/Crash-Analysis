# NYC Crash Analysis


## Goal
NYC Crash Analysis is a web application designed to provide in-depth insights into crash data in New York City. The platform allows users to download publicly available crash data from [CrashMapper](https://crashmapper.org), process the data by filling in missing records, and perform basic statistical analysis. The results are presented in a table format and visualized through a zip code-based heatmap. This feature offers a more comprehensive view than the original website, which does not provide table views or heatmap visualization.


## Core Features

- **Download Crash Data**: Easily download crash data directly from [CrashMapper](https://crashmapper.org).
- **Data Cleaning**: Automatically fill in missing values using machine learning and statistical techniques.
- **Data Filtering**: View crash data either for the entire city of NYC or filtered by specific boroughs.
- **Statistical Breakdown**: View basic statistical summaries such as sums and averages by zip code.
- **Decile Table**: Display crash data broken down into deciles, allowing for easy comparison and analysis.
- **Heatmap Visualization**: Visualize the decile table data with a heatmap, showing the geographic distribution of crashs by zip code.

## Target Audience

1. Injury Attorney Firms
Identify high-crash areas to optimize ad placement and office locations.
Use crash severity data to focus on cases with higher legal value.
Gain a competitive edge by understanding trends in accident frequency.

2. Urban Planners & City Officials
Departments of Transportation (DOT): Improve road safety through data-driven policy decisions.
City Planners: Plan safer intersections, bike lanes, and pedestrian zones.
Vision Zero & Safety Advocacy Groups: Support initiatives aimed at reducing traffic fatalities.

3. Insurance Companies
Underwriters & Actuaries: Adjust auto insurance risk models based on accident trends.
Claims Analysts: Verify crash reports and detect potential fraud.

4. Rideshare & Delivery Companies
Uber, Lyft, DoorDash, etc.: Identify high-risk areas to enhance driver safety and optimize routes.

5. Journalists & Researchers
Investigative Reporters: Analyze accident patterns for public safety reporting.
Academics & Data Scientists: Study urban mobility and accident correlations with infrastructure.

6. Real Estate Developers & Property Managers
Commercial Developers: Assess traffic safety near business locations.
Residential Real Estate Agents: Provide safety insights to homebuyers


## Technical Stack

The web application is built using the following technologies:

- **Backend**: Python (Flask for web framework)
- **Frontend**: HTML, CSS, and JavaScript (for user interface)
- **Data Storage**: CSV files (for storing accident data)
- **Machine Learning**: Scikit-learn for data cleaning and prediction
- **Geospatial Data**: GeoPandas for handling geospatial data
- **Data Visualization**: Folium for interactive maps, Matplotlib for static visualizations
- **Web Server**: Gunicorn (for serving the Flask application)



## Data Sources & Licensing

The accident data is sourced from [CrashMapper](https://crashmapper.org), which provides publicly available automobile, cyclist, and pedestrian accident data from New York City. 

## How to Use




## Future Improvements



