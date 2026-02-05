// Function to clear browser cache
function clearBrowserCache() {
    // Call the server-side cache clearing endpoint
    $.get('/clear_cache', function (data) {
        // Clear client-side storage
        localStorage.clear();
        sessionStorage.clear();

        // Force reload without cache
        window.location.reload(true);
    });
}

// Function to log errors to backend
function logErrorToBackend(message, source, stack) {
    $.ajax({
        url: '/log_frontend_error',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            message: message,
            source: source || 'browser',
            stack: stack
        }),
        error: function (xhr, status, error) {
            // If logging fails, at least log to console
            console.error('Failed to log error to backend:', error);
        }
    });
}

// Setup global error handler
window.onerror = function (message, source, lineno, colno, error) {
    logErrorToBackend(message, source, error ? error.stack : null);
    return false; // Let default error handler run as well
};

$(document).ready(function () {
    let processing = false;
    let decision = null;
    let processingComplete = false;

    // Clear any cached data in localStorage
    localStorage.clear();
    sessionStorage.clear();

    // Initialize empty fields with placeholder
    $('.json-field-value').text('-');

    // Toggle button for processing
    $('#processing-toggle').click(function () {
        if (!processing) {
            // Start processing
            $.get('/start_processing', function (data) {
                // Processing started
                processing = true;
                processingComplete = false; // Reset processing complete flag

                // Update button appearance
                $('#processing-toggle')
                    .removeClass('btn-primary')
                    .addClass('btn-danger')
                    .find('#processing-toggle-text')
                    .text('Stop Processing');

                // Start the intervals for automatic updates
                // Clear any existing intervals first
                if (progressInterval) clearInterval(progressInterval);
                if (objectInterval) clearInterval(objectInterval);
                if (processedListInterval) clearInterval(processedListInterval);

                // Set new intervals
                progressInterval = setInterval(updateProgress, 1000);
                objectInterval = setInterval(updateObject, 1000);
                processedListInterval = setInterval(updateProcessedList, 5000);

                // Immediately update to show current state
                updateProgress();
                updateObject();
                updateProcessedList();
            });
        } else {
            // Stop processing
            $.get('/stop_processing', function (data) {
                // Processing stopped
                processing = false;

                // Update button appearance
                $('#processing-toggle')
                    .removeClass('btn-danger')
                    .addClass('btn-primary')
                    .find('#processing-toggle-text')
                    .text('Start Processing');

                // Stop all automatic updates
                if (progressInterval) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                }
                if (objectInterval) {
                    clearInterval(objectInterval);
                    objectInterval = null;
                }
                if (processedListInterval) {
                    clearInterval(processedListInterval);
                    processedListInterval = null;
                }
            });
        }
    });

    function updateProgress() {
        $.get('/progress', function (data) {
            // Update both progress bars
            $('#total-progress').css('width', data.total_progress.toFixed(2) + '%');
            $('#file-progress').css('width', data.file_progress.toFixed(2) + '%');

            // Update the file index information
            if (data.total_files > 0) {
                $('#file-progress-text').text(
                    `File ${data.current_file_index} of ${data.total_files} (${data.total_progress.toFixed(2)}%)`
                );
            }

            // Update current file object progress
            if (data.total_objects > 0) {
                let objectText = `Object ${data.current_object_index} of ${data.total_objects}`;
                $('#object-progress-text').text(
                    `${objectText} (${data.file_progress.toFixed(2)}%)`
                );
            }

            // Check if processing is complete using the flag from the server
            if (data.processing_complete && processing) {
                // Server reported processing is complete
                processing = false;
                processingComplete = true; // Mark processing as complete to keep the last object

                // Get the final object one more time to ensure we have the latest
                $.get('/current_object', function (finalObject) {
                    if (finalObject) {
                        // Final object received
                        lastProcessedObject = finalObject;
                        displayObject(finalObject);
                    }
                });

                // Clear the intervals to stop polling
                clearInterval(progressInterval);
                progressInterval = null;
                clearInterval(objectInterval);
                objectInterval = null;

                // Stop updating the processed list once processing is complete
                clearInterval(processedListInterval);
                processedListInterval = null;

                // Update processed list one final time
                updateProcessedList();

                // Update UI to show processing is complete
                $('#processing-toggle')
                    .removeClass('btn-danger')
                    .addClass('btn-success')
                    .prop('disabled', true)
                    .find('#processing-toggle-text')
                    .text('Processing Complete');

                // Add a pulsing effect to the button
                $('#processing-toggle').addClass('animate-pulse');

                // Keep the last item displayed - we've set processingComplete flag
                // Processing complete, last object preserved
            }
        });
    }

    function updateProcessedList() {
        // Update the processed files list
        $.get('/processed_status', function (data) {
            // Process the received data

            // Get the processed-list container
            const $container = $('#processed-list');

            // Ensure data is an array
            if (!Array.isArray(data)) {
                // Log error to backend if data is not an array
                logErrorToBackend('Invalid data format in updateProcessedList', 'script.js', 'Data is not an array');
                $container.html('<p class="text-red-600">Error: Invalid data format</p>');
                return;
            }

            // Filter out any items without a filename
            const validData = data.filter(item => item?.filename && typeof item.filename === 'string');

            // Process valid data items
            if (validData.length > 0) {
                // Create content with count
                let newContent = `
                    <p class="text-green-600 font-semibold mb-4">${validData.length} file(s) processed</p>
                    <div class="overflow-x-auto">
                        <table class="table">
                            <thead class="table-header">
                                <tr>
                                    <th class="table-header-cell w-12">#</th>
                                    <th class="table-header-cell">Filename</th>
                                    <th class="table-header-cell w-24">Status</th>
                                </tr>
                            </thead>
                            <tbody class="table-body">
                `;

                // Add a row for each file
                validData.forEach((item, index) => {
                    const filename = item.filename || 'Unknown file';

                    newContent += `
                        <tr class="table-row">
                            <td class="table-cell">${index + 1}</td>
                            <td class="table-cell">${filename}</td>
                            <td class="table-cell"><span class="badge badge-success">Processed</span></td>
                        </tr>
                    `;
                });

                // Close the table
                newContent += `
                            </tbody>
                        </table>
                    </div>
                `;

                // Update the container
                $container.html(newContent);
            } else {
                // Empty state
                $container.html('<p class="text-gray-500">No files processed yet.</p>');
            }
            // Processed items section replaced
        }).fail(function (error) {
            // Log error to backend
            logErrorToBackend('Error fetching processed files', 'script.js', JSON.stringify(error));
            $('#processed-list').html('<p class="text-red-600">Error loading processed files</p>');
        });
    }

    function updateObject() {
        // If processing is complete, don't update the object anymore
        if (processingComplete && lastProcessedObject) {
            // Processing complete, using last processed object
            // Display the last processed object even when processing is complete
            displayObject(lastProcessedObject);
            return;
        }

        $.get('/current_object', function (data) {
            // Process the received object

            if (data) {
                // Store the last processed object
                lastProcessedObject = data;
                displayObject(data);

                // If this object requires a decision, pause polling
                if (data.awaiting_user_decision) {
                    // Pause all polling intervals while waiting for user decision
                    if (progressInterval) {
                        clearInterval(progressInterval);
                        progressInterval = null;
                    }
                    if (objectInterval) {
                        clearInterval(objectInterval);
                        objectInterval = null;
                    }
                    if (processedListInterval) {
                        clearInterval(processedListInterval);
                        processedListInterval = null;
                    }

                    // Log that we're waiting for user input
                    console.log("Waiting for user decision - polling paused");
                }
            } else if (!processingComplete) {
                clearJsonDisplay();
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            // Log error to backend
            logErrorToBackend('Error fetching object: ' + errorThrown, 'script.js', textStatus);
        });
    }

    function displayObject(data) {
        // Ensure data is valid
        if (!data) {
            console.warn("displayObject called with invalid data");
            return;
        }

        // Update the current filename
        $('#current-filename').text(data.current_filename || 'No file selected');

        const showAutoAnalysis = data.show_auto_analysis === true || data.manual_analysis_required;

        if (showAutoAnalysis) {
            $('#automatic-analysis-block').removeClass('hidden');
        } else {
            $('#automatic-analysis-block').addClass('hidden');
        }

        // Update the title and show/hide manual analysis indicators
        if (data.manual_analysis_required) {
            $('#json-display-title').text('Function Analysis');

            // Show all manual analysis indicators
            $('#manual-analysis-indicator').removeClass('hidden').addClass('flex');
            $('#manual-analysis-banner').removeClass('hidden').addClass('block');
            $('#manual-analysis-message').removeClass('hidden').addClass('block');

            // Highlight the decision buttons to draw attention
            $('#decision-buttons').addClass('bg-red-50');

            // Add strong visual cues
            $('#not-vulnerable-btn, #vulnerable-btn, #submit-decision').addClass('animate-bounce');
            setTimeout(() => {
                $('#not-vulnerable-btn, #vulnerable-btn, #submit-decision').removeClass('animate-bounce');
            }, 2000);

            // Play notification sound if supported
            try {
                // Create audio element for notification
                const audio = new Audio();
                audio.src = 'data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAAFAAAGhgCFhYWFhYWFhYWFhYWFhYWFhYXj4+Pj4+Pj4+Pj4+Pj4+Pj4+P///////////////////8AAAA8TEFNRTMuOTlyAc0AAAAAAAAAABSAJAJAQgAAgAAAA+aGWrQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//sQxAADwAABpAAAACAAADSAAAAETEFNRTMuOTkuNVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVU=';
                audio.volume = 0.5;
                audio.play();
            } catch (e) {
                console.log('Audio notification not supported');
            }
        } else {
            $('#json-display-title').text('Function Analysis');

            // Hide all manual analysis indicators
            $('#manual-analysis-indicator').addClass('hidden').removeClass('flex');
            $('#manual-analysis-banner').addClass('hidden').removeClass('block');
            $('#manual-analysis-message').addClass('hidden').removeClass('block');

            // Remove highlighting
            $('#decision-buttons').removeClass('bg-red-50');
        }

        // Always show decision buttons and make sure they're visible
        $('#decision-buttons').show();

        // Directly update ID fields (these are spans, not complex elements)
        $('#id').text(data.id !== undefined ? data.id : '-');
        $('#sub_id').text(data.sub_id !== undefined ? data.sub_id : '-');
        $('#code_id').text(data.code_id !== undefined ? data.code_id : '-');
        $('#function_id').text(data.function_id !== undefined ? data.function_id : '-');

        // Update function information fields
        updateField('class_name', data.class_name);
        updateField('subclass_name', data.subclass_name);
        updateField('function_name', data.function_name);
        updateField('function_body', data.function_body);

        // Update response field
        updateField('response', data.response);

        // Update function analysis field
        if (!data.function_analysis) {
            updateField('function_analysis', 'No function analysis available for this object.');
        } else {
            updateField('function_analysis', data.function_analysis);
        }

        // Update hidden metadata fields for JS functionality
        try {
            $('#is_vulnerable').text(data.is_vulnerable !== undefined ? data.is_vulnerable : '-');
            $('#relevance_label').text(data.relevance_label !== undefined ? data.relevance_label : '-');
            $('#function_label').text(data.function_label !== undefined ? data.function_label : '-');
            $('#filename').text(data.filename !== undefined ? data.filename : '-');
            $('#human_patch').text(data.human_patch !== undefined ? data.human_patch : '-');
            $('#cve_id').text(data.cve_id !== undefined ? data.cve_id : '-');
            $('#cwe_id').text(data.cwe_id !== undefined ? data.cwe_id : '-');
            $('#prompt_eval_count').text(data.prompt_eval_count !== undefined ? data.prompt_eval_count : '-');
            $('#prompt_eval_duration').text(data.prompt_eval_duration !== undefined ? data.prompt_eval_duration : '-');
            $('#eval_count').text(data.eval_count !== undefined ? data.eval_count : '-');
            $('#eval_duration').text(data.eval_duration !== undefined ? data.eval_duration : '-');
            $('#total_duration').text(data.total_duration !== undefined ? data.total_duration : '-');
            $('#load_duration').text(data.load_duration !== undefined ? data.load_duration : '-');
        } catch (e) {
            console.error("Error updating hidden metadata fields:", e);
        }

        // Update additional metadata fields
        try {
            $('#meta-human-patch').text(data.human_patch !== undefined ? data.human_patch : '-');
            $('#meta-cve-id').text(data.cve_id !== undefined ? data.cve_id : '-');
            $('#meta-cwe-id').text(data.cwe_id !== undefined ? data.cwe_id : '-');
            $('#meta-relevance-label').text(data.relevance_label !== undefined ? data.relevance_label : '-');
            $('#meta-eval-count').text(data.eval_count !== undefined ? data.eval_count : '-');
            $('#meta-total-duration').text(data.total_duration !== undefined ? data.total_duration : '-');
            $('#meta-prompt-eval-count').text(data.prompt_eval_count !== undefined ? data.prompt_eval_count : '-');
            $('#meta-prompt-eval-duration').text(data.prompt_eval_duration !== undefined ? data.prompt_eval_duration : '-');
            $('#meta-eval-duration').text(data.eval_duration !== undefined ? data.eval_duration : '-');
            $('#meta-load-duration').text(data.load_duration !== undefined ? data.load_duration : '-');
        } catch (e) {
            console.error("Error updating additional metadata fields:", e);
        }

        // Update detailed metadata section
        try {
            $('#meta-id').text(data.id !== undefined ? data.id : '-');
            $('#meta-sub-id').text(data.sub_id !== undefined ? data.sub_id : '-');
            $('#meta-code-id').text(data.code_id !== undefined ? data.code_id : '-');
            $('#meta-function-id').text(data.function_id !== undefined ? data.function_id : '-');
            $('#meta-human-patch').text(data.human_patch !== undefined ? data.human_patch : '-');
            $('#meta-cve-id').text(data.cve_id !== undefined ? data.cve_id : '-');
            $('#meta-cwe-id').text(data.cwe_id !== undefined ? data.cwe_id : '-');
            $('#meta-filename').text(data.filename !== undefined ? data.filename : '-');
            $('#meta-relevance-label').text(data.relevance_label !== undefined ? data.relevance_label : '-');
            $('#meta-prompt-eval-count').text(data.prompt_eval_count !== undefined ? data.prompt_eval_count : '-');
            $('#meta-prompt-eval-duration').text(data.prompt_eval_duration !== undefined ? data.prompt_eval_duration : '-');
            $('#meta-eval-count').text(data.eval_count !== undefined ? data.eval_count : '-');
            $('#meta-eval-duration').text(data.eval_duration !== undefined ? data.eval_duration : '-');
            $('#meta-total-duration').text(data.total_duration !== undefined ? data.total_duration : '-');
            $('#meta-load-duration').text(data.load_duration !== undefined ? data.load_duration : '-');
        } catch (e) {
            console.error("Error updating detailed metadata section:", e);
        }
    }

    // Helper function to update a field with animation
    function updateField(key, value) {
        // Handle null/undefined values
        if (value === null || value === undefined) {
            value = '-';
        }

        // First try to find the element as a span (for ID fields)
        let element = $(`#${key}`);

        // If it's not a span, try to find it as a div (for other fields)
        if (!element.length) {
            element = $(`#${key}`).find('div:last-child');
        }

        if (element.length) {
            // Special formatting for certain fields
            if (key === 'relevance_label') {
                if (value === 1) {
                    element.html('<span class="text-red-600 font-bold">VULNERABLE</span>');
                    return;
                } else if (value === 0) {
                    element.html('<span class="text-green-600 font-bold">NOT VULNERABLE</span>');
                    return;
                } else if (value === -1) {
                    element.html('<span class="text-yellow-600 font-bold">NOT RELEVANT</span>');
                    return;
                }
            }

            if (key === 'function_label') {
                if (value === 1) {
                    element.html('<span class="text-red-600 font-bold">VULNERABLE</span>');
                    return;
                } else if (value === 0) {
                    element.html('<span class="text-green-600 font-bold">NOT VULNERABLE</span>');
                    return;
                }
            }

            // Special handling for code blocks
            if (key === 'function_body') {
                const codeElement = element.find('code');
                if (codeElement.length) {
                    codeElement.text(String(value));
                    hljs.highlightElement(codeElement[0]);
                } else {
                    element.text(String(value));
                }
                return;
            }

            if (key === 'response') {
                const codeElement = element.find('code');
                if (codeElement.length) {
                    codeElement.text(String(value));
                    hljs.highlightElement(codeElement[0]);
                } else {
                    element.text(String(value));
                }
                return;
            }

            if (key === 'function_analysis') {
                const codeElement = element.find('code');
                if (codeElement.length) {
                    codeElement.text(String(value));
                    hljs.highlightElement(codeElement[0]);
                } else {
                    element.text(String(value));
                }
                return;
            }

            // For simple span elements (like ID fields), just update the text
            if (element.is('span')) {
                if (element.text() !== String(value)) {
                    element.fadeOut(200, function () {
                        element.text(String(value)).fadeIn(200);
                    });
                }
                return;
            }

            // Update with animation if the content has changed
            if (element.html() !== String(value)) {
                element.fadeOut(200, function () {
                    element.html(String(value)).fadeIn(200);
                });
            }
        } else {
            // Element not found, log to backend
            logErrorToBackend(`Element not found for key: ${key}`, 'script.js');
        }
    }

    function clearJsonDisplay() {
        try {
            $('#json-display-title').text('Function Analysis');

            // Hide all manual analysis indicators
            $('#manual-analysis-indicator').addClass('hidden').removeClass('flex');
            $('#manual-analysis-banner').addClass('hidden').removeClass('block');
            $('#manual-analysis-message').addClass('hidden').removeClass('block');

            // Remove any highlighting
            $('#decision-buttons').removeClass('bg-red-50');

            // Reset identification fields
            $('#current-filename').text('No file selected');
            $('#id').text('-');
            $('#sub_id').text('-');
            $('#code_id').text('-');
            $('#function_id').text('-');

            // Reset additional metadata fields
            $('#meta-human-patch').text('-');
            $('#meta-cve-id').text('-');
            $('#meta-cwe-id').text('-');
            $('#meta-relevance-label').text('-');
            $('#meta-eval-count').text('-');
            $('#meta-total-duration').text('-');
            $('#meta-prompt-eval-count').text('-');
            $('#meta-prompt-eval-duration').text('-');
            $('#meta-eval-duration').text('-');
            $('#meta-load-duration').text('-');

            // Reset function information fields - safely check if elements exist
            const classNameElement = $('#class_name div:last-child');
            if (classNameElement.length) classNameElement.text('-');

            const subclassNameElement = $('#subclass_name div:last-child');
            if (subclassNameElement.length) subclassNameElement.text('-');

            const functionNameElement = $('#function_name div:last-child');
            if (functionNameElement.length) functionNameElement.text('-');

            const functionBodyElement = $('#function_body div:last-child').find('code');
            if (functionBodyElement.length) functionBodyElement.text('-');

            // Reset response field - safely check if element exists
            const responseElement = $('#response div:last-child').find('code');
            if (responseElement.length) responseElement.text('-');

            // Reset function analysis field - safely check if element exists
            const functionAnalysisElement = $('#function_analysis div:last-child').find('code');
            if (functionAnalysisElement.length) functionAnalysisElement.text('No function analysis available.');

            // Reset detailed metadata fields
            $('#meta-id').text('-');
            $('#meta-sub-id').text('-');
            $('#meta-code-id').text('-');
            $('#meta-function-id').text('-');
            $('#meta-human-patch').text('-');
            $('#meta-cve-id').text('-');
            $('#meta-cwe-id').text('-');
            $('#meta-filename').text('-');
            $('#meta-relevance-label').text('-');
            $('#meta-prompt-eval-count').text('-');
            $('#meta-prompt-eval-duration').text('-');
            $('#meta-eval-count').text('-');
            $('#meta-eval-duration').text('-');
            $('#meta-total-duration').text('-');
            $('#meta-load-duration').text('-');

            // Reset decision state
            decision = null;
            $('.btn-decision').removeClass('active');
            $('.btn-decision').removeClass('ring-2');
            $('.btn-decision').removeClass('ring-offset-2');
            $('.btn-decision').removeClass('animate-pulse');

            // Reset button text
            $('#not-vulnerable-btn').find('span').html('<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>Not Vulnerable (Q)');
            $('#vulnerable-btn').find('span').html('<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>Vulnerable (W)');

            // Always show decision buttons
            $('#decision-buttons').show();
        } catch (e) {
            console.error("Error in clearJsonDisplay:", e);
            // Log to backend
            logErrorToBackend("Error in clearJsonDisplay: " + e.message, 'script.js', e.stack);
        }
    }

    $('#not-vulnerable-btn').click(function () {
        decision = 0;
        // Clear active state from all buttons
        $('.btn-decision').removeClass('active');
        $('.btn-decision').removeClass('ring-2');
        $('.btn-decision').removeClass('ring-offset-2');

        // Add active state to this button
        $(this).addClass('active');
        $(this).addClass('ring-2');
        $(this).addClass('ring-offset-2');

        // Visual feedback - pulse effect
        $(this).addClass('animate-pulse');
        setTimeout(() => {
            $(this).removeClass('animate-pulse');
        }, 500);

        // Update button text to show selection
        $(this).find('span').html('<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>Not Vulnerable (Selected)');
        $('#vulnerable-btn').find('span').html('<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>Vulnerable (W)');
    });

    $('#vulnerable-btn').click(function () {
        decision = 1;
        // Clear active state from all buttons
        $('.btn-decision').removeClass('active');
        $('.btn-decision').removeClass('ring-2');
        $('.btn-decision').removeClass('ring-offset-2');

        // Add active state to this button
        $(this).addClass('active');
        $(this).addClass('ring-2');
        $(this).addClass('ring-offset-2');

        // Visual feedback - pulse effect
        $(this).addClass('animate-pulse');
        setTimeout(() => {
            $(this).removeClass('animate-pulse');
        }, 500);

        // Update button text to show selection
        $(this).find('span').html('<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>Vulnerable (Selected)');
        $('#not-vulnerable-btn').find('span').html('<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>Not Vulnerable (Q)');
    });

    $('#submit-decision').click(function () {
        if (decision === null) {
            alert("Please select whether the function is vulnerable or not.");
            return;
        }

        $(this).prop('disabled', true).text('Submitting...');

        // Submit the function decision
        $.ajax({
            url: '/submit_decision',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ decision: decision }),
            success: function (data) {
                // Decision submitted successfully
                clearJsonDisplay();

                // Resume polling now that the decision has been submitted
                if (processing && !processingComplete) {
                    console.log("Decision submitted - resuming polling");

                    // Restart the intervals for automatic updates
                    if (!progressInterval) {
                        progressInterval = setInterval(updateProgress, 1000);
                    }
                    if (!objectInterval) {
                        objectInterval = setInterval(updateObject, 1000);
                    }
                    if (!processedListInterval) {
                        processedListInterval = setInterval(updateProcessedList, 5000);
                    }

                    // Immediately update to get the next object
                    updateProgress();
                    updateObject();
                    updateProcessedList();
                }
            },
            error: function (xhr, status, error) {
                // Log error to backend
                logErrorToBackend("Error submitting decision: " + error, 'script.js', xhr.responseText);
                alert("Error submitting decision. Please try again.");
            },
            complete: function () {
                $('#submit-decision').prop('disabled', false).text('Submit Decision (S)');
            }
        });
    });

    // Set up metadata toggle
    $('#metadata-toggle').click(function () {
        $('#metadata-content').slideToggle(200);
        $('#metadata-chevron').toggleClass('rotate-180');
    });

    // Remove any references to detailed-metadata-toggle
    $('#detailed-metadata-toggle').remove();
    $('#detailed-metadata-content').remove();

    // Keyboard shortcuts
    $(document).keydown(function (e) {
        if (!$('#decision-buttons').hasClass('hidden')) {
            switch (e.key.toLowerCase()) {
                case 'q':
                    $('#not-vulnerable-btn').click();
                    break;
                case 'w':
                    $('#vulnerable-btn').click();
                    break;
                case 's':
                    $('#submit-decision').click();
                    break;
                case 'm':
                    $('#metadata-toggle').click();
                    break;
            }
        }
    });

    // Variables to track the last processed object and intervals
    let lastProcessedObject = null;

    // Initialize interval variables
    let progressInterval = null;
    let objectInterval = null;
    let processedListInterval = null;

    // Only update progress when processing is active
    // We'll start these intervals when the user clicks "Start Processing"
});
