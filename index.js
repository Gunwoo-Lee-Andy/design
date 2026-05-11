document.addEventListener('DOMContentLoaded', () => {
    const checkboxes = document.querySelectorAll('.check-item input');
    const progressVal = document.getElementById('progress-val');
    const progressFill = document.getElementById('progress-fill');

    // Load saved state from LocalStorage
    const loadState = () => {
        const savedData = JSON.parse(localStorage.getItem('artistChecklistState') || '{}');
        checkboxes.forEach((cb, index) => {
            if (savedData[index]) {
                cb.checked = true;
            }
        });
        updateProgress();
    };

    // Calculate and update progress
    const updateProgress = () => {
        let totalWeight = 0;
        let completedWeight = 0;

        checkboxes.forEach(cb => {
            const weight = parseInt(cb.dataset.weight || 10);
            totalWeight += weight;
            if (cb.checked) {
                completedWeight += weight;
            }
        });

        const percentage = Math.round((completedWeight / totalWeight) * 100);
        progressVal.textContent = percentage;
        progressFill.style.width = `${percentage}%`;

        // Save to LocalStorage
        saveState();
    };

    // Save state to LocalStorage
    const saveState = () => {
        const state = {};
        checkboxes.forEach((cb, index) => {
            state[index] = cb.checked;
        });
        localStorage.setItem('artistChecklistState', JSON.stringify(state));
    };

    // Event Listeners
    checkboxes.forEach(cb => {
        cb.addEventListener('change', updateProgress);
    });

    // Smooth scroll for anchors
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Initialize
    loadState();
    
    // Model Viewer AR Support Check (Optional logging)
    const modelViewer = document.querySelector('model-viewer');
    modelViewer.addEventListener('ar-status', (event) => {
        if (event.detail.status === 'failed') {
            console.log('AR interaction failed or not supported on this device.');
        }
    });
});
