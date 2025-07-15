/**
 * Risk Distribution Visualization Module
 * 
 * Handles the interactive visualization of Monte Carlo risk uncertainty analysis.
 * Creates histograms showing the distribution of possible risk outcomes.
 * 
 * Dependencies: Chart.js (loaded via CDN in template)
 * Usage: Call createRiskDistributionChart() with data from Python backend
 */

class RiskDistributionVisualizer {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.chart = null;
        this.options = {
            responsive: true,
            maintainAspectRatio: false,
            height: 300,
            colorScheme: {
                primary: '#4f46e5',
                secondary: '#60a5fa',
                success: '#10b981',
                warning: '#f59e0b',
                danger: '#ef4444'
            },
            ...options
        };
        
        if (!this.container) {
            console.error(`Container with ID "${containerId}" not found`);
        }
    }

    /**
     * Create the risk distribution chart
     * @param {Object} distributionData - Data from Python generate_risk_distribution_data()
     */
    createChart(distributionData) {
        if (!this.container) return;

        // Validate data structure
        if (!this.validateData(distributionData)) {
            console.error('Invalid distribution data provided');
            return;
        }

        // Clear existing content
        this.container.innerHTML = '';

        // Create chart container
        const chartContainer = document.createElement('div');
        chartContainer.className = 'risk-distribution-chart-container';
        chartContainer.innerHTML = `
            <canvas id="${this.containerId}-chart" width="400" height="300"></canvas>
        `;
        this.container.appendChild(chartContainer);

        // Create statistics summary
        const summaryContainer = this.createSummarySection(distributionData);
        this.container.appendChild(summaryContainer);

        // Initialize chart
        this.initializeChart(distributionData);
    }

    /**
     * Initialize Chart.js histogram
     */
    initializeChart(distributionData) {
        const canvas = document.getElementById(`${this.containerId}-chart`);
        const ctx = canvas.getContext('2d');

        const { histogram, statistics, axis_config } = distributionData;
        
        // Prepare data for Chart.js
        const chartData = this.prepareChartData(histogram, statistics);
        const chartOptions = this.prepareChartOptions(axis_config, statistics);

        // Create chart
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: chartOptions
        });
    }

    /**
     * Prepare data for Chart.js
     */
    prepareChartData(histogram, statistics) {
        const { counts, edges } = histogram;
        
        // Convert bin edges to labels (midpoints)
        const labels = [];
        const data = [];
        const backgroundColors = [];
        
        for (let i = 0; i < counts.length; i++) {
            const binMidpoint = (edges[i] + edges[i + 1]) / 2;
            labels.push((binMidpoint * 100).toFixed(1)); // Convert to percentage
            data.push(counts[i]);
            
            // Color code based on percentiles
            backgroundColors.push(this.getBinColor(binMidpoint, statistics));
        }

        return {
            labels: labels,
            datasets: [{
                label: 'Number of Scenarios',
                data: data,
                backgroundColor: backgroundColors,
                borderColor: this.options.colorScheme.primary,
                borderWidth: 1,
                borderRadius: 2,
                borderSkipped: false
            }]
        };
    }

    /**
     * Determine color for histogram bins based on risk level
     */
    getBinColor(riskValue, statistics) {
        const alpha = 0.7;
        
        if (riskValue < statistics.p25) {
            return `rgba(16, 185, 129, ${alpha})`; // Green - lower risk
        } else if (riskValue < statistics.p75) {
            return `rgba(96, 165, 250, ${alpha})`; // Blue - typical risk
        } else {
            return `rgba(239, 68, 68, ${alpha})`; // Red - higher risk
        }
    }

    /**
     * Prepare Chart.js options
     */
    prepareChartOptions(axisConfig, statistics) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Risk Distribution (${statistics.simulation_count || 'N'} simulations)`,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    color: '#374151'
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const scenarios = context.parsed.y;
                            const percentage = ((scenarios / (statistics.simulation_count || 1)) * 100).toFixed(1);
                            return `${scenarios} scenarios (${percentage}%)`;
                        },
                        title: (context) => {
                            return `Risk: ${context[0].label}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Infection Risk (%)',
                        font: {
                            weight: 'bold'
                        },
                        color: '#374151'
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Number of Scenarios',
                        font: {
                            weight: 'bold'
                        },
                        color: '#374151'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    beginAtZero: true
                }
            },
            animation: {
                duration: 800,
                easing: 'easeOutQuart'
            }
        };
    }

    /**
     * Create statistics summary section
     */
    createSummarySection(distributionData) {
        const { statistics, interpretation } = distributionData;
        
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'risk-distribution-summary';
        
        const meanPct = (statistics.mean * 100).toFixed(1);
        const medianPct = (statistics.median * 100).toFixed(1);
        
        summaryDiv.innerHTML = `
            <div class="risk-stats-grid">
                <div class="risk-stat">
                    <span class="stat-label">Mean:</span>
                    <span class="stat-value">${meanPct}%</span>
                </div>
                <div class="risk-stat">
                    <span class="stat-label">Median:</span>
                    <span class="stat-value">${medianPct}%</span>
                </div>
                <div class="risk-stat">
                    <span class="stat-label">Typical range:</span>
                    <span class="stat-value">${interpretation.typical_range}</span>
                </div>
            </div>
            <div class="risk-interpretation">
                <p><strong>What this shows:</strong> ${interpretation.summary}</p>
                <p class="uncertainty-explanation">${interpretation.uncertainty_explanation}</p>
            </div>
        `;
        
        return summaryDiv;
    }

    /**
     * Validate distribution data structure
     */
    validateData(data) {
        const requiredKeys = ['histogram', 'statistics', 'axis_config', 'interpretation'];
        
        for (const key of requiredKeys) {
            if (!(key in data)) {
                console.error(`Missing required key: ${key}`);
                return false;
            }
        }
        
        // Validate histogram structure
        const hist = data.histogram;
        if (!hist.counts || !hist.edges || hist.counts.length !== hist.edges.length - 1) {
            console.error('Invalid histogram data structure');
            return false;
        }
        
        return true;
    }

    /**
     * Destroy the chart (cleanup)
     */
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

