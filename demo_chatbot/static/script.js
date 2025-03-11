document.addEventListener('DOMContentLoaded', function() {
    const modelToggle = document.getElementById('modelToggle');
    const translationToggle = document.getElementById('translationToggle');
    const modelType = document.getElementById('modelType');
    const translationType = document.getElementById('translationType');
    const hawaiianInput = document.getElementById('hawaiianInput');
    const translationOutput = document.getElementById('translationOutput');
    const translateBtn = document.getElementById('translateBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    
    // Toggle model type (fast/best)
    modelToggle.addEventListener('change', function() {
        modelType.textContent = this.checked ? 'Best Model' : 'Fast Model';
    });
    
    // Toggle translation type (regular/natural)
    translationToggle.addEventListener('change', function() {
        translationType.textContent = this.checked ? 'Natural' : 'Regular';
    });
    
    // Translation request
    translateBtn.addEventListener('click', function() {
        const hawaiianText = hawaiianInput.value.trim();
        
        if (!hawaiianText) {
            alert('Please enter some Hawaiian text to translate.');
            return;
        }
        
        // Clear previous translation and show loading indicator
        translationOutput.value = '';
        loadingIndicator.style.display = 'block';
        translateBtn.disabled = true;
        
        // Prepare request payload
        const payload = {
            hawaiianText: hawaiianText,
            modelType: modelToggle.checked ? 'best' : 'fast',
            naturalTranslation: translationToggle.checked
        };
        
        // Set up event source for streaming response
        const eventSource = new EventSource(`/translate?data=${encodeURIComponent(JSON.stringify(payload))}`);
        
        // Handle streaming translation updates
        eventSource.addEventListener('message', function(event) {
            try {
                const data = JSON.parse(event.data);
                
                if (data.translation) {
                    // Show final translation
                    translationOutput.value = data.translation;
                }
                
                if (data.error) {
                    translationOutput.value = `Error: ${data.error}`;
                    eventSource.close();
                    loadingIndicator.style.display = 'none';
                    translateBtn.disabled = false;
                }
                
                if (data.done) {
                    // Close connection when done
                    eventSource.close();
                    loadingIndicator.style.display = 'none';
                    translateBtn.disabled = false;
                }
            } catch (error) {
                console.error('Error parsing event data:', error);
            }
        });
        
        // Handle connection errors
        eventSource.addEventListener('error', function() {
            eventSource.close();
            loadingIndicator.style.display = 'none';
            translateBtn.disabled = false;
            
            if (translationOutput.value === '') {
                translationOutput.value = 'An error occurred during translation. Please try again.';
            }
        });
        
        // Fallback for browsers that don't handle SSE well
        setTimeout(() => {
            if (translationOutput.value === '' && loadingIndicator.style.display === 'block') {
                fetch('/translate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.translation) {
                        translationOutput.value = data.translation;
                    } else if (data.error) {
                        translationOutput.value = `Error: ${data.error}`;
                    } else {
                        translationOutput.value = 'Translation completed, but no result was returned.';
                    }
                })
                .catch(error => {
                    translationOutput.value = 'An error occurred during translation. Please try again.';
                    console.error('Fetch error:', error);
                })
                .finally(() => {
                    loadingIndicator.style.display = 'none';
                    translateBtn.disabled = false;
                    if (eventSource.readyState !== 2) { // If not closed
                        eventSource.close();
                    }
                });
            }
        }, 10000); // 10 second timeout for SSE
    });
});