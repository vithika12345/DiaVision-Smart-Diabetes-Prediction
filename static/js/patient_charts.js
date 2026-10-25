// Patient Historical Health Progress Tracker Charts

function initPatientProgressCharts(historyData) {
  if (!window.Chart || !historyData || !historyData.length) return;

  // Chronological sort
  const sorted = [...historyData].reverse();
  const dates = sorted.map(d => d.prediction_date.substring(0, 16));
  
  // Extract glucose and BMI from features_json
  const glucoseVals = [];
  const bmiVals = [];
  const riskProbas = [];

  sorted.forEach(item => {
    try {
      const feat = JSON.parse(item.features_json || '{}');
      glucoseVals.push(feat.blood_glucose_level || null);
      bmiVals.push(feat.bmi || null);
      riskProbas.push(item.risk_probability || null);
    } catch (e) {
      glucoseVals.push(null);
      bmiVals.push(null);
      riskProbas.push(null);
    }
  });

  // Glucose History Chart
  const glucCtx = document.getElementById('chartPatientGlucose');
  if (glucCtx) {
    new Chart(glucCtx, {
      type: 'line',
      data: {
        labels: dates,
        datasets: [{
          label: 'Blood Glucose (mg/dL)',
          data: glucoseVals,
          borderColor: '#0d9488',
          backgroundColor: 'rgba(13, 148, 136, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 5,
          pointBackgroundColor: '#0d9488'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: false, grid: { color: '#f1f5f9' } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // Risk Probability History Chart
  const probCtx = document.getElementById('chartPatientRisk');
  if (probCtx) {
    new Chart(probCtx, {
      type: 'line',
      data: {
        labels: dates,
        datasets: [{
          label: 'Estimated Risk Probability (%)',
          data: riskProbas,
          borderColor: '#e11d48',
          backgroundColor: 'rgba(225, 29, 72, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 5,
          pointBackgroundColor: '#e11d48'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 100, grid: { color: '#f1f5f9' } },
          x: { grid: { display: false } }
        }
      }
    });
  }
}
