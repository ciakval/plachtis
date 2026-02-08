/* Prevent double form submissions by disabling submit button after first click */

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('form[method="post"]').forEach(form => {
        form.addEventListener('submit', function () {
            const btn = this.querySelector('[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.textContent = btn.dataset.loadingText || 'Submitting…';
            }
        });
    });
});

