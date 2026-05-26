document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const submitBtn = document.getElementById('submit-btn');
    const spinner = document.getElementById('spinner');
    const analysisForm = document.getElementById('analysis-form');
    const consoleOutput = document.getElementById('console-output');
    const clearLogsBtn = document.getElementById('clear-logs');
    
    // Result elements
    const resultsPlaceholder = document.getElementById('results-placeholder');
    const resultsDisplay = document.getElementById('results-display');
    const resultMeta = document.getElementById('result-meta');
    const resultRenderImg = document.getElementById('result-render-img');
    const resultOriginalImg = document.getElementById('result-original-img');
    
    // Stat elements
    const statRisk3 = document.getElementById('stat-risk-3');
    const statRisk2 = document.getElementById('stat-risk-2');
    const statRisk1 = document.getElementById('stat-risk-1');
    const statRisk0 = document.getElementById('stat-risk-0');
    
    const detailTotalCells = document.getElementById('detail-total-cells');
    const detailMoisture = document.getElementById('detail-moisture');
    const detailMeanTemp = document.getElementById('detail-mean-temp');
    const detailTempRange = document.getElementById('detail-temp-range');

    let selectedFile = null;
    let logInterval = null;

    // Log function
    function log(message, type = 'system') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        
        // Add timestamp
        const now = new Date();
        const timeStr = `[${now.toTimeString().split(' ')[0]}]`;
        line.innerText = `${timeStr} ${message}`;
        
        consoleOutput.appendChild(line);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }

    // Drag and drop handlers
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    dropzone.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    fileInput.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.type.startsWith('image/')) {
            log(`[!] 오류: 이미지 파일만 업로드할 수 있습니다. (선택됨: ${file.type})`, 'error');
            return;
        }
        selectedFile = file;
        fileInfo.innerText = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        submitBtn.removeAttribute('disabled');
        log(`[*] 파일 선택 완료: ${file.name}`);
    }

    // Clear logs
    clearLogsBtn.addEventListener('click', () => {
        consoleOutput.innerHTML = '';
        log('[SYSTEM] 로그가 초기화되었습니다.');
    });

    // Form submission
    analysisForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        const damType = document.querySelector('input[name="dam-type"]:checked').value;
        
        // Prepare UI state
        submitBtn.setAttribute('disabled', 'true');
        submitBtn.classList.add('loading');
        
        consoleOutput.innerHTML = '';
        log('[SYSTEM] 댐 열화상 분석 요청을 생성하는 중...', 'system');
        log(`[SYSTEM] 댐 재질 모델: ${damType.toUpperCase()}`, 'system');
        log('[SYSTEM] 이미지 업로드 중...', 'system');

        // Simulate progress logs in console to engage user
        let progressStep = 0;
        const progressMessages = [
            { text: '[+] 파일 업로드 성공! 백엔드에서 분석 대기열에 등록되었습니다.', delay: 1500, type: 'success' },
            { text: '[*] 분석 락(Lock) 획득 완료. 댐 열화상 분석 파이프라인 가동...', delay: 3000, type: 'system' },
            { text: '[>] [Step 1/3] Blender headless 백업 씬 및 기본 기하학 셀 모델 생성 중...', delay: 5000, type: 'run' },
            { text: '[>] [Step 2/3] Python 이미지 전처리 및 이상(Anomaly) 온도 구간 탐지 solver 실행 중...', delay: 9000, type: 'run' },
            { text: '[>] [Step 3/3] Blender 3D 렌더러 로딩 및 리스크 레벨 색상 투영 렌더링 이미지 추출 중...', delay: 14000, type: 'run' }
        ];

        const logTimeouts = [];
        progressMessages.forEach(msg => {
            const timeout = setTimeout(() => {
                log(msg.text, msg.type);
            }, msg.delay);
            logTimeouts.push(timeout);
        });

        // Send API request
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('dam_type', damType);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            // Clear the simulated logs timeouts
            logTimeouts.forEach(t => clearTimeout(t));

            const result = await response.json();

            if (response.ok && result.success) {
                log('[+] 분석 파이프라인이 성공적으로 완료되었습니다!', 'success');
                
                // Show raw server logs
                log('================ SERVER EXECUTION LOG ================', 'system');
                const logLines = result.logs.split('\n');
                logLines.forEach(line => {
                    if (line.trim()) {
                        if (line.includes('Error') || line.includes('[!]')) {
                            log(line, 'error');
                        } else if (line.includes('Successful') || line.includes('[+]') || line.includes('Finished')) {
                            log(line, 'success');
                        } else if (line.includes('[>]')) {
                            log(line, 'run');
                        } else {
                            log(line, 'system');
                        }
                    }
                });
                log('=======================================================', 'system');

                // Render results
                displayResults(result);
            } else {
                log(`[!] 오류 발생: ${result.error || '분석 실패'}`, 'error');
                if (result.logs) {
                    log('================ ERROR LOG ================', 'error');
                    log(result.logs, 'system');
                }
            }
        } catch (error) {
            logTimeouts.forEach(t => clearTimeout(t));
            log(`[!] 서버 통신 오류: ${error.message}`, 'error');
        } finally {
            submitBtn.removeAttribute('disabled');
            submitBtn.classList.remove('loading');
        }
    });

    // Populate results and display
    function displayResults(data) {
        // Show Display Card, Hide Placeholder
        resultsPlaceholder.classList.add('hidden');
        resultsDisplay.classList.remove('hidden');

        // Cache-busting parameter
        const timestamp = new Date().getTime();
        
        resultMeta.innerText = `세션 ID: ${data.session_id}`;
        
        if (data.render_image_url) {
            resultRenderImg.src = `${data.render_image_url}?t=${timestamp}`;
        }
        if (data.original_image_url) {
            resultOriginalImg.src = `${data.original_image_url}?t=${timestamp}`;
        }

        // Parse and display stats
        const stats = data.stats;
        
        // 1. Risk levels
        const rLevels = stats.metadata?.analysis_summary?.risk_levels || { "0": 0, "1": 0, "2": 0, "3": 0 };
        statRisk3.innerText = rLevels["3"] || 0;
        statRisk2.innerText = rLevels["2"] || 0;
        statRisk1.innerText = rLevels["1"] || 0;
        statRisk0.innerText = rLevels["0"] || 0;

        // 2. Total Grid Cells
        detailTotalCells.innerText = `${stats.metadata?.analysis_summary?.total_cells || '-'}개`;

        // 3. Moisture / Seepage Level
        const moisture = stats.metadata?.analysis_summary?.moisture_levels || { "low": 0, "medium": 0, "high": 0 };
        const highMoist = moisture["high"] || 0;
        const medMoist = moisture["medium"] || 0;
        detailMoisture.innerText = `High: ${highMoist} / Mid: ${medMoist}`;

        // 4. Calculate Temperature metrics directly from the cells list if available
        if (data.stats.cells && data.stats.cells.length > 0) {
            const cells = data.stats.cells;
            let tempSum = 0;
            let minTemp = Infinity;
            let maxTemp = -Infinity;
            let validCellCount = 0;

            cells.forEach(cell => {
                if (typeof cell.thermal_mean_temp_c === 'number') {
                    const temp = cell.thermal_mean_temp_c;
                    tempSum += temp;
                    if (temp < minTemp) minTemp = temp;
                    if (temp > maxTemp) maxTemp = temp;
                    validCellCount++;
                }
            });

            if (validCellCount > 0) {
                const meanTemp = tempSum / validCellCount;
                detailMeanTemp.innerText = `${meanTemp.toFixed(2)} °C`;
                detailTempRange.innerText = `${minTemp.toFixed(1)}°C ~ ${maxTemp.toFixed(1)}°C`;
            } else {
                detailMeanTemp.innerText = '-';
                detailTempRange.innerText = '-';
            }
        } else {
            detailMeanTemp.innerText = '-';
            detailTempRange.innerText = '-';
        }
    }

    // Tabs logic
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active class to clicked button and target tab content
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            document.getElementById(targetId).classList.add('active');
        });
    });
});
