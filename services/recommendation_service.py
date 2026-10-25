def get_personalized_recommendations(features, prediction_result):
    """
    Generates structured, clinically aligned, evidence-informed personalized health recommendations
    based on patient measurements, prediction category, and clinical risk rules.
    """
    category = prediction_result.get('prediction_category', 'Lower Risk')
    probability = prediction_result.get('risk_probability', 0.0)
    
    age = float(features.get('age', 0))
    bmi = float(features.get('bmi', 0))
    glucose = float(features.get('blood_glucose_level', 0))
    hba1c = float(features.get('HbA1c_level', 0))
    hypertension = int(features.get('hypertension', 0))
    heart_disease = int(features.get('heart_disease', 0))
    smoking = str(features.get('smoking_history', 'No Info')).lower()

    # 1. Critical & Smart Health Alerts
    smart_alerts = []
    if glucose >= 300:
        smart_alerts.append({
            'level': 'danger',
            'title': 'Urgent Clinical Review Required',
            'message': f'Blood glucose measurement of {glucose} mg/dL is critically high (>= 300 mg/dL). Seek immediate consultation with a qualified physician or healthcare facility for evaluation of potential acute metabolic complications.'
        })
    elif glucose >= 200:
        smart_alerts.append({
            'level': 'warning',
            'title': 'Significant Glucose Elevation',
            'message': f'Blood glucose of {glucose} mg/dL meets clinical criteria indicative of potential diabetes or marked hyperglycemia. A formal diagnostic fasting glucose or HbA1c laboratory confirmation is strongly recommended.'
        })
    elif glucose < 70 and glucose > 0:
        smart_alerts.append({
            'level': 'warning',
            'title': 'Hypoglycemia Caution',
            'message': f'Blood glucose reading of {glucose} mg/dL is below normal threshold (< 70 mg/dL). If you experience shakiness, sweating, or dizziness, seek medical guidance promptly.'
        })

    if hba1c >= 6.5:
        smart_alerts.append({
            'level': 'warning',
            'title': 'Elevated Glycated Hemoglobin (HbA1c)',
            'message': f'HbA1c of {hba1c}% is at or above the established clinical screening threshold of 6.5%. Please consult your doctor for diagnostic confirmation and individualized guidance.'
        })

    # 2. Prediction Summary Explanation
    if category == 'Higher Risk':
        summary_explanation = (
            f"The predictive algorithm identifies clinical indicators associated with an elevated probability ({probability}%) of diabetes. "
            "This is an educational risk evaluation based on population data patterns, NOT a confirmed medical diagnosis. "
            "A physician should evaluate your full clinical profile using certified laboratory testing."
        )
    else:
        summary_explanation = (
            f"The predictive model indicates a lower estimated risk ({probability}%) based on your currently entered parameters. "
            "Please note that a lower prediction does not guarantee absolute immunity from diabetes. "
            "Maintaining proactive wellness habits and routine health checkups remains essential."
        )

    # 3. Recommended Actions ("What Should I Do?")
    actions = [
        {
            'icon': 'calendar-check',
            'title': 'Schedule Professional Consultation',
            'desc': 'Discuss these screening insights and your full health background with your family doctor or endocrinologist.' if category == 'Higher Risk' else 'Continue regular annual preventive health checkups and routine metabolic screenings.'
        },
        {
            'icon': 'utensils',
            'title': 'Adopt Fiber-Rich, Balanced Meals',
            'desc': 'Incorporate fresh vegetables, whole grains, lentils, and lean proteins in consistent portions to stabilize blood glucose fluctuations.'
        },
        {
            'icon': 'droplet',
            'title': 'Prioritize Pure Water Hydration',
            'desc': 'Choose plain water or unsweetened infusions throughout the day instead of sweetened sodas, packaged juices, or sugary teas.'
        },
        {
            'icon': 'activity',
            'title': 'Daily Moderate Movement',
            'desc': 'Engage in at least 25 to 30 minutes of comfortable, moderate physical activity (such as brisk walking) on most days.'
        },
        {
            'icon': 'moon',
            'title': 'Consistent Sleep Rest Cycle',
            'desc': 'Maintain 7 to 8 hours of restorative sleep each night, as irregular sleep impairs glucose regulation and insulin sensitivity.'
        },
        {
            'icon': 'clipboard',
            'title': 'Maintain a Simple Health Log',
            'desc': 'Track routine blood pressure, weight, and fasting blood sugar periodically to monitor long-term trends.'
        }
    ]

    # 4. Habits to Limit or Avoid ("What Should I Avoid?")
    avoid_list = [
        {
            'title': 'Sugary Drinks & High-Glycemic Sweets',
            'desc': 'Limit sodas, commercial packaged fruit drinks, sweetened syrups, and refined bakery confections that cause rapid glucose spikes.'
        },
        {
            'title': 'Prolonged Sedentary Time',
            'desc': 'Avoid sitting continuously for longer than 45–60 minutes. Take brief 2-minute standing or walking breaks.'
        },
        {
            'title': 'Crash Diets & Unverified "Cures"',
            'desc': 'Avoid extreme starvation plans or unverified online herbal diabetes cures that lack scientific validation.'
        },
        {
            'title': 'Self-Altering Prescribed Medications',
            'desc': 'Never initiate, discontinue, or alter dosages of any medication without direct clinical guidance from your physician.'
        },
        {
            'title': 'Tobacco and Smoking Products',
            'desc': 'Avoid smoking or tobacco use; nicotine damages endothelial function and exacerbates insulin resistance.' if smoking in ['current', 'ever'] else 'Continue to steer clear of active and secondhand tobacco exposure.'
        },
        {
            'title': 'False Complacency from Normal Readings',
            'desc': 'Never assume a single favorable reading means preventive lifestyle choices are no longer necessary.'
        }
    ]

    # 5. Personalized Exercise Recommendations
    # Consider age, mobility, BMI, and cardiovascular comorbidity
    if heart_disease == 1 or age >= 65:
        exercise_intensity = "Gentle & Supervised"
        exercise_guidance = (
            "Because of cardiovascular history or age considerations, begin with gentle, low-impact activities. "
            "Discuss safe target heart rates and exertion levels with your physician prior to intensifying any routine."
        )
        exercise_activities = [
            {'name': 'Comfortable Walking', 'duration': '15–20 minutes daily on a flat, even surface.'},
            {'name': 'Gentle Chair Yoga / Stretching', 'duration': '10 minutes daily for joint mobility.'},
            {'name': 'Low-Impact Water Aerobics', 'duration': '2 times a week, gentle on joints.'}
        ]
    elif bmi >= 30:
        exercise_intensity = "Low-Impact & Joint-Friendly"
        exercise_guidance = (
            "Focus on sustainable low-impact aerobic activities that protect knees and joints while burning steady energy. "
            "Work gradually toward the public health benchmark of 150 minutes per week."
        )
        exercise_activities = [
            {'name': 'Brisk Walking', 'duration': '25–30 minutes, 5 days per week.'},
            {'name': 'Stationary Cycling', 'duration': '20 minutes at moderate resistance.'},
            {'name': 'Light Resistance Bands', 'duration': '2 days per week for core muscle tone.'}
        ]
    else:
        exercise_intensity = "Moderate Dynamic Routine"
        exercise_guidance = (
            "Aim for at least 150 minutes of moderate-intensity aerobic physical activity per week, "
            "supplemented with basic muscle-strengthening exercises on two non-consecutive days."
        )
        exercise_activities = [
            {'name': 'Brisk Walking / Jogging', 'duration': '30 minutes, 5 days per week.'},
            {'name': 'Cycling / Swimming', 'duration': '30–45 minutes, 2–3 times per week.'},
            {'name': 'Bodyweight Exercises', 'duration': 'Squats, wall-pushups, or light dumbbells 2x weekly.'}
        ]

    # 6. Personalized Food Guidance (Incorporating authentic Indian balanced meal examples)
    diet_guidance = {
        'intro': 'Prioritize balanced nutrient distribution, fiber density, and consistent meal timings. A plate model emphasizing 50% non-starchy vegetables, 25% whole grains, and 25% healthy protein provides steady glycemic control.',
        'indian_meal_examples': [
            {
                'meal': 'Balanced Breakfast',
                'example': 'Vegetable oats upma, or 2 small multi-grain/methi rotis with a bowl of sprouted moong salad, or steamed vegetable idlis with sambar.'
            },
            {
                'meal': 'Balanced Lunch',
                'example': '1–2 whole wheat / jowar rotis OR a measured portion of brown/steamed rice, paired with a generous bowl of yellow dal (toor/moong), spinach or bottle gourd sabzi, and fresh cucumber salad.'
            },
            {
                'meal': 'Mid-Day Snack',
                'example': 'A handful of unsalted roasted chana, a few walnuts/almonds, or a cup of warm buttermilk (chaas) infused with cumin and mint.'
            },
            {
                'meal': 'Nutritious Dinner',
                'example': 'Light paneer/tofu and vegetable stir-fry, or mixed dal khichdi with plenty of vegetables, accompanied by a small bowl of fresh homemade curd.'
            }
        ],
        'principles': [
            'Portion Awareness: Measure rice and roti portions rather than unlimited servings.',
            'Fiber First: Begin meals with fresh salad or sabzi to slow gastric emptying and blunt post-meal glucose surges.',
            'Beverage Mindfulness: Replace sweetened chai or fruit juices with water, lemon water, or herbal green tea without sugar.'
        ]
    }

    # 7. Measurement-Specific Observations
    measurement_notes = []
    if bmi >= 30:
        measurement_notes.append(f"Elevated BMI ({bmi:.1f} kg/m²): Even a gradual 5% to 7% reduction in weight through sustained dietary habits can substantially improve insulin sensitivity.")
    elif bmi >= 25:
        measurement_notes.append(f"Overweight Category BMI ({bmi:.1f} kg/m²): Maintaining active physical habits helps prevent progression into higher metabolic risk tiers.")
    
    if glucose >= 140:
        measurement_notes.append(f"Glucose Measurement ({glucose} mg/dL): Appears above standard baseline. A formal fasting blood glucose and HbA1c test is recommended.")
    
    if hba1c >= 5.7:
        measurement_notes.append(f"HbA1c Reading ({hba1c}%): Suggests sustained glycemic levels in prediabetes or diabetes range over the past 2–3 months.")

    if hypertension == 1:
        measurement_notes.append("Hypertension noted: Monitor sodium intake, aim for DASH-style dietary habits, and follow your physician's blood pressure guidelines.")

    return {
        'prediction_category': category,
        'risk_probability': probability,
        'summary_explanation': summary_explanation,
        'smart_alerts': smart_alerts,
        'recommended_actions': actions,
        'habits_to_avoid': avoid_list,
        'exercise_plan': {
            'intensity': exercise_intensity,
            'guidance': exercise_guidance,
            'activities': exercise_activities
        },
        'diet_guidance': diet_guidance,
        'measurement_notes': measurement_notes,
        'medical_disclaimer': (
            "Diavision is an educational machine learning decision-support prototype. "
            "Its predictions are not a medical diagnosis. Health recommendations are general educational information "
            "and do not replace consultation with a qualified healthcare professional. "
            "Do not change prescribed medications based on this application."
        )
    }
