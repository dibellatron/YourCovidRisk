/**
 * Debug utility for environment-aware logging
 * 
 * This module provides console logging that only outputs in development mode.
 * In production, these calls are effectively no-ops.
 * 
 * Usage:
 *   import { debugLog, debugWarn, debugError } from '/static/js/utils/debug.js';
 *   debugLog('This only logs in development');
 *   
 * Or for inline scripts in templates:
 *   {% if is_development %}console.log('Debug message');{% endif %}
 */

// Check if we're in development mode
// This will be set by the Flask template context
const IS_DEVELOPMENT = window.DEBUG === true || window.IS_DEVELOPMENT === true;

/**
 * Environment-aware console.log
 */
export function debugLog(...args) {
    if (IS_DEVELOPMENT) {
        console.log(...args);
    }
}

/**
 * Environment-aware console.warn
 */
export function debugWarn(...args) {
    if (IS_DEVELOPMENT) {
        console.warn(...args);
    }
}

/**
 * Environment-aware console.error
 */
export function debugError(...args) {
    if (IS_DEVELOPMENT) {
        console.error(...args);
    }
}

/**
 * Environment-aware console.info
 */
export function debugInfo(...args) {
    if (IS_DEVELOPMENT) {
        console.info(...args);
    }
}

/**
 * Environment-aware console.debug
 */
export function debugDebug(...args) {
    if (IS_DEVELOPMENT) {
        console.debug(...args);
    }
}

/**
 * Global debug object for non-module usage
 */
window.debug = {
    log: debugLog,
    warn: debugWarn,
    error: debugError,
    info: debugInfo,
    debug: debugDebug,
    isDevelopment: IS_DEVELOPMENT
};

// Set global flag for template use
window.IS_DEVELOPMENT = IS_DEVELOPMENT;