/**
 * Global function to create risk distribution visualization
 * @param {string} containerId - ID of container element
 * @param {Object} distributionData - Data from Python backend
 * @param {Object} options - Optional configuration
 */
function createRiskDistributionChart(containerId, distributionData, options = {}) {
    const visualizer = new RiskDistributionVisualizer(containerId, options);
    visualizer.createChart(distributionData);
    return visualizer;
}

/**
 * Function to toggle uncertainty analysis display
 * @param {string} buttonId - ID of the toggle button
 * @param {string} containerId - ID of the container to toggle
 */
function toggleUncertaintyAnalysis(buttonId, containerId) {
    const button = document.getElementById(buttonId);
    const container = document.getElementById(containerId);
    
    if (!button || !container) {
        console.error('Button or container not found');
        return;
    }
    
    const isVisible = container.style.display !== 'none';
    
    if (isVisible) {
        // Hide
        container.style.display = 'none';
        button.textContent = 'How certain is this result?';
        button.classList.remove('active');
    } else {
        // Show
        container.style.display = 'block';
        button.textContent = 'Hide uncertainty analysis';
        button.classList.add('active');
        
        // If container has data attribute, create chart
        const distributionData = container.getAttribute('data-distribution');
        if (distributionData) {
            try {
                const data = JSON.parse(distributionData);
                createRiskDistributionChart(containerId, data);
            } catch (e) {
                console.error('Failed to parse distribution data:', e);
            }
        }
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        RiskDistributionVisualizer,
        createRiskDistributionChart,
        toggleUncertaintyAnalysis
    };
}