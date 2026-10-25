import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

NUMERICAL_FEATURES = ['age', 'bmi', 'HbA1c_level', 'blood_glucose_level']
CATEGORICAL_FEATURES = ['gender', 'smoking_history']
BINARY_FEATURES = ['hypertension', 'heart_disease']
ALL_FEATURES = ['gender', 'age', 'hypertension', 'heart_disease', 'smoking_history', 'bmi', 'HbA1c_level', 'blood_glucose_level']

def get_preprocessor():
    """
    Creates a scikit-learn ColumnTransformer for preprocessing diabetes dataset features.
    Handles numerical scaling, categorical encoding, and binary passthrough.
    """
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='No Info')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    binary_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, NUMERICAL_FEATURES),
            ('cat', categorical_transformer, CATEGORICAL_FEATURES),
            ('bin', binary_transformer, BINARY_FEATURES)
        ],
        remainder='drop'
    )
    return preprocessor

def clean_dataset(df):
    """
    Cleans raw dataframe, handles types, removes duplicates, and standardizes columns.
    """
    df = df.copy()
    
    # Strip column names
    df.columns = [c.strip() for c in df.columns]

    # Map expected column names if slight variations exist
    col_mapping = {
        'Gender': 'gender',
        'Age': 'age',
        'Hypertension': 'hypertension',
        'Heart_disease': 'heart_disease',
        'Heart Disease': 'heart_disease',
        'heart disease': 'heart_disease',
        'Smoking_history': 'smoking_history',
        'Smoking History': 'smoking_history',
        'smoking history': 'smoking_history',
        'BMI': 'bmi',
        'Bmi': 'bmi',
        'hba1c_level': 'HbA1c_level',
        'HbA1C_level': 'HbA1c_level',
        'HbA1c': 'HbA1c_level',
        'Hba1c': 'HbA1c_level',
        'Blood_glucose_level': 'blood_glucose_level',
        'Blood Glucose Level': 'blood_glucose_level',
        'blood glucose level': 'blood_glucose_level',
        'Glucose': 'blood_glucose_level',
        'Diabetes': 'diabetes',
        'Outcome': 'diabetes'
    }
    df.rename(columns=col_mapping, inplace=True)

    # Clean numeric fields
    for col in NUMERICAL_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    for col in BINARY_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Standardize categoricals
    if 'gender' in df.columns:
        df['gender'] = df['gender'].astype(str).str.strip().str.capitalize()
        # Replace unexpected with 'Other'
        valid_genders = {'Female', 'Male', 'Other'}
        df['gender'] = df['gender'].apply(lambda x: x if x in valid_genders else 'Other')

    if 'smoking_history' in df.columns:
        df['smoking_history'] = df['smoking_history'].astype(str).str.strip()
        valid_smoking = {'never', 'No Info', 'current', 'former', 'ever', 'not current'}
        df['smoking_history'] = df['smoking_history'].apply(lambda x: x if x in valid_smoking else 'No Info')

    return df
