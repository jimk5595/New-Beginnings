document.addEventListener('DOMContentLoaded', () => {
    const ctaButton = document.getElementById('cta-button');

    if (ctaButton) {
        ctaButton.addEventListener('click', () => {
            console.log('CTA Button was clicked.');
            alert('Thank you for your interest!');
        });
    }
});