# Short Mackerel Distribution Prediction System

This project is a **university project** developed as a web-based system for predicting and analyzing the distribution of **short mackerel in the Upper Gulf of Thailand**.

The system combines fisheries data, marine environmental data, and weather data with Machine Learning techniques to support the analysis of short mackerel abundance and distribution.

The web application includes three main Machine Learning approaches:

- **Linear Regression** — predicts short mackerel quantity as a numerical value.
- **Random Forest Classification** — classifies predicted mackerel quantity into **LOW, MEDIUM, and HIGH** levels.
- **K-Means Clustering** — groups areas or environmental conditions with similar characteristics.

---

## System Process

The overall workflow of the system is:

1. **Collect historical short mackerel data** and related station information.
2. **Retrieve environmental and weather data from open-data APIs**.
3. **Clean and prepare the data**, including monthly aggregation and matching records by station, year, and month.
4. **Store the processed data in a MySQL database**.
5. **Train Machine Learning models** using historical fisheries and environmental variables.
6. **Generate predictions and analytical results** using Regression, Classification, and Clustering.
7. **Display the results through the web application** using tables, graphs, and a prediction dashboard.

---

## Data Variables

The project combines multiple types of data. Not every variable is used by every Machine Learning model.

### Fisheries Data
- **Short mackerel catch amount** — target quantity used for training and prediction
- **Fishing equipment / gear information**
- **Station / province**
- **Year**
- **Month**

### Marine Environmental Data
- **Sea Surface Temperature (SST)**
- **Chlorophyll-a**
- **Sea Surface Salinity (SSS)**

### Weather and Atmospheric Data
- **Rainfall**
- **Wind Speed**
- **Sea Level Pressure**
- **Air Temperature**
- **Wind Direction**

### Location Data
- **Latitude**
- **Longitude**
- **Water Depth**

---

# Web Application Screenshots

## 1. Homepage

The homepage introduces the project and provides access to the system's main Machine Learning and prediction features.

![Homepage](screenshots/01-homepage.png)

---

## 2. Data Management

This page is used to review and manage historical data by location, year, month, and related information.

![Short Mackerel Data Management](screenshots/02-mackerel-data-management.png)

---

## 3. Linear Regression

The Regression page uses historical fisheries, marine environmental, and weather data to estimate short mackerel quantity as a numerical prediction.

![Linear Regression](screenshots/03-regression.png)

---

## 4. Random Forest Classification

The Classification page predicts the short mackerel quantity level and classifies the result into **LOW, MEDIUM, or HIGH**.

![Random Forest Classification](screenshots/04-classification.png)

---

## 5. K-Means Clustering

The Clustering page groups records with similar environmental characteristics to support pattern and area analysis.

![K-Means Clustering](screenshots/05-clustering.png)

---

## 6. Prediction Dashboard

The Prediction Dashboard combines model outputs into a single interface for selecting prediction parameters and viewing the predicted short mackerel quantity and related analysis.

![Prediction Dashboard](screenshots/06-prediction-dashboard.png)

---


# Project Team & Responsibilities

## Theerapat Pokkaew

**Project Manager / Classification / Web Development**

- Project management and team coordination
- Random Forest Classification model development
- Design and development of the web application
- Development of Archive pages
- Database integration for historical data
- Home page development

---

## Sattaya Pokkaew

**Regression / Data Analyst**

- Linear Regression model development
- Dataset research and collection
- External API data collection
- Data preprocessing
- Data normalization
- Training data preparation

---

## Panyakorn Khaiwchoo

**Clustering / Data Analyst**

- K-Means Clustering model development
- Dataset research and collection
- External API data collection
- Data preprocessing
- Data normalization
- Training data preparation

---

# Required Libraries

Install the required Python libraries before running the Machine Learning and data-processing components of the project.

```bash
pip install pandas numpy scikit-learn mysql-connector-python pymysql joblib matplotlib scipy requests SQLAlchemy
```

### Python Libraries Used

- **pandas** — data loading, cleaning, preprocessing, and analysis
- **numpy** — numerical operations
- **scikit-learn** — Linear Regression, Random Forest Classification, K-Means Clustering, preprocessing, and model evaluation
- **mysql-connector-python** — connecting Python to MySQL
- **PyMySQL** — MySQL database connectivity
- **joblib** — saving and loading trained Machine Learning models
- **matplotlib** — data visualization and graphs
- **scipy** — scientific and statistical calculations
- **requests** — retrieving data from external APIs
- **SQLAlchemy** — database connection and data handling

### Required Software

- **Python**
- **PHP**
- **MySQL / MariaDB**
- **XAMPP** or another local Apache/PHP/MySQL web server

---
