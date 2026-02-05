$(document).ready(function () {
    let processing = false;
    let decision = null;
    let processingStatusInterval = null;
    let lastReviewStage = null;
    let lastReviewReason = null;

    // Initialize scroll tracking
    window.initialScrollDone = false;

    // Check for dark mode preference
    initDarkMode();

    // Initialize empty fields with placeholder
    $('.json-field-value').text('-');

    // Check input directory status on page load
    checkInputDirectory();

    // Check processing status on page load
    checkProcessingStatus();

    // Dark mode toggle
    $('#dark-mode-toggle').click(function () {
        $('html').toggleClass('dark');
        localStorage.setItem('darkMode', $('html').hasClass('dark') ? 'enabled' : 'disabled');
    });

    $('#start-processing').click(function () {
        if (!processing) {
            // First check if input directory exists and has files
            $.get('/check_input_directory', function (data) {
                if (data.exists) {
                    if (data.file_count > 0) {
                        // Directory exists and has files, proceed with processing
                        $.get('/start_processing', function (data) {
                            console.log(data.status);
                            processing = true;
                            updateProcessingUI(true);
                            updateObject();

                            // Show decision buttons immediately if there's an object requiring manual review
                            checkForManualReviewObjects();

                            // Start checking processing status more frequently
                            if (processingStatusInterval) {
                                clearInterval(processingStatusInterval);
                            }
                            processingStatusInterval = setInterval(checkProcessingStatus, 1000);
                        });
                    } else {
                        // Directory exists but has no files
                        showAlert("Input directory exists but contains no JSON files to process.", "warning");
                    }
                } else {
                    // Directory doesn't exist
                    showAlert("Input directory does not exist. Please check configuration.", "error");
                }
            });
        }
    });

    $('#stop-processing').click(function () {
        if (processing) {
            // Disable the button while request is in progress
            $('#stop-processing').prop('disabled', true).addClass('opacity-50');

            // Show stopping state immediately for better user feedback
            $('#status-indicator').removeClass('bg-gray-400 bg-green-500').addClass('bg-yellow-500');
            $('#status-text').removeClass('text-gray-500 text-green-500').addClass('text-yellow-500');
            $('#status-text').text('Stopping...');

            $.get('/stop_processing', function (data) {
                console.log(data.status);
                showAlert("Processing stop requested. Please wait for current operation to complete.", "info");

                // Don't update UI yet - wait for status check to confirm processing has stopped
                // The checkProcessingStatus function will update the UI when processing actually stops

                // Re-enable the button
                $('#stop-processing').prop('disabled', false).removeClass('opacity-50');
            }).fail(function () {
                // Re-enable the button on failure
                $('#stop-processing').prop('disabled', false).removeClass('opacity-50');
                showAlert("Failed to stop processing. Please try again.", "error");

                // Reset status indicator to processing state
                $('#status-indicator').removeClass('bg-gray-400 bg-yellow-500').addClass('bg-green-500');
                $('#status-text').removeClass('text-gray-500 text-yellow-500').addClass('text-green-500');
                $('#status-text').text('Processing');
            });
        }
    });

    function checkProcessingStatus() {
        $.get('/processing_status', function (data) {
            console.log('Processing status:', data);

            // Update the processing state based on server response
            processing = data.is_processing;

            // Update UI based on processing state
            updateProcessingUI(processing);

            // If processing has stopped, clear the interval
            if (!processing && processingStatusInterval) {
                clearInterval(processingStatusInterval);
                processingStatusInterval = null;
                showAlert("Processing has stopped.", "info");
            }
        });
    }

    function updateProcessingUI(isProcessing) {
        if (isProcessing) {
            // Update buttons
            $('#start-processing').addClass('hidden');
            $('#stop-processing').removeClass('hidden');

            // Update status indicator
            $('#status-indicator').removeClass('bg-gray-400 bg-red-500').addClass('bg-green-500');
            $('#status-text').removeClass('text-gray-500 text-red-500').addClass('text-green-500');
            $('#status-text').text('Processing');
        } else {
            // Update buttons
            $('#stop-processing').addClass('hidden');
            $('#start-processing').removeClass('hidden');

            // Update status indicator
            $('#status-indicator').removeClass('bg-green-500 bg-red-500').addClass('bg-gray-400');
            $('#status-text').removeClass('text-green-500 text-red-500').addClass('text-gray-500');
            $('#status-text').text('Idle');
        }
    }

    // Store the last progress data to prevent unnecessary UI updates
    let lastProgressData = null;

    function updateProgress() {
        $.get('/progress', function (data) {
            // Check if we need to update the progress UI
            const needsProgressUpdate = !lastProgressData ||
                Math.abs(data.file_progress - lastProgressData.file_progress) >= 0.5 ||
                Math.abs(data.total_progress - lastProgressData.total_progress) >= 0.5;

            // Update processing state if it's included in the response
            if (data.hasOwnProperty('is_processing')) {
                // Only update the UI if the state has changed
                if (processing !== data.is_processing) {
                    processing = data.is_processing;
                    updateProcessingUI(processing);

                    // If processing has stopped, show a notification
                    if (!processing && processingStatusInterval) {
                        clearInterval(processingStatusInterval);
                        processingStatusInterval = null;
                        showAlert("Processing has completed or been stopped.", "info");
                    }
                }
            }

            // Only update the progress UI if there's a significant change
            if (needsProgressUpdate) {
                const fileProgress = data.file_progress.toFixed(2);
                const totalProgress = data.total_progress.toFixed(2);

                // Update the text displays
                $('#file-progress-text').text(fileProgress + '%');
                $('#total-progress-text').text(totalProgress + '%');

                // Update the progress bar widths
                $('#file-progress-bar').css('width', fileProgress + '%');
                $('#total-progress-bar').css('width', totalProgress + '%');

                // Update progress bar colors based on progress
                updateProgressBarColors(data.file_progress, data.total_progress);

                // Save the current progress data
                lastProgressData = data;
            }
        });
    }

    function updateProgressBarColors(fileProgress, totalProgress) {
        // Add color classes based on progress percentage
        if (fileProgress < 25) {
            $('#file-progress-bar').removeClass('bg-yellow-500 bg-green-500').addClass('bg-primary-500');
        } else if (fileProgress < 75) {
            $('#file-progress-bar').removeClass('bg-primary-500 bg-green-500').addClass('bg-yellow-500');
        } else {
            $('#file-progress-bar').removeClass('bg-primary-500 bg-yellow-500').addClass('bg-green-500');
        }

        if (totalProgress < 25) {
            $('#total-progress-bar').removeClass('bg-yellow-500 bg-green-500').addClass('bg-primary-500');
        } else if (totalProgress < 75) {
            $('#total-progress-bar').removeClass('bg-primary-500 bg-green-500').addClass('bg-yellow-500');
        } else {
            $('#total-progress-bar').removeClass('bg-primary-500 bg-yellow-500').addClass('bg-green-500');
        }
    }

    function highlightResponse() {
        $('#response').addClass('animate-pulse');
        setTimeout(() => {
            $('#response').removeClass('animate-pulse');
        }, 1000);
    }

    function setRelevanceAnalysisVisibility(show) {
        const panel = $('#relevance_analysis');
        const responsePanel = $('#response-panel');

        if (show) {
            panel.removeClass('hidden');
            responsePanel.removeClass('lg:col-span-3').addClass('lg:col-span-2');
        } else {
            panel.addClass('hidden');
            responsePanel.removeClass('lg:col-span-2').addClass('lg:col-span-3');
        }
    }

    function setReviewStageBadge(stage) {
        const badge = $('#review-stage-badge');
        const decisionLabel = $('#decision-stage-label');
        if (!badge.length) return;

        badge.removeClass('bg-primary-100 text-primary-700 dark:bg-primary-800 dark:text-primary-200 bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-100');

        if (stage === 2) {
            badge.text('Step 2 of 2');
            badge.addClass('bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-100');
            decisionLabel.text('Step 2 of 2');
        } else if (stage === 1) {
            badge.text('Step 1 of 2');
            badge.addClass('bg-primary-100 text-primary-700 dark:bg-primary-800 dark:text-primary-200');
            decisionLabel.text('Step 1 of 2');
        } else {
            badge.text('Waiting');
            badge.addClass('bg-primary-100 text-primary-700 dark:bg-primary-800 dark:text-primary-200');
            decisionLabel.text('');
        }
    }

    function updateReviewInstructions(stage) {
        const title = $('#review-instructions-title');
        const body = $('#review-instructions-body');

        if (stage === 2) {
            title.text('Second Review Required');
            body.text('Review the LLM response and the relevance analysis, then confirm your final decision.');
        } else if (stage === 1) {
            title.text('Vulnerability Assessment Instructions');
            body.html('Review the LLM response below and make your decision based only on the <span class="font-bold">Response</span> content.');
        } else {
            title.text('Vulnerability Assessment Instructions');
            body.text('Waiting for the next item to review.');
        }
    }

    function getSecondReviewMessage(reason) {
        if (reason === 'mismatch') {
            return 'Your first decision did not match the relevance analysis result. Review both sources and decide again.';
        }
        if (reason === 'unparsed') {
            return 'The relevance analysis could not be parsed automatically. Review it and confirm your final decision.';
        }
        return 'Second review required. Review the relevance analysis and confirm your final decision.';
    }

    function updateSecondReviewBanner(show, reason) {
        const banner = $('#second-review-banner');
        if (!banner.length) return;

        if (show) {
            $('#second-review-message').text(getSecondReviewMessage(reason));
            banner.removeClass('hidden');
        } else {
            banner.addClass('hidden');
        }
    }

    function updateObject(objectData) {
        // If objectData is not provided, fetch it from the server
        if (!objectData) {
            $.get('/current_object', function (data) {
                updateObject(data);
            }).fail(function (jqXHR, textStatus, errorThrown) {
                console.error('Error fetching object:', textStatus, errorThrown);
            });
            return;
        }

        const data = objectData;

        if (data) {
            console.log('Processing object data:', data);  // Debug log

            // Update filename in both places
            const filename = data.current_filename || 'No file selected';
            $('#current-filename').text(filename);
            $('#current-filename-display').text(filename);

            // Check if this object needs manual review
            const needsManualReview = data.needs_manual_review === true || data.relevance_label === null;

            const parsedReviewStage = parseInt(data.review_stage, 10);
            const reviewStage = needsManualReview ? (parsedReviewStage === 2 ? 2 : 1) : 0;
            const reviewReason = data.review_reason || null;
            const objectChanged = !lastObjectData ||
                data.id !== lastObjectData.id ||
                data.sub_id !== lastObjectData.sub_id ||
                data.code_id !== lastObjectData.code_id;
            const stageChanged = reviewStage !== lastReviewStage || objectChanged;
            const reasonChanged = reviewReason !== lastReviewReason || objectChanged;

            if (needsManualReview) {
                $('#decision-buttons').removeClass('hidden');
                setReviewStageBadge(reviewStage);
                updateReviewInstructions(reviewStage);

                if (reviewStage === 2) {
                    $('#json-display-title').text('Second Review Required');
                    setRelevanceAnalysisVisibility(true);
                    updateSecondReviewBanner(true, reviewReason);

                    if (stageChanged || reasonChanged) {
                        showAlert(getSecondReviewMessage(reviewReason), "warning", 7000);
                        highlightResponse();
                    }
                } else {
                    $('#json-display-title').text('Review Required');
                    setRelevanceAnalysisVisibility(false);
                    updateSecondReviewBanner(false);

                    if (stageChanged) {
                        showAlert("Review the LLM response and make your decision based only on the response.", "info", 5000);
                        highlightResponse();
                    }
                }

                if (stageChanged) {
                    $('.btn-decision').removeClass('ring-2');
                    decision = null;
                }
            } else {
                $('#json-display-title').text('Decision Recorded');
                $('#decision-buttons').addClass('hidden');
                setRelevanceAnalysisVisibility(false);
                updateSecondReviewBanner(false);
                setReviewStageBadge(0);
                updateReviewInstructions(0);
            }

            lastReviewStage = reviewStage;
            lastReviewReason = reviewReason;

            // Update all ID fields in the header and in the metadata section
            if (data.id !== undefined) {
                const idValue = data.id;
                $('#id-value').text(idValue);
                $('#header-id').text(idValue);
            }

            if (data.sub_id !== undefined) {
                const subIdValue = data.sub_id;
                $('#header-sub-id').text(subIdValue);
                $('#sub-id-value').text(subIdValue);
            }

            if (data.code_id !== undefined) {
                const codeIdValue = data.code_id;
                $('#code-id-value').text(codeIdValue);
                $('#header-code-id').text(codeIdValue);
            }

            // Update all fields without animation for a more stable UI
            updateFieldContent(data);

            // Only scroll to the response section on the first load and if manual review is needed
            if (!window.initialScrollDone && needsManualReview) {
                $('html, body').animate({
                    scrollTop: $('#response').offset().top - 100
                }, 500);
                window.initialScrollDone = true;
            }
        } else {
            clearJsonDisplay();
        }
    }

    // Helper function to format markdown text
    function formatMarkdown(text) {
        // This is a simple formatter that preserves some markdown formatting
        // For a more complete solution, consider using a markdown library

        // Preserve code blocks
        text = text.replace(/```([^`]+)```/g, '<pre class="bg-gray-100 dark:bg-gray-900 p-2 rounded my-2 overflow-x-auto">$1</pre>');

        // Preserve headers
        text = text.replace(/^### (.*$)/gm, '<h3 class="text-lg font-semibold mt-3 mb-1">$1</h3>');
        text = text.replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>');
        text = text.replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>');

        // Preserve lists
        text = text.replace(/^\* (.*$)/gm, '<li class="ml-4">• $1</li>');
        text = text.replace(/^- (.*$)/gm, '<li class="ml-4">• $1</li>');

        // Preserve bold and italic
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

        return text;
    }

    function clearJsonDisplay() {
        $('#json-display-title').text('Waiting for Analysis');
        $('#decision-buttons').addClass('hidden');
        setRelevanceAnalysisVisibility(false);
        updateSecondReviewBanner(false);
        setReviewStageBadge(0);
        updateReviewInstructions(0);

        // Reset all fields with animation
        $('.json-field-value').fadeOut(200, function () {
            $(this).text('-').fadeIn(200);
        });

        // Reset all ID fields in both header and metadata section
        $('#id-value').text('-');
        $('#sub-id-value').text('-');  // Reset the Sub ID in the metadata summary
        $('#code-id-value').text('-');
        $('#header-id').text('-');
        $('#header-sub-id').text('-');
        $('#header-code-id').text('-');

        // Reset filenames
        $('#current-filename').text('No file selected');
        $('#current-filename-display').text('No file selected');

        // Reset decision state
        decision = null;
        $('.btn-decision').removeClass('ring-2');
        lastReviewStage = null;
        lastReviewReason = null;

        // Reset scroll flag to allow scrolling to the next item
        window.initialScrollDone = false;
    }

    function checkInputDirectory() {
        $.get('/check_input_directory', function (data) {
            let statusMessage;
            let alertType;

            if (data.exists) {
                if (data.file_count > 0) {
                    statusMessage = `Input directory ready with ${data.file_count} files. ${data.processed_count} files already processed.`;
                    alertType = "success";
                } else {
                    statusMessage = "Input directory exists but contains no JSON files to process.";
                    alertType = "warning";
                }
            } else {
                statusMessage = "Input directory does not exist. Please check configuration.";
                alertType = "error";
            }

            showAlert(statusMessage, alertType, 5000);
        });
    }

    // Function to check if an object requires manual review
    function requiresManualReview(obj) {
        return obj && (obj.needs_manual_review === true || obj.relevance_label === null);
    }

    // Function to safely format JSON if possible
    function formatJsonIfPossible(text) {
        if (!text) return text;

        try {
            // Try to parse and pretty-print JSON
            const jsonObj = JSON.parse(text);
            return JSON.stringify(jsonObj, null, 2);
        } catch (error) {
            // Log the error but don't throw it
            console.log('Failed to parse JSON:', error.message);
            // Return the original text
            return text;
        }
    }

    // Function to update all field content
    function updateFieldContent(data) {
        // Fields that need special formatting
        const specialFields = {
            'relevance_analysis': formatJsonIfPossible,
            'response': formatMarkdown
        };

        // Update each field in the data object
        Object.keys(data).forEach(key => {
            const element = $(`#${key} .json-field-value`);
            if (!element.length) return;

            let newValue = data[key];

            // Handle null/undefined values
            if (newValue === null || newValue === undefined) {
                newValue = '-';
            }

            // Apply special formatting if needed
            if (specialFields[key] && typeof newValue === 'string') {
                newValue = specialFields[key](newValue);
            }

            // Only update if the content has changed
            if (element.text() !== String(newValue)) {
                // Use html() for content with HTML tags, text() otherwise
                if (typeof newValue === 'string' && newValue.includes('<')) {
                    element.html(newValue);
                } else {
                    element.text(String(newValue));
                }

                // Add syntax highlighting for JSON content
                if (key === 'relevance_analysis' || key === 'response') {
                    element.addClass('json-content');
                }
            }
        });
    }

    function checkForManualReviewObjects() {
        $.get('/current_object', function (data) {
            if (requiresManualReview(data)) {
                $('#decision-buttons').removeClass('hidden');
            }
        });
    }

    function initDarkMode() {
        // Check if user has a preference stored
        const darkModePreference = localStorage.getItem('darkMode');

        // Check if user prefers dark mode at the OS level
        const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

        // Apply dark mode if user has enabled it or if they prefer it at OS level and haven't explicitly disabled it
        if (darkModePreference === 'enabled' || (prefersDarkMode && darkModePreference !== 'disabled')) {
            $('html').addClass('dark');
        } else {
            $('html').removeClass('dark');
        }
    }

    $('#not-vulnerable-btn').click(function () {
        decision = false;
        $('.btn-decision').removeClass('ring-2');
        $(this).addClass('ring-2');
    });

    $('#vulnerable-btn').click(function () {
        decision = true;
        $('.btn-decision').removeClass('ring-2');
        $(this).addClass('ring-2');
    });

    $('#not-relevant-btn').click(function () {
        decision = -1;
        $('.btn-decision').removeClass('ring-2');
        $(this).addClass('ring-2');
    });

    $('#submit-decision').click(function () {
        if (decision === null) {
            // Show a more modern alert using Tailwind
            showAlert("Please select a decision first.");
            return;
        }

        $(this).prop('disabled', true).text('Submitting...');

        // Convert decision to the correct type
        let decisionValue;
        if (decision === true) {
            decisionValue = 1;  // Vulnerable
        } else if (decision === false) {
            decisionValue = 0;  // Not vulnerable
        } else {
            decisionValue = decision;  // Already -1 for Not relevant
        }

        console.log('Submitting decision:', decisionValue);  // Debug log

        $.ajax({
            url: '/submit_decision',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ decision: decisionValue }),
            success: function (data) {
                console.log("Decision submitted successfully:", data.status);
                decision = null;
                $('.btn-decision').removeClass('ring-2');
                showAlert("Decision submitted. If a second review is required, it will appear shortly.", "info", 5000);
            },
            error: function (xhr, status, error) {
                console.error("Error submitting decision:", error);
                console.error("Response:", xhr.responseText);  // Add response text to debug
                showAlert("Error submitting decision. Please try again.", "error");
            },
            complete: function () {
                $('#submit-decision').prop('disabled', false).text('Submit Decision (S)');
            }
        });
    });

    function showAlert(message, type = "warning", duration = 3000) {
        // Remove any existing alerts
        $('.alert-message').remove();

        // Create alert element
        const alertClasses = {
            success: "bg-green-100 border-green-500 text-green-700 dark:bg-green-800 dark:border-green-600 dark:text-green-100",
            warning: "bg-yellow-100 border-yellow-500 text-yellow-700 dark:bg-yellow-800 dark:border-yellow-600 dark:text-yellow-100",
            error: "bg-red-100 border-red-500 text-red-700 dark:bg-red-800 dark:border-red-600 dark:text-red-100",
            info: "bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-800 dark:border-blue-600 dark:text-blue-100"
        };

        // Choose the appropriate icon based on alert type
        let icon = '';
        switch (type) {
            case 'success':
                icon = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />';
                break;
            case 'error':
                icon = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />';
                break;
            case 'warning':
                icon = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />';
                break;
            case 'info':
            default:
                icon = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />';
                break;
        }

        const alert = $(`
            <div class="alert-message fixed top-4 right-4 p-4 rounded-lg border-l-4 shadow-md ${alertClasses[type]} z-50">
                <div class="flex items-center">
                    <div class="py-1">
                        <svg class="h-6 w-6 mr-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            ${icon}
                        </svg>
                    </div>
                    <div>
                        <p class="font-medium">${message}</p>
                    </div>
                </div>
            </div>
        `);

        $('body').append(alert);

        // Auto-remove after specified duration
        setTimeout(function () {
            alert.fadeOut(300, function () {
                $(this).remove();
            });
        }, duration);
    }

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
                case 'e':
                    $('#not-relevant-btn').click();
                    break;
                case 's':
                    $('#submit-decision').click();
                    break;
            }
        }
    });

    // Store the last object data to prevent unnecessary UI updates
    let lastObjectData = null;

    // Function to check if we need to update the UI based on new data
    function needsUIUpdate(newData) {
        // Basic existence checks
        if (!lastObjectData || !newData) return true;

        // Check if any of the key identifiers have changed
        return newData.id !== lastObjectData.id ||
            newData.sub_id !== lastObjectData.sub_id ||
            newData.code_id !== lastObjectData.code_id ||
            requiresManualReview(newData) !== requiresManualReview(lastObjectData) ||
            newData.review_stage !== lastObjectData.review_stage ||
            newData.review_reason !== lastObjectData.review_reason;
    }

    // Modified updateObject function to prevent unnecessary UI updates
    function updateObjectWithStability() {
        $.get('/current_object', function (data) {
            // Only update the UI if the data has changed in a meaningful way
            if (needsUIUpdate(data)) {
                console.log('Updating UI with new object data');
                updateObject(data);
                lastObjectData = data;
            }
        });
    }

    // Start polling with appropriate intervals
    // Use longer intervals for progress updates to reduce server load
    setInterval(updateProgress, 1000);

    // Use a more reasonable interval for object updates
    setInterval(updateObjectWithStability, 1000);

    // Initial check for processing status
    checkProcessingStatus();
});
