document.addEventListener('DOMContentLoaded', () => {
  const toggleButtons = document.querySelectorAll('[data-password-toggle]');
  toggleButtons.forEach((button) => {
    const targetId = button.getAttribute('data-target');
    const icon = button.querySelector('i');
    button.addEventListener('click', () => {
      const input = document.getElementById(targetId);
      if (!input) {
        return;
      }
      const isHidden = input.getAttribute('type') === 'password';
      input.setAttribute('type', isHidden ? 'text' : 'password');
      button.setAttribute('aria-expanded', String(isHidden));
      if (icon) {
        icon.classList.toggle('fa-eye', !isHidden);
        icon.classList.toggle('fa-eye-slash', isHidden);
      }
    });
  });

  const authForms = document.querySelectorAll('form[data-auth-form]');
  authForms.forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!form.checkValidity()) {
        return;
      }
      const primaryAction = form.querySelector('[data-primary-action]');
      if (!primaryAction) {
        return;
      }
      primaryAction.classList.add('is-loading');
      primaryAction.setAttribute('aria-busy', 'true');
      primaryAction.setAttribute('disabled', 'true');
    });
  });
});
