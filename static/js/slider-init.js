// Glue code extracted from test_calculator.html to wrap selects/inputs and handle validation
document.addEventListener('DOMContentLoaded', function() {
  // Add select-wrapper to all select elements that don't have it
  document.querySelectorAll('select').forEach(function(select) {
    // Check if this select is already wrapped
    if (!select.parentElement.classList.contains('select-wrapper')) {
      // Create wrapper
      var wrapper = document.createElement('div');
      wrapper.className = 'select-wrapper';

      // Create validation message element
      var validationMessage = document.createElement('span');
      validationMessage.className = 'validation-message';
      validationMessage.textContent = 'Please select an option';

      // Replace select with wrapper containing select
      select.parentNode.insertBefore(wrapper, select);
      wrapper.appendChild(select);
      wrapper.appendChild(validationMessage);
    }

    // Improve validation message persistence
    select.addEventListener('invalid', function(e) {
      // Prevent default validation popup
      e.preventDefault();

      // Add custom validation class
      this.classList.add('validation-error');

      // Clear validation state when user interacts with the field
      this.addEventListener('change', function() {
        this.classList.remove('validation-error');
      }, { once: true });
    });
  });

  // Improve validation for number inputs (particularly in Advanced fields)
  document.querySelectorAll('input[type="number"]').forEach(function(input) {
    // Create a wrapper if it doesn't exist
    if (!input.parentElement.classList.contains('input-wrapper')) {
      var wrapper = document.createElement('div');
      wrapper.className = 'input-wrapper';

      // Create validation message element
      var validationMessage = document.createElement('span');
      validationMessage.className = 'validation-message';

      // Replace input with wrapper containing input
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
      wrapper.appendChild(validationMessage);
    }

    // Handle validation errors
    input.addEventListener('invalid', function(e) {
      // Prevent default validation popup
      e.preventDefault();

      // Set the validation message
      var validationMessage = this.nextElementSibling;
      if (validationMessage && validationMessage.classList.contains('validation-message')) {
        validationMessage.textContent = this.validationMessage;
      }

      // Add custom validation class
      this.classList.add('validation-error');

      // Clear validation state when user focuses on the field
      this.addEventListener('focus', function() {
        this.classList.remove('validation-error');
      }, { once: true });
    });
  });
});
