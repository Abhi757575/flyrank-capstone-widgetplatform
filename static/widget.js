(function() {
    // 1. Identify the script element and extract configuration parameters
    const script = document.currentScript;
    if (!script) {
        console.error("FlyRank Widget: Unable to find currentScript element.");
        return;
    }

    const scriptUrl = new URL(script.src);
    const widgetId = scriptUrl.searchParams.get("id") || script.getAttribute("data-widget-id");
    
    if (!widgetId) {
        console.error("FlyRank Widget: Missing widget 'id' parameter in script source URL or data-widget-id attribute.");
        return;
    }

    // Determine the API base URL (relative to the script source origin)
    const apiBaseUrl = scriptUrl.origin;

    // 2. Fetch the widget configuration from the backend
    fetch(`${apiBaseUrl}/api/widgets/${widgetId}/config`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(config => {
            renderWidget(config);
        })
        .catch(error => {
            console.error("FlyRank Widget: Failed to load widget configuration.", error);
        });

    // 3. Render the widget HTML and apply beautiful CSS scoped styles
    function renderWidget(config) {
        // Create container div where the script is located
        const container = document.createElement("div");
        container.className = `flyrank-widget-container flyrank-widget-${config.id}`;
        
        // Inject scoped CSS styling to avoid clashes with the host website stylesheet
        const style = document.createElement("style");
        style.textContent = `
            .flyrank-widget-container {
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background: #111827;
                color: #f9fafb;
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 24px;
                max-width: 400px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                box-sizing: border-box;
                margin: 20px auto;
                transition: all 0.3s ease;
            }
            .flyrank-widget-container * {
                box-sizing: border-box;
            }
            .flyrank-widget-title {
                font-size: 1.25rem;
                font-weight: 700;
                margin-top: 0;
                margin-bottom: 8px;
                color: #10b981;
            }
            .flyrank-widget-desc {
                font-size: 0.875rem;
                color: #9ca3af;
                margin-bottom: 20px;
                line-height: 1.4;
            }
            .flyrank-widget-group {
                margin-bottom: 16px;
                text-align: left;
            }
            .flyrank-widget-label {
                display: block;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #d1d5db;
                margin-bottom: 6px;
            }
            .flyrank-widget-input {
                width: 100%;
                background: #1f2937;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 10px 12px;
                color: #ffffff;
                font-size: 0.875rem;
                transition: border-color 0.2s, box-shadow 0.2s;
            }
            .flyrank-widget-input:focus {
                outline: none;
                border-color: #10b981;
                box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
            }
            .flyrank-widget-btn {
                width: 100%;
                background: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-size: 0.875rem;
                font-weight: 600;
                cursor: pointer;
                transition: background-color 0.2s, transform 0.1s;
                margin-top: 8px;
            }
            .flyrank-widget-btn:hover {
                background: #059669;
            }
            .flyrank-widget-btn:active {
                transform: scale(0.98);
            }
            .flyrank-widget-btn:disabled {
                background: #374151;
                color: #9ca3af;
                cursor: not-allowed;
            }
            .flyrank-widget-alert {
                padding: 12px;
                border-radius: 6px;
                font-size: 0.875rem;
                margin-top: 16px;
                display: none;
                line-height: 1.4;
            }
            .flyrank-widget-alert-success {
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid #10b981;
                color: #34d399;
            }
            .flyrank-widget-alert-error {
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid #ef4444;
                color: #f87171;
            }
        `;
        document.head.appendChild(style);

        // Build the HTML Form Structure
        let fieldsHtml = '';
        config.fields.forEach(field => {
            const reqStar = field.required ? ' <span style="color:#ef4444">*</span>' : '';
            const placeholder = field.placeholder ? `placeholder="${field.placeholder}"` : '';
            const requiredAttr = field.required ? 'required' : '';
            
            let inputFieldHtml = '';
            
            if (field.type === 'textarea') {
                inputFieldHtml = `<textarea name="${field.name}" class="flyrank-widget-input" rows="3" ${placeholder} ${requiredAttr}></textarea>`;
            } else if (field.type === 'select' && field.options) {
                let optionsHtml = '';
                field.options.forEach(opt => {
                    optionsHtml += `<option value="${opt}">${opt}</option>`;
                });
                inputFieldHtml = `
                    <select name="${field.name}" class="flyrank-widget-input" ${requiredAttr}>
                        <option value="">Select option...</option>
                        ${optionsHtml}
                    </select>
                `;
            } else {
                // Default to standard input type (text, email, number)
                inputFieldHtml = `<input type="${field.type}" name="${field.name}" class="flyrank-widget-input" ${placeholder} ${requiredAttr}>`;
            }

            fieldsHtml += `
                <div class="flyrank-widget-group">
                    <label class="flyrank-widget-label">${field.label}${reqStar}</label>
                    ${inputFieldHtml}
                </div>
            `;
        });

        // Add Honeypot spam protection field (hidden from screen readers and styling)
        fieldsHtml += `
            <input type="text" name="_honeypot" style="display:none !important;" tabindex="-1" autocomplete="off" placeholder="leave this empty">
        `;

        container.innerHTML = `
            <form class="flyrank-widget-form">
                <div class="flyrank-widget-title">${config.title || 'Get in Touch'}</div>
                <div class="flyrank-widget-desc">${config.description || 'Fill out the form below.'}</div>
                
                <div class="flyrank-widget-fields">
                    ${fieldsHtml}
                </div>
                
                <button type="submit" class="flyrank-widget-btn">${config.button_text || 'Submit'}</button>
                <div class="flyrank-widget-alert flyrank-widget-alert-success"></div>
                <div class="flyrank-widget-alert flyrank-widget-alert-error"></div>
            </form>
        `;

        // Inject widget into DOM where script tag is located
        script.parentNode.insertBefore(container, script);

        // Bind Submit Handler
        const form = container.querySelector(".flyrank-widget-form");
        const submitBtn = container.querySelector(".flyrank-widget-btn");
        const successAlert = container.querySelector(".flyrank-widget-alert-success");
        const errorAlert = container.querySelector(".flyrank-widget-alert-error");

        form.addEventListener("submit", function(e) {
            e.preventDefault();
            
            // Hide previous alerts
            successAlert.style.display = "none";
            errorAlert.style.display = "none";

            // Disable submit button & show loading state
            submitBtn.disabled = true;
            const originalBtnText = submitBtn.textContent;
            submitBtn.textContent = "Sending...";

            // Serialize Form Data
            const formData = new FormData(form);
            const payload = {
                widget_id: config.id
            };
            
            formData.forEach((value, key) => {
                payload[key] = value;
            });

            // Send payload to backend
            fetch(`${apiBaseUrl}/api/submissions`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            })
            .then(async response => {
                const result = await response.json().catch(() => ({}));
                if (!response.ok) {
                    throw new Error(result.detail || "Submission failed. Please try again.");
                }
                return result;
            })
            .then(data => {
                // Show success
                successAlert.textContent = data.message || "Thank you! Your submission was recorded.";
                successAlert.style.display = "block";
                form.reset();
            })
            .catch(error => {
                // Show error
                errorAlert.textContent = error.message;
                errorAlert.style.display = "block";
            })
            .finally(() => {
                // Restore button state
                submitBtn.disabled = false;
                submitBtn.textContent = originalBtnText;
            });
        });
    }
})();
