/**
 * Analytics Tracking Utility for COVID Risk Calculator
 * 
 * This module provides centralized Google Analytics event tracking
 * to understand user behavior and app usage patterns.
 * 
 * Tracking ID: G-QS2H07PT34
 */

// Check if gtag is available
const isAnalyticsEnabled = typeof gtag !== 'undefined';

/**
 * Track page views
 */
export function trackPageView(pageName, additionalParams = {}) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'page_view', {
        page_title: pageName,
        page_location: window.location.href,
        page_path: window.location.pathname,
        ...additionalParams
    });
}

/**
 * Track calculator usage
 */
export function trackCalculatorUsage(calculatorType, eventAction, additionalParams = {}) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', eventAction, {
        event_category: 'calculator_usage',
        event_label: calculatorType,
        ...additionalParams
    });
}

/**
 * Track form interactions
 */
export function trackFormInteraction(formName, fieldName, action, value = null) {
    if (!isAnalyticsEnabled) return;
    
    const eventParams = {
        event_category: 'form_interaction',
        event_label: `${formName}_${fieldName}`,
        form_name: formName,
        field_name: fieldName,
        action: action
    };
    
    if (value !== null) {
        eventParams.field_value = value;
    }
    
    gtag('event', `form_${action}`, eventParams);
}

/**
 * Track button clicks
 */
export function trackButtonClick(buttonName, buttonType = 'button', additionalParams = {}) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'click', {
        event_category: 'button_interaction',
        event_label: buttonName,
        button_type: buttonType,
        ...additionalParams
    });
}

/**
 * Track navigation events
 */
export function trackNavigation(destination, source = 'unknown') {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'navigate', {
        event_category: 'navigation',
        event_label: destination,
        source: source
    });
}

/**
 * Track calculator results
 */
export function trackCalculatorResult(calculatorType, resultData) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'calculator_result', {
        event_category: 'calculator_completion',
        event_label: calculatorType,
        calculator_type: calculatorType,
        risk_level: resultData.riskLevel || 'unknown',
        result_value: resultData.resultValue || null
    });
}

/**
 * Track slider interactions
 */
export function trackSliderChange(sliderName, value, calculatorType) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'slider_change', {
        event_category: 'input_interaction',
        event_label: `${calculatorType}_${sliderName}`,
        slider_name: sliderName,
        slider_value: value,
        calculator_type: calculatorType
    });
}

/**
 * Track dropdown selections
 */
export function trackDropdownSelection(dropdownName, selectedValue, calculatorType) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'dropdown_select', {
        event_category: 'input_interaction',
        event_label: `${calculatorType}_${dropdownName}`,
        dropdown_name: dropdownName,
        selected_value: selectedValue,
        calculator_type: calculatorType
    });
}

/**
 * Track advanced settings usage
 */
export function trackAdvancedSettings(calculatorType, settingName, value) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'advanced_setting', {
        event_category: 'advanced_usage',
        event_label: `${calculatorType}_${settingName}`,
        calculator_type: calculatorType,
        setting_name: settingName,
        setting_value: value
    });
}

/**
 * Track FAQ interactions
 */
export function trackFAQInteraction(questionTitle, action = 'open') {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', `faq_${action}`, {
        event_category: 'faq_interaction',
        event_label: questionTitle,
        faq_question: questionTitle
    });
}

/**
 * Track errors and issues
 */
export function trackError(errorType, errorMessage, context = '') {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'error', {
        event_category: 'app_error',
        event_label: errorType,
        error_type: errorType,
        error_message: errorMessage,
        error_context: context
    });
}

/**
 * Track time spent on page
 */
export function trackTimeOnPage(pageName, timeSpent) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'time_on_page', {
        event_category: 'engagement',
        event_label: pageName,
        page_name: pageName,
        time_spent_seconds: timeSpent
    });
}

/**
 * Track repeated exposure calculator usage
 */
export function trackRepeatedExposure(exposureType, frequency, riskLevel) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', 'repeated_exposure_calc', {
        event_category: 'repeated_exposure',
        event_label: exposureType,
        exposure_type: exposureType,
        frequency: frequency,
        risk_level: riskLevel
    });
}

/**
 * Track test calculator specific events
 */
export function trackTestCalculator(action, testData = {}) {
    if (!isAnalyticsEnabled) return;
    
    gtag('event', `test_calc_${action}`, {
        event_category: 'test_calculator',
        event_label: action,
        test_type: testData.testType || 'unknown',
        test_result: testData.testResult || 'unknown',
        symptoms: testData.symptoms || 'unknown',
        num_tests: testData.numTests || 1
    });
}

// Global analytics object for easy access from templates
window.analytics = {
    trackPageView,
    trackCalculatorUsage,
    trackFormInteraction,
    trackButtonClick,
    trackNavigation,
    trackCalculatorResult,
    trackSliderChange,
    trackDropdownSelection,
    trackAdvancedSettings,
    trackFAQInteraction,
    trackError,
    trackTimeOnPage,
    trackRepeatedExposure,
    trackTestCalculator
};

// Auto-track page load time
window.addEventListener('load', function() {
    const pageLoadTime = performance.now();
    if (pageLoadTime > 0) {
        gtag('event', 'page_load_time', {
            event_category: 'performance',
            value: Math.round(pageLoadTime)
        });
    }
});

// Track page unload to measure time spent
let pageStartTime = Date.now();
window.addEventListener('beforeunload', function() {
    const timeSpent = Math.round((Date.now() - pageStartTime) / 1000);
    if (timeSpent > 5) { // Only track if user spent more than 5 seconds
        trackTimeOnPage(document.title, timeSpent);
    }
});