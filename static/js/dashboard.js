// Diavision Dashboard Charts Initialization

function initDashboardCharts(data) {
  if (!window.Chart || !data) return;

  // Chart defaults for clean healthcare aesthetics
  Chart.defaults.font.family = "'Outfit', 'Inter', sans-serif";
  Chart.defaults.color = '#64748b';
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;

  // 1. Prediction Distribution (Doughnut)
  const predCtx = document.getElementById('chartPredDist');
  if (predCtx && data.pred_dist) {
    const labels = Object.keys(data.pred_dist);
    const values = Object.values(data.pred_dist);
    const bgColors = labels.map(l => l.includes('High') ? '#e11d48' : '#0d9488');

    new Chart(predCtx, {
      type: 'doughnut',
      data: {
        labels: labels.length ? labels : ['No Data'],
        datasets: [{
          data: values.length ? values : [1],
          backgroundColor: bgColors.length ? bgColors : ['#cbd5e1'],
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' }
        },
        cutout: '68%'
      }
    });
  }

  // 2. Age Distribution (Bar)
  const ageCtx = document.getElementById('chartAgeDist');
  if (ageCtx && data.age_dist) {
    new Chart(ageCtx, {
      type: 'bar',
      data: {
        labels: Object.keys(data.age_dist),
        datasets: [{
          label: 'Patients',
          data: Object.values(data.age_dist),
          backgroundColor: '#6366f1',
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // 3. Glucose Distribution (Bar)
  const glucCtx = document.getElementById('chartGlucoseDist');
  if (glucCtx && data.glucose_dist) {
    new Chart(glucCtx, {
      type: 'bar',
      data: {
        labels: Object.keys(data.glucose_dist),
        datasets: [{
          label: 'Patients',
          data: Object.values(data.glucose_dist),
          backgroundColor: ['#0d9488', '#14b8a6', '#f59e0b', '#e11d48'],
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // 4. BMI Distribution (Polar Area / Doughnut)
  const bmiCtx = document.getElementById('chartBmiDist');
  if (bmiCtx && data.bmi_dist) {
    new Chart(bmiCtx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(data.bmi_dist),
        datasets: [{
          data: Object.values(data.bmi_dist),
          backgroundColor: ['#93c5fd', '#10b981', '#f59e0b', '#f43f5e'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' }
        },
        cutout: '60%'
      }
    });
  }

  // 5. Risk by Age Group (Stacked Bar)
  const riskAgeCtx = document.getElementById('chartRiskByAge');
  if (riskAgeCtx && data.risk_by_age) {
    const ageGroups = Object.keys(data.risk_by_age);
    const lowRiskVals = ageGroups.map(g => (data.risk_by_age[g] && data.risk_by_age[g]['Lower Risk']) || 0);
    const highRiskVals = ageGroups.map(g => (data.risk_by_age[g] && data.risk_by_age[g]['Higher Risk']) || 0);

    new Chart(riskAgeCtx, {
      type: 'bar',
      data: {
        labels: ageGroups,
        datasets: [
          {
            label: 'Lower Risk',
            data: lowRiskVals,
            backgroundColor: '#0d9488',
            borderRadius: 4
          },
          {
            label: 'Higher Risk',
            data: highRiskVals,
            backgroundColor: '#e11d48',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, beginAtZero: true, grid: { color: '#f1f5f9' } }
        },
        plugins: {
          legend: { position: 'bottom' }
        }
      }
    });
  }

  // 6. Prediction Trends Over Time (Smooth Line)
  const trendCtx = document.getElementById('chartTrends');
  if (trendCtx && data.trends) {
    new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: Object.keys(data.trends),
        datasets: [{
          label: 'Predictions Logged',
          data: Object.values(data.trends),
          borderColor: '#0d9488',
          backgroundColor: 'rgba(13, 148, 136, 0.1)',
          fill: true,
          tension: 0.35,
          pointBackgroundColor: '#0d9488',
          pointRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
          x: { grid: { display: false } }
        }
      }
    });
  }
}
