export function initPasswordValidation(formSelector = '#pane-register form') {
    const form = document.querySelector(formSelector);
    if (!form) return;

    const password1 = form.querySelector('[name="password1"]');
    const password2 = form.querySelector('[name="password2"]');
    if (!password1 || !password2) return;

    // Crear contenedor de feedback
    let feedback = form.querySelector('.password-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'password-feedback mt-2 small';
        password1.closest('.col-12,.mb-3').appendChild(feedback);
    }

    function validate() {
        const pass = password1.value;
        const checks = [
            { test: pass.length >= 8, text: '8+ caracteres' },
            { test: /[A-Z]/.test(pass), text: '1 mayúscula' },
            { test: /[0-9]/.test(pass), text: '1 número' },
            { test: pass && pass === password2.value, text: 'Coinciden' }
        ];

        const ok = checks.filter(c => c.test).map(c => `✓ ${c.text}`);
        const ko = checks.filter(c => !c.test).map(c => `✗ ${c.text}`);

        feedback.innerHTML = '';
        if (ok.length) feedback.innerHTML += `<div class="text-success"><strong>${ok.join(' · ')}</strong></div>`;
        if (ko.length) feedback.innerHTML += `<div class="text-danger"><strong>${ko.join(' · ')}</strong></div>`;

        password1.classList.toggle('is-valid', ok.length === 4);
        password1.classList.toggle('is-invalid', ko.length > 0 && pass.length > 0);
        password2.classList.toggle('is-valid', pass && pass === password2.value);
        password2.classList.toggle('is-invalid', password2.value && pass !== password2.value);
    }

    password1.addEventListener('input', validate);
    password2.addEventListener('input', validate);
    validate();
}