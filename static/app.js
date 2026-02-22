// LeetCode Helper - SPA Logic

// Roadmap Manager
class RoadmapManager {
    constructor(app) {
        this.app = app;
        this.roadmapData = null;
        this.userProgress = {
            currentDay: 1,
            currentPhase: 1,
            completedDays: [],
            unlockedPhases: [1]
        };
        this.currentView = 'problems';
    }

    async init() {
        await this.loadRoadmapData();
        await this.loadRoadmapProgress();
        this.bindEvents();
    }

    async loadRoadmapData() {
        try {
            const response = await fetch('/static/roadmap.json');
            this.roadmapData = await response.json();
        } catch (error) {
            console.error('Failed to load roadmap data:', error);
        }
    }

    async loadRoadmapProgress() {
        try {
            const response = await fetch('/api/roadmap/progress');
            const data = await response.json();
            if (data.currentDay) {
                this.userProgress = data;
            }
        } catch (error) {
            console.error('Failed to load roadmap progress:', error);
        }
    }

    bindEvents() {
        // Nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const page = e.target.dataset.page;
                this.switchPage(page);
            });
        });

        // Modal close buttons
        document.getElementById('modalBackBtn').addEventListener('click', () => this.closeModal());
        document.getElementById('modalCloseBtn').addEventListener('click', () => this.closeModal());

        // Close modal on backdrop click
        document.getElementById('dayDetailModal').addEventListener('click', (e) => {
            if (e.target.id === 'dayDetailModal') {
                this.closeModal();
            }
        });
    }

    switchPage(page) {
        this.currentView = page;

        // Update nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.page === page);
        });

        // Show/hide pages
        const mainContent = document.querySelector('.main-content');
        const sidebar = document.querySelector('.sidebar');
        const roadmapPage = document.getElementById('roadmapPage');

        if (page === 'roadmap') {
            mainContent.style.display = 'none';
            sidebar.style.display = 'none';
            roadmapPage.style.display = 'flex';
            roadmapPage.style.flexDirection = 'column';
            this.renderRoadmap();
        } else {
            mainContent.style.display = 'flex';
            sidebar.style.display = 'flex';
            roadmapPage.style.display = 'none';
        }
    }

    renderRoadmap() {
        if (!this.roadmapData) return;

        const phasesContainer = document.getElementById('roadmapPhases');
        phasesContainer.innerHTML = '';

        // Update overall progress
        this.updateOverallProgress();

        // Render each phase
        this.roadmapData.phases.forEach(phase => {
            const phaseCard = this.renderPhase(phase);
            phasesContainer.appendChild(phaseCard);
        });
    }

    updateOverallProgress() {
        const currentDay = this.userProgress.currentDay || 1;
        const completedCount = this.userProgress.completedDays?.length || 0;
        const percent = Math.round((completedCount / 60) * 100);

        document.getElementById('currentDayDisplay').textContent = currentDay;
        document.getElementById('roadmapProgressBar').style.width = `${percent}%`;
        document.getElementById('roadmapProgressPercent').textContent = `${percent}%`;
    }

    renderPhase(phase) {
        const isUnlocked = this.userProgress.unlockedPhases?.includes(phase.id) || phase.id === 1;
        const phaseDays = phase.days || [];
        const totalDays = phaseDays.length;
        const completedDays = phaseDays.filter(d => this.userProgress.completedDays?.includes(d.day)).length;
        const phasePercent = totalDays > 0 ? Math.round((completedDays / totalDays) * 100) : 0;

        const card = document.createElement('div');
        card.className = `phase-card${!isUnlocked ? ' locked' : ''}`;

        const lockIcon = !isUnlocked ? '<span class="phase-lock">🔒</span>' : '';

        card.innerHTML = `
            <div class="phase-header">
                <span class="phase-icon">${phase.icon}</span>
                <div class="phase-info">
                    <div class="phase-name">
                        ${phase.name}
                        ${lockIcon}
                    </div>
                    <div class="phase-subtitle">${phase.subtitle}</div>
                    <div class="phase-description">${phase.description}</div>
                </div>
                <div class="phase-progress">
                    <div class="phase-progress-bar">
                        <div class="phase-progress-fill" style="width: ${phasePercent}%"></div>
                    </div>
                    <div class="phase-progress-text">${completedDays}/${totalDays} days</div>
                </div>
            </div>
            <div class="phase-days"></div>
        `;

        // Render days
        const daysContainer = card.querySelector('.phase-days');
        phaseDays.forEach(day => {
            const dayCard = this.renderDayCard(day, phase);
            daysContainer.appendChild(dayCard);
        });

        // Toggle collapse on header click
        const header = card.querySelector('.phase-header');
        header.addEventListener('click', () => {
            daysContainer.style.display = daysContainer.style.display === 'none' ? 'grid' : 'none';
        });

        return card;
    }

    renderDayCard(day, phase) {
        const isCompleted = this.userProgress.completedDays?.includes(day.day);
        const isCurrent = this.userProgress.currentDay === day.day;
        const isUnlocked = this.userProgress.unlockedPhases?.includes(phase.id) || phase.id === 1;

        const card = document.createElement('div');
        card.className = `day-card${isCompleted ? ' completed' : ''}${isCurrent ? ' current' : ''}${!isUnlocked ? ' locked' : ''}`;

        const totalProblems = day.problems?.length || 0;
        const solvedProblems = day.problems?.filter(p => this.app.isProblemSolved(p.leetcodeId)).length || 0;

        const statusIcon = isCompleted ? '<span class="day-status completed">✓</span>' : '';
        const currentIndicator = isCurrent ? '→' : '';

        card.innerHTML = `
            <div class="day-header">
                <span class="day-number">${currentIndicator} Day ${day.day}</span>
                <span class="day-title">${day.title}</span>
                ${statusIcon}
            </div>
            <div class="day-problems">
                <span class="day-problems-count">${solvedProblems}/${totalProblems}</span>
                <span>solved</span>
            </div>
        `;

        if (isUnlocked) {
            card.addEventListener('click', () => this.openDayDetail(day, phase));
        }

        return card;
    }

    openDayDetail(day, phase) {
        const modal = document.getElementById('dayDetailModal');
        const modalBody = document.getElementById('modalBody');

        const totalProblems = day.problems?.length || 0;
        const solvedProblems = day.problems?.filter(p => this.app.isProblemSolved(p.leetcodeId)).length || 0;
        const isCompleted = this.userProgress.completedDays?.includes(day.day);
        const isCurrent = this.userProgress.currentDay === day.day;

        const canMarkComplete = solvedProblems >= totalProblems && !isCompleted;

        let problemsHtml = '';
        if (day.problems && day.problems.length > 0) {
            problemsHtml = `
                <div class="day-problems-section">
                    <h3>Problems for Today</h3>
                    <div class="day-problem-list">
                        ${day.problems.map(p => {
                const isSolved = this.app.isProblemSolved(p.leetcodeId);
                return `
                                <div class="day-problem-item${isSolved ? ' solved' : ''}" data-problem-id="${p.leetcodeId}">
                                    <div class="day-problem-check">${isSolved ? '✓' : ''}</div>
                                    <div class="day-problem-info">
                                        <div class="day-problem-id">#${p.leetcodeId}</div>
                                        <div class="day-problem-title">${this.escapeHtml(p.title)}</div>
                                    </div>
                                    <span class="day-problem-difficulty ${p.difficulty}">${p.difficulty}</span>
                                </div>
                            `;
            }).join('')}
                    </div>
                </div>
            `;
        }

        let tipsHtml = '';
        if (day.tips && day.tips.length > 0) {
            tipsHtml = `
                <div class="day-tips-section">
                    <h3>💡 Tips for Today</h3>
                    <ul class="day-tips-list">
                        ${day.tips.map(tip => `<li>${this.escapeHtml(tip)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        modalBody.innerHTML = `
            <div class="day-detail-header">
                <h2 class="day-detail-title">Day ${day.day}: ${this.escapeHtml(day.title)}</h2>
                <div class="day-detail-focus">
                    <span class="day-detail-focus-label">Focus:</span>
                    <span>${this.escapeHtml(day.focus)}</span>
                </div>
            </div>

            <div class="day-detail-progress">
                <span class="day-detail-progress-text${solvedProblems >= totalProblems ? ' all-done' : ''}">
                    ${solvedProblems >= totalProblems ? '✓ All done!' : `Progress: ${solvedProblems}/${totalProblems} problems solved`}
                </span>
                <div class="day-detail-actions">
                    ${isCurrent && !isCompleted ? `
                        <button class="mark-day-btn" ${canMarkComplete ? '' : 'disabled'}>
                            ${canMarkComplete ? 'Mark Day Complete' : 'Solve all problems first'}
                        </button>
                    ` : ''}
                    ${isCompleted ? '<span style="color: var(--success); font-weight: 500;">Day Completed ✓</span>' : ''}
                </div>
            </div>

            ${problemsHtml}
            ${tipsHtml}
        `;

        // Add click handlers for problems
        modalBody.querySelectorAll('.day-problem-item').forEach(item => {
            item.addEventListener('click', () => {
                const problemId = item.dataset.problemId;
                this.closeModal();
                this.switchPage('problems');
                this.app.loadProblem(problemId);
            });
        });

        // Add click handler for mark day complete
        const markBtn = modalBody.querySelector('.mark-day-btn');
        if (markBtn && canMarkComplete) {
            markBtn.addEventListener('click', () => this.markDayComplete(day.day));
        }

        modal.style.display = 'flex';
    }

    closeModal() {
        document.getElementById('dayDetailModal').style.display = 'none';
    }

    async markDayComplete(day) {
        try {
            const response = await fetch('/api/roadmap/progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'complete_day', day: day })
            });

            const data = await response.json();
            if (data.success) {
                this.userProgress = data.progress;
                this.closeModal();
                this.renderRoadmap();
            }
        } catch (error) {
            console.error('Failed to mark day complete:', error);
        }
    }

    async setCurrentDay(day) {
        try {
            const response = await fetch('/api/roadmap/progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'set_day', day: day })
            });

            const data = await response.json();
            if (data.success) {
                this.userProgress = data.progress;
                this.renderRoadmap();
            }
        } catch (error) {
            console.error('Failed to set current day:', error);
        }
    }

    updateProgress() {
        // Recalculate phase unlocks based on completed days
        const phases = this.roadmapData?.phases || [];

        phases.forEach((phase, index) => {
            const prevPhase = index > 0 ? phases[index - 1] : null;
            const prevPhaseComplete = !prevPhase || this.isPhaseComplete(prevPhase);

            if (prevPhaseComplete && !this.userProgress.unlockedPhases?.includes(phase.id)) {
                this.userProgress.unlockedPhases = this.userProgress.unlockedPhases || [];
                this.userProgress.unlockedPhases.push(phase.id);

                // Auto-advance current day if needed
                if (this.userProgress.currentDay < phase.startDay) {
                    this.userProgress.currentDay = phase.startDay;
                }
            }
        });

        this.renderRoadmap();
    }

    isPhaseComplete(phase) {
        if (!phase.days) return false;
        return phase.days.every(d => this.userProgress.completedDays?.includes(d.day));
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Custom Select Dropdown Component

// Custom Select Dropdown Component
class CustomSelect {
    constructor(element, onChange) {
        this.container = element;
        this.input = element.querySelector('.select-input');
        this.toggle = element.querySelector('.select-toggle');
        this.dropdown = element.querySelector('.select-dropdown');
        this.options = Array.from(element.querySelectorAll('.select-option'));
        this.onChange = onChange;
        this.selectedValue = '';
        this.selectedIndex = -1;
        this.isOpen = false;

        this.init();
    }

    init() {
        // Toggle dropdown on input click or toggle button click
        this.input.addEventListener('click', (e) => {
            e.stopPropagation();
            this.open();
        });

        this.toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });

        // Handle typing to filter
        this.input.addEventListener('input', () => {
            this.input.removeAttribute('readonly');
            this.filterOptions(this.input.value);
            this.open();
        });

        this.input.addEventListener('keydown', (e) => {
            this.handleKeydown(e);
        });

        // Handle option selection
        this.options.forEach((option, index) => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectOption(option);
            });
        });

        // Close on click outside
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.close();
            }
        });
    }

    toggleDropdown() {
        this.isOpen ? this.close() : this.open();
    }

    open() {
        this.isOpen = true;
        this.container.classList.add('open');
        this.selectedIndex = -1;
        this.updateHighlight();
    }

    close() {
        this.isOpen = false;
        this.container.classList.remove('open');
        this.input.setAttribute('readonly', '');
        // Reset to selected value text
        if (this.selectedValue) {
            const selectedOption = this.options.find(opt => opt.getAttribute('value') === this.selectedValue);
            if (selectedOption) {
                this.input.value = selectedOption.textContent;
            }
        } else {
            this.input.value = this.options[0]?.textContent || '';
        }
    }

    filterOptions(search) {
        const searchLower = search.toLowerCase();
        this.options.forEach(option => {
            const text = option.textContent.toLowerCase();
            if (text.includes(searchLower)) {
                option.classList.remove('hidden');
            } else {
                option.classList.add('hidden');
            }
        });
    }

    handleKeydown(e) {
        const visibleOptions = this.options.filter(opt => !opt.classList.contains('hidden'));

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (!this.isOpen) this.open();
            this.selectedIndex = Math.min(this.selectedIndex + 1, visibleOptions.length - 1);
            this.updateHighlight();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (!this.isOpen) this.open();
            this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
            this.updateHighlight();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.isOpen && this.selectedIndex >= 0 && visibleOptions[this.selectedIndex]) {
                this.selectOption(visibleOptions[this.selectedIndex]);
            } else {
                this.close();
            }
        } else if (e.key === 'Escape') {
            this.close();
        } else if (e.key === 'Tab') {
            this.close();
        }
    }

    updateHighlight() {
        const visibleOptions = this.options.filter(opt => !opt.classList.contains('hidden'));
        visibleOptions.forEach((option, index) => {
            option.classList.toggle('selected', index === this.selectedIndex);
        });
    }

    selectOption(option) {
        // Update UI
        this.options.forEach(opt => opt.classList.remove('selected'));
        option.classList.add('selected');
        this.input.value = option.textContent;
        this.selectedValue = option.getAttribute('value');

        this.close();

        // Trigger change callback
        if (this.onChange) {
            this.onChange(this.selectedValue);
        }
    }

    setValue(value) {
        this.selectedValue = value;
        const option = this.options.find(opt => opt.getAttribute('value') === value);
        if (option) {
            this.input.value = option.textContent;
            this.options.forEach(opt => opt.classList.remove('selected'));
            option.classList.add('selected');
        } else {
            this.input.value = this.options[0]?.textContent || '';
        }
    }

    getValue() {
        return this.selectedValue;
    }

    addOption(value, text) {
        const option = document.createElement('div');
        option.className = 'select-option';
        option.setAttribute('value', value);
        option.textContent = text;
        option.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectOption(option);
        });
        this.dropdown.appendChild(option);
        this.options.push(option);
    }

    clearOptions() {
        // Keep the first default option
        const defaultOption = this.options[0];
        this.dropdown.innerHTML = '';
        this.dropdown.appendChild(defaultOption);
        this.options = [defaultOption];
    }
}

class LeetCodeApp {
    constructor() {
        this.problems = [];
        this.currentProblem = null;
        this.allTags = new Set();
        this.searchDebounce = null;
        this.saveCodeDebounce = null;
        this.editor = null;
        this.customSelects = {};
        this.roadmap = null;
        this.currentSolutionPath = null;

        this.hintsSection = null;
        this.hintsList = null;
        this.hintLevel = 0;
        this.viewingHintLevel = 0;
        this.currentHints = [];

        this.init();
    }

    async init() {
        this.cacheElements();
        this.bindEvents();
        await this.loadProblems();
        this.initCustomSelects();
        this.initCodeMirror();

        // Load API key from localStorage
        this.apiKey = localStorage.getItem('openrouter_api_key') || '';

        // Initialize roadmap
        this.roadmap = new RoadmapManager(this);
        await this.roadmap.init();
    }

    cacheElements() {
        // Header elements
        this.searchInput = document.getElementById('searchInput');
        this.difficultyFilterEl = document.getElementById('difficultyFilter');
        this.statusFilterEl = document.getElementById('statusFilter');
        this.randomBtn = document.getElementById('randomBtn');
        this.collapseBtn = document.getElementById('collapseBtn');
        this.collapseIcon = document.getElementById('collapseIcon');
        this.settingsBtn = document.getElementById('settingsBtn');

        // Settings modal
        this.settingsModal = document.getElementById('settingsModal');
        this.closeSettingsBtn = document.getElementById('closeSettingsBtn');
        this.apiKeyInput = document.getElementById('apiKeyInput');
        this.saveApiKeyBtn = document.getElementById('saveApiKeyBtn');

        // Main container
        this.mainContainer = document.querySelector('.main-container');

        // Sidebar elements
        this.problemCount = document.getElementById('problemCount');
        this.problemList = document.getElementById('problemList');

        // Main content elements
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.problemView = document.getElementById('problemView');
        this.totalProblems = document.getElementById('totalProblems');

        // Problem detail elements
        this.problemId = document.getElementById('problemId');
        this.problemTitle = document.getElementById('problemTitle');
        this.problemDifficulty = document.getElementById('problemDifficulty');
        this.problemMeta = document.getElementById('problemMeta');
        this.problemTags = document.getElementById('problemTags');
        this.problemContent = document.getElementById('problemContent');
        this.testCasesList = document.getElementById('testCasesList');
        this.codeEditor = document.getElementById('codeEditor');
        this.solvedBtn = document.getElementById('solvedBtn');

        // Test results
        this.testResults = document.getElementById('testResults');
        this.resultsHeader = document.getElementById('resultsHeader');
        this.resultsSummary = document.getElementById('resultsSummary');
        this.resultsList = document.getElementById('resultsList');
        this.closeResults = document.getElementById('closeResults');
        this.expandResults = document.getElementById('expandResults');
        this.runBtn = document.getElementById('runBtn');
        this.submitBtn = document.getElementById('submitBtn');
        this.aiBtn = document.getElementById('aiBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.draftBadge = document.getElementById('draftBadge');
        this.hintBadge = document.getElementById('hintBadge');
    }

    bindEvents() {
        // Search
        this.searchInput.addEventListener('input', () => {
            clearTimeout(this.searchDebounce);
            this.searchDebounce = setTimeout(() => this.filterProblems(), 150);
        });

        // Sidebar tabs / content switching
        document.querySelectorAll('.panel-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const contentId = e.target.dataset.content;
                this.switchDescriptionTab(contentId);
            });
        });

        // Collapse button
        this.collapseBtn.addEventListener('click', () => this.toggleSidebar());

        // Random button
        this.randomBtn.addEventListener('click', () => this.loadRandomProblem());

        // Settings button
        this.settingsBtn.addEventListener('click', () => this.openSettings());
        this.closeSettingsBtn.addEventListener('click', () => this.closeSettings());
        this.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.settingsModal) this.closeSettings();
        });
        this.saveApiKeyBtn.addEventListener('click', () => this.saveApiKey());

        // Run button
        this.runBtn.addEventListener('click', () => this.runTests());

        // Ask AI button
        if (this.aiBtn) {
            this.aiBtn.addEventListener('click', () => this.startAISolution());
        }

        // Hint modal backdrop close
        document.getElementById('hintModal').addEventListener('click', (e) => {
            if (e.target.id === 'hintModal') {
                document.getElementById('hintModal').style.display = 'none';
            }
        });

        // Hint modal footer buttons
        const hintPrevBtn = document.getElementById('hintPrevBtn');
        if (hintPrevBtn) hintPrevBtn.addEventListener('click', () => this.navigateToPrevHint());

        const hintNextBtn = document.getElementById('hintNextBtn');
        if (hintNextBtn) hintNextBtn.addEventListener('click', () => this.navigateToNextHint());

        const hintNewAngleBtn = document.getElementById('hintNewAngleBtn');
        if (hintNewAngleBtn) hintNewAngleBtn.addEventListener('click', () => this.regenerateCurrentHint());

        const hintInsertBtn = document.getElementById('hintInsertBtn');
        if (hintInsertBtn) hintInsertBtn.addEventListener('click', () => this.applyHintToEditor());

        // Reset code button
        if (this.resetBtn) {
            this.resetBtn.addEventListener('click', () => this.resetCode());
        }

        // Close results
        this.closeResults.addEventListener('click', (e) => {
            e.stopPropagation();
            this.resultsList.style.display = 'none';
            this.expandResults.textContent = '▲';
        });

        // Toggle results/console
        this.resultsHeader.addEventListener('click', () => {
            const isVisible = this.resultsList.style.display !== 'none';
            this.resultsList.style.display = isVisible ? 'none' : 'block';
            this.expandResults.textContent = isVisible ? '▲' : '▼';
        });

        // Submit button
        this.submitBtn.addEventListener('click', () => this.toggleSolved());

        // Solved button
        this.solvedBtn.addEventListener('click', () => this.toggleSolved());
    }

    switchDescriptionTab(tabId) {
        document.querySelectorAll('.panel-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.content === tabId);
        });
        document.querySelectorAll('.tab-content').forEach(c => {
            c.classList.toggle('active', c.id === `content-${tabId}`);
        });
    }

    initCustomSelects() {
        // Initialize custom selects with change callbacks
        this.customSelects.difficulty = new CustomSelect(
            this.difficultyFilterEl,
            () => this.filterProblems()
        );

        this.customSelects.status = new CustomSelect(
            this.statusFilterEl,
            () => this.filterProblems()
        );
    }

    initCodeMirror() {
        const mount = document.getElementById('editor-main-mount');
        if (!mount) { console.error('editor-main-mount not found'); return; }

        const tryInit = () => {
            if (!window.ace) {
                setTimeout(tryInit, 50);
                return;
            }

            try {
                this.editorView = ace.edit("editor-main-mount");
                this.editorView.setTheme("ace/theme/github");
                this.editorView.session.setMode("ace/mode/python");
                this.editorView.setOptions({
                    fontSize: "13px",
                    fontFamily: "'JetBrains Mono', 'Cascadia Code', 'Fira Code', Consolas, monospace",
                    tabSize: 4,
                    useSoftTabs: true,
                    showPrintMargin: false,
                    displayIndentGuides: false,
                    wrap: true,
                    highlightActiveLine: true,
                    showGutter: true,
                    behavioursEnabled: true
                });

                // Set initial value
                const initialCode = this.codeEditor ? this.codeEditor.value : '';
                this.editorView.setValue(initialCode, -1);

                // Add run keybindings
                this.editorView.commands.addCommand({
                    name: 'runTests',
                    bindKey: { win: 'Ctrl-Enter', mac: 'Command-Enter' },
                    exec: (editor) => {
                        this.runTests();
                    }
                });

                // Listen to changes
                this.editorView.session.on('change', () => {
                    clearTimeout(this.saveCodeDebounce);
                    this.saveCodeDebounce = setTimeout(() => this.saveCode(), 1000);
                    if (this.currentProblem && !this.currentProblem.solved && this.draftBadge) {
                        this.draftBadge.style.display = '';
                    }
                });
            } catch (err) {
                console.error('Failed to create Ace editor:', err);
            }
        };

        tryInit();
    }

    // Helper methods for Ace Editor compatibility
    getEditorValue() {
        if (this.editorView) {
            return this.editorView.getValue();
        }
        return this.codeEditor.value;
    }

    setEditorValue(code) {
        if (this.editorView) {
            this.editorView.setValue(code, -1);
            return;
        }
        this.codeEditor.value = code;
    }

    focusEditor() {
        if (this.editorView) {
            this.editorView.focus();
        }
    }

    editorExists() {
        return this.editorView !== null && this.editorView !== undefined;
    }

    async loadProblems() {
        try {
            const response = await fetch('/api/problems');
            this.problems = await response.json();

            this.problemCount.textContent = `${this.problems.length} problems`;
            this.totalProblems.textContent = this.problems.length;

            this.renderProblemList(this.problems);
        } catch (error) {
            console.error('Failed to load problems:', error);
            this.problemCount.textContent = 'Failed to load';
        }
    }

    filterProblems() {
        const search = this.searchInput.value.toLowerCase();
        const difficulty = this.customSelects.difficulty.getValue();
        const status = this.customSelects.status.getValue();

        const filtered = this.problems.filter(p => {
            // Search
            if (search && !p.title.toLowerCase().includes(search)) {
                const tags = (p.topic_tags || []).join(' ').toLowerCase();
                if (!tags.includes(search)) return false;
            }

            // Difficulty
            if (difficulty && p.difficulty !== difficulty) return false;

            // Status
            if (status === 'solved' && !p.solved) return false;
            if (status === 'unsolved' && p.solved) return false;

            return true;
        });

        this.renderProblemList(filtered);
    }

    getFilteredProblems() {
        const search = this.searchInput.value.toLowerCase();
        const difficulty = this.customSelects.difficulty.getValue();
        const status = this.customSelects.status.getValue();

        return this.problems.filter(p => {
            // Search
            if (search && !p.title.toLowerCase().includes(search)) {
                const tags = (p.topic_tags || []).join(' ').toLowerCase();
                if (!tags.includes(search)) return false;
            }

            // Difficulty
            if (difficulty && p.difficulty !== difficulty) return false;

            // Status
            if (status === 'solved' && !p.solved) return false;
            if (status === 'unsolved' && p.solved) return false;

            return true;
        });
    }

    loadRandomProblem() {
        const filtered = this.getFilteredProblems();
        if (filtered.length === 0) {
            this.showToast('No problems match the current filters', 'warning');
            return;
        }
        const random = filtered[Math.floor(Math.random() * filtered.length)];
        this.loadProblem(random.id);
    }

    toggleSidebar() {
        this.mainContainer.classList.toggle('sidebar-collapsed');
        const isCollapsed = this.mainContainer.classList.contains('sidebar-collapsed');
        this.collapseIcon.textContent = isCollapsed ? '▶' : '◀';
        this.collapseBtn.title = isCollapsed ? 'Show Sidebar' : 'Hide Sidebar';
    }

    renderProblemList(problems) {
        this.problemList.innerHTML = '';

        if (problems.length === 0) {
            this.problemList.innerHTML = '<div class="loading">No problems found</div>';
            return;
        }

        const fragment = document.createDocumentFragment();

        problems.forEach(p => {
            const item = document.createElement('div');
            item.className = `problem-item${p.solved ? ' solved' : ''}${this.currentProblem?.id === p.id ? ' active' : ''}`;
            item.dataset.id = p.id;

            const difficultyClass = p.difficulty || 'Medium';
            const solvedIcon = p.solved ? '✓' : '';

            item.innerHTML = `
                <div class="problem-item-title">${this.escapeHtml(p.title)}</div>
                <div class="problem-item-meta">
                    <span class="problem-item-id">#${p.frontend_id || p.id}</span>
                    <span class="problem-item-difficulty ${difficultyClass}">${p.difficulty || 'Medium'}</span>
                    <span class="problem-item-solved">${solvedIcon}</span>
                </div>
            `;

            item.addEventListener('click', () => this.loadProblem(p.id));
            fragment.appendChild(item);
        });

        this.problemList.appendChild(fragment);
    }


    async loadProblem(problemId) {
        try {
            // Update active state in list
            document.querySelectorAll('.problem-item').forEach(item => {
                item.classList.toggle('active', item.dataset.id === problemId);
            });

            const response = await fetch(`/api/problem/${problemId}`);
            const problem = await response.json();

            this.currentProblem = problem;
            this.renderProblem(problem);

            // Ensure we are on the description tab
            this.switchDescriptionTab('description');

            // Clear hints and draft badge when loading new problem
            this.clearHints();
            if (this.draftBadge) this.draftBadge.style.display = 'none';

            // Show problem view
            this.welcomeScreen.style.display = 'none';
            this.problemView.style.display = 'flex';
            this.testResults.style.display = 'none';

            // Refresh editor after showing problem view (CodeMirror 6 doesn't need manual refresh)

        } catch (error) {
            console.error('Failed to load problem:', error);
        }
    }

    renderProblem(problem) {
        // Basic info
        this.problemId.textContent = `#${problem.frontend_id || problem.id}`;
        this.problemTitle.textContent = problem.title;
        this.problemDifficulty.textContent = problem.difficulty || 'Medium';
        this.problemDifficulty.className = `badge difficulty-badge ${problem.difficulty || 'Medium'}`;

        // Solved button state
        this.updateSolvedButton(problem.solved);

        // Meta info
        const acceptance = problem.acceptance_rate ? `${(problem.acceptance_rate * 100).toFixed(1)}% Acceptance` : '';
        const likes = problem.likes ? `${(problem.likes / 1000).toFixed(1)}K likes` : '';
        this.problemMeta.textContent = [acceptance, likes].filter(Boolean).join(' • ');

        // Tags
        this.problemTags.innerHTML = '';
        (problem.topic_tags || []).forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'tag';
            tagEl.textContent = tag;
            tagEl.addEventListener('click', () => {
                this.searchInput.value = tag;
                this.filterProblems();
            });
            this.problemTags.appendChild(tagEl);
        });

        // Description
        this.problemContent.innerHTML = problem.content || 'No description available.';

        // Test cases
        this.renderTestCases(problem.example_test_cases);

        // Code editor
        this.loadProblemCode(problem);
    }

    async loadProblemCode(problem) {
        const problemId = problem.id || problem.frontend_id;

        // First, try to load saved code from progress
        try {
            const progressResponse = await fetch('/api/progress');
            const progress = await progressResponse.json();

            if (progress.solved && progress.solved[problemId] && progress.solved[problemId].code) {
                // Load saved code
                const savedCode = progress.solved[problemId].code;
                this.setEditorValue(savedCode);
                return;
            }
        } catch (error) {
            console.error('Failed to load saved code:', error);
        }

        // No saved code, load starter code
        this.loadStarterCode(problem);
    }

    loadStarterCode(problem) {
        // Find Python3 snippet
        const snippets = problem.code_snippets || [];
        const pythonSnippet = snippets.find(s => s.lang === 'python3' || s.lang === 'python');

        let code = '';
        if (pythonSnippet) {
            code = pythonSnippet.code || '';
        } else {
            // Default template
            code = `class Solution:
    def solve(self, *args):
        # Your solution here
        pass
`;
        }

        this.setEditorValue(code);
    }

    async saveCode() {
        if (!this.currentProblem) return;

        const code = this.getEditorValue();
        const problemId = this.currentProblem.id || this.currentProblem.frontend_id;

        try {
            await fetch('/api/progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'save_code',
                    problem_id: problemId,
                    code: code
                })
            });
        } catch (error) {
            console.error('Failed to save code:', error);
        }
    }

    renderTestCases(testCasesStr) {
        this.testCasesList.innerHTML = '';

        if (!testCasesStr) {
            this.testCasesList.innerHTML = '<p style="color: var(--text-3);">No example test cases available.</p>';
            return;
        }

        // Parse test cases (newline separated)
        const testCases = testCasesStr.split('\n').filter(t => t.trim());

        testCases.forEach((testCase, index) => {
            const item = document.createElement('div');
            item.className = 'test-case-item';

            // Try to parse input/output
            let input = testCase.trim();
            let output = '';

            // Look for output patterns
            if (input.includes('Output:')) {
                const parts = input.split('Output:');
                input = parts[0].replace(/Input:/, '').trim();
                output = parts[1].trim();
            }

            item.innerHTML = `
                <div class="test-case-input">Case ${index + 1}: <span>${this.escapeHtml(input)}</span></div>
                ${output ? `<div class="test-case-output">Output: ${this.escapeHtml(output)}</div>` : ''}
            `;

            this.testCasesList.appendChild(item);
        });
    }

    async runTests() {
        if (!this.currentProblem) return;

        const code = this.getEditorValue();
        const testCasesStr = this.currentProblem.example_test_cases;
        const problemContent = this.currentProblem.content || '';

        // Parse test cases and extract expected outputs
        const testCases = this.parseTestCases(testCasesStr);
        const expectedOutputs = this.extractExpectedOutputs(problemContent);

        // Show loading state
        this.runBtn.disabled = true;
        this.runBtn.innerHTML = '<span class="btn-icon">⟳</span> Running...';

        try {
            const response = await fetch('/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: code,
                    problem_id: String(this.currentProblem.id || this.currentProblem.frontend_id),
                    use_local_solution: true,
                    test_cases: testCases,
                    expected_outputs: expectedOutputs,
                    function_name: 'solve',
                    class_name: 'Solution'
                })
            });

            const result = await response.json();
            this.displayResults(result);

        } catch (error) {
            console.error('Failed to run tests:', error);
            this.displayResults({
                results: [{ passed: false, error: 'Failed to connect to server' }],
                passed: 0,
                total: 1
            });
        } finally {
            this.runBtn.disabled = false;
            this.runBtn.innerHTML = '<span class="btn-icon">▶</span> Run All Tests';
        }
    }

    async startAISolution() {
        if (!this.currentProblem) return;

        const problemTitle = this.currentProblem.title || '';
        const problemDescription = this.currentProblem.content || this.currentProblem.description || '';
        const testCases = this.parseTestCases(this.currentProblem.example_test_cases || '');

        const snippets = this.currentProblem.code_snippets || [];
        const pythonSnippet = snippets.find(s => s.lang === 'python3' || s.lang === 'python');
        const starterCode = pythonSnippet ? pythonSnippet.code : '';

        this.aiBtn.disabled = true;
        this.aiBtn.innerHTML = '<span class="btn-icon">⟳</span> Generating...';

        this.showAIPanelLoading();

        try {
            const response = await fetch('/api/ai/solution', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    problem_title: problemTitle,
                    problem_description: problemDescription.substring(0, 3000),
                    test_cases: testCases.slice(0, 3),
                    starter_code: starterCode
                })
            });

            const result = await response.json();

            if (result.error) {
                this.showToast('AI error: ' + result.error, 'error');
                this.closeAIPanel();
                return;
            }

            if (result.solution) {
                const solutionText = typeof result.solution === 'string' ? result.solution : (result.solution.code || '');

                const chatArea = document.getElementById('aiChatArea');
                const loadingBubble = chatArea.querySelector('.chat-bubble.loading');
                if (loadingBubble) loadingBubble.remove();

                const aiBubble = document.createElement('div');
                aiBubble.className = 'chat-bubble ai';
                aiBubble.innerHTML = this.renderAiExplanation(solutionText);
                chatArea.appendChild(aiBubble);
                chatArea.scrollTop = chatArea.scrollHeight;

                const codeMatch = solutionText.match(/```(?:python)?\n([\s\S]*?)```/i);
                if (codeMatch) {
                    this._lastAiCode = codeMatch[1].trim();
                } else {
                    this._lastAiCode = solutionText;
                }

                this._currentProblemTitle = problemTitle;

                const useBtn = document.getElementById('copyToEditorBtn');
                if (useBtn && codeMatch) {
                    useBtn.style.display = 'inline-flex';
                }
            }

        } catch (error) {
            console.error('Failed to get AI solution:', error);
            this.showToast('Failed to connect to AI service. Please try again.', 'error');
            this.closeAIPanel();
        } finally {
            this.aiBtn.disabled = false;
            this.aiBtn.innerHTML = '<span class="btn-icon">✨</span>';
        }
    }

    showAIPanelLoading() {
        const aiTabBtn = document.getElementById('aiTabBtn');
        if (aiTabBtn) aiTabBtn.style.display = 'flex';

        this.switchDescriptionTab('ai-solution');

        const useBtn = document.getElementById('copyToEditorBtn');
        if (useBtn) useBtn.style.display = 'none';

        const chatArea = document.getElementById('aiChatArea');
        if (chatArea) {
            chatArea.innerHTML = '';

            const userBubble = document.createElement('div');
            userBubble.className = 'chat-bubble user';
            userBubble.textContent = "Can you show me a solution for this problem?";
            chatArea.appendChild(userBubble);

            const aiBubble = document.createElement('div');
            aiBubble.className = 'chat-bubble ai loading';
            aiBubble.innerHTML = '<span class="typing-dots"><span></span><span></span><span></span></span>';
            chatArea.appendChild(aiBubble);
            chatArea.scrollTop = chatArea.scrollHeight;
        }

        const useActionBtn = document.getElementById('copyToEditorBtn');
        if (useActionBtn) {
            useActionBtn.onclick = () => {
                if (this._lastAiCode) {
                    this.setEditorValue(this._lastAiCode);
                    this.showToast('AI solution inserted into editor', 'success');
                    this.focusEditor();
                }
            };
        }

        const askInput = document.getElementById('aiAskInput');
        const askSend = document.getElementById('aiAskSendBtn');
        if (askInput && askSend) {
            askSend.onclick = () => {
                const q = askInput.value.trim();
                if (q) {
                    this.handleAiAsk(q);
                    askInput.value = '';
                }
            };
            askInput.onkeydown = (e) => {
                if (e.key === 'Enter') askSend.click();
            };
        }
    }

    closeAIPanel() {
        const aiTabBtn = document.getElementById('aiTabBtn');
        if (aiTabBtn) aiTabBtn.style.display = 'none';
        this.switchDescriptionTab('description');
    }

    async handleAiAsk(question) {
        if (!question) return;
        const chatArea = document.getElementById('aiChatArea');
        if (!chatArea) return;

        // User message bubble
        const userBubble = document.createElement('div');
        userBubble.className = 'chat-bubble user';
        userBubble.textContent = question;
        chatArea.appendChild(userBubble);

        // AI loading bubble
        const aiBubble = document.createElement('div');
        aiBubble.className = 'chat-bubble ai loading';
        aiBubble.innerHTML = '<span class="typing-dots"><span></span><span></span><span></span></span>';
        chatArea.appendChild(aiBubble);
        chatArea.scrollTop = chatArea.scrollHeight;

        const codeSnippet = this._lastAiCode || '';
        const problemTitle = this._currentProblemTitle || '';

        try {
            const response = await fetch('/api/ai/explain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, code_snippet: codeSnippet, problem_title: problemTitle })
            });
            const result = await response.json();

            aiBubble.classList.remove('loading');
            if (result.error) {
                aiBubble.innerHTML = `<span style="color:var(--error)">${this.escapeHtml(result.error)}</span>`;
            } else {
                aiBubble.innerHTML = this.renderAiExplanation(result.answer || '');
            }
        } catch (e) {
            aiBubble.classList.remove('loading');
            aiBubble.innerHTML = '<span style="color:var(--error)">Connection failed. Please try again.</span>';
        }
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    renderAiExplanation(text) {
        if (window.marked) {
            return marked.parse(text);
        }
        // Fallback
        let result = text;
        result = result.replace(/```python\n([\s\S]*?)```/g, (_, code) =>
            `<pre class="hint-code-block"><code>${this.escapeHtml(code.trim())}</code></pre>`);
        result = result.replace(/```([\s\S]*?)```/g, (_, code) =>
            `<pre class="hint-code-block"><code>${this.escapeHtml(code.trim())}</code></pre>`);
        result = result.replace(/`([^`]+)`/g, '<code class="hint-inline-code">$1</code>');
        result = result.replace(/\n/g, '<br>');
        return result;
    }

    parseTestCases(testCasesStr) {
        if (!testCasesStr) return [];

        const cases = [];
        const lines = testCasesStr.split('\n').filter(l => l.trim());

        // Group lines by pairs (or triples for some problems)
        // Most LeetCode problems have 2 args per test case
        let currentCase = [];
        lines.forEach(line => {
            const trimmed = line.trim();
            // Remove Input: prefix if present
            let input = trimmed.replace(/^Input:\s*/i, '');

            // Extract output if present
            if (input.includes('Output:')) {
                const parts = input.split('Output:');
                input = parts[0].trim();
            }

            currentCase.push(input);

            // Group by 2 lines (most common pattern)
            if (currentCase.length >= 2) {
                cases.push(currentCase);
                currentCase = [];
            }
        });

        // Handle remaining lines
        if (currentCase.length > 0) {
            cases.push(currentCase);
        }

        return cases.length > 0 ? cases : [['None']];
    }

    extractExpectedOutputs(content) {
        // Extract expected outputs from problem content HTML
        const outputs = [];

        // Match patterns like "Output: [0,1]" or "<strong>Output:</strong> [0,1]"
        const outputPatterns = [
            /Output:\s*([^\n<]+)/gi,
            /<strong>Output:<\/strong>\s*([^\n<]+)/gi
        ];

        for (const pattern of outputPatterns) {
            let match;
            while ((match = pattern.exec(content)) !== null) {
                const output = match[1].trim();
                if (output && !outputs.includes(output)) {
                    outputs.push(output);
                }
            }
        }

        return outputs;
    }

    displayResults(result) {
        this.testResults.style.display = 'flex';
        this.resultsList.style.display = 'block';
        this.expandResults.textContent = '▼';
        this.resultsList.innerHTML = '';

        // Summary
        const allPassed = result.passed === result.total;
        this.resultsSummary.textContent = `${result.passed}/${result.total} tests passed`;
        this.resultsSummary.className = allPassed ? 'passed' : 'failed';

        // Individual results
        result.results.forEach((r, i) => {
            const item = document.createElement('div');
            item.className = `result-item ${r.passed ? 'pass' : 'fail'}`;

            if (r.passed) {
                item.innerHTML = `<span class="result-status">✓ Test case ${i + 1} passed</span>`;
            } else {
                let html = `<span class="result-status">✗ Test case ${i + 1} failed</span>`;

                if (r.input) {
                    html += `<div class="result-input">Input: ${this.escapeHtml(r.input)}</div>`;
                }

                if (r.expected && r.expected !== 'N/A') {
                    html += `<div class="result-expected">Expected: ${this.escapeHtml(r.expected)}</div>`;
                }

                if (r.actual) {
                    html += `<div class="result-actual">Actual: ${this.escapeHtml(r.actual)}</div>`;
                }

                if (r.error) {
                    html += `<div class="result-error">Error: ${this.escapeHtml(r.error)}</div>`;
                }

                item.innerHTML = html;
            }

            this.resultsList.appendChild(item);
        });
    }

    async toggleSolved() {
        if (!this.currentProblem) return;

        const isSolved = !this.currentProblem.solved;
        const action = isSolved ? 'mark_solved' : 'mark_unsolved';
        const problemId = this.currentProblem.id || this.currentProblem.frontend_id;
        const code = this.getEditorValue();

        try {
            await fetch('/api/progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: action,
                    problem_id: problemId,
                    code: code
                })
            });

            // Update local state
            this.currentProblem.solved = isSolved;

            // Hide draft badge when marking solved
            if (this.draftBadge && isSolved) this.draftBadge.style.display = 'none';

            // Update problem in list
            const problem = this.problems.find(p => p.id === this.currentProblem.id);
            if (problem) {
                problem.solved = isSolved;
            }

            this.updateSolvedButton(isSolved);
            this.filterProblems(); // Refresh list to show checkmark

            // Notify roadmap of progress change
            if (this.roadmap) {
                this.roadmap.updateProgress();
            }

        } catch (error) {
            console.error('Failed to update progress:', error);
        }
    }

    updateSolvedButton(isSolved) {
        if (isSolved) {
            this.solvedBtn.classList.add('solved');
            this.solvedBtn.textContent = '✓';
            this.solvedBtn.title = 'Mark as unsolved';
        } else {
            this.solvedBtn.classList.remove('solved');
            this.solvedBtn.textContent = '';
            this.solvedBtn.title = 'Mark as solved';
        }
    }

    openSettings() {
        this.apiKeyInput.value = this.apiKey || '';
        this.settingsModal.style.display = 'flex';
    }

    closeSettings() {
        this.settingsModal.style.display = 'none';
    }

    saveApiKey() {
        const key = this.apiKeyInput.value.trim();
        if (key) {
            this.apiKey = key;
            localStorage.setItem('openrouter_api_key', key);
            this.closeSettings();
            this.showToast('API key saved', 'success');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    isProblemSolved(problemId) {
        // Check if problem is in the solved list
        const pid = String(problemId);
        return this.problems.some(p => String(p.id) === pid && p.solved);
    }

    async getNextHint() {
        if (!this.currentProblem) return;

        const nextLevel = this.hintLevel + 1;
        if (nextLevel > 3) {
            // All hints revealed — re-open modal showing hint 3
            if (this.currentHints[2]) {
                this.showHintModal(this.currentHints[2], 3);
            } else {
                this.showToast('All 3 hints have already been revealed', 'info');
            }
            return;
        }

        this.hintBtn.disabled = true;
        const hintIcon = this.hintBtn.querySelector('.btn-icon');
        if (hintIcon) hintIcon.textContent = '⟳';

        // Open modal immediately with a skeleton so it feels instant
        const modal = document.getElementById('hintModal');
        document.getElementById('hintModalContent').innerHTML = this.getHintSkeleton();
        this.viewingHintLevel = nextLevel;
        this.updateHintDots();
        this.updateHintNavButtons();
        modal.style.display = 'flex';

        try {
            await this._fetchHintAtLevel(nextLevel, false);
        } finally {
            this.hintBtn.disabled = false;
            if (hintIcon) hintIcon.textContent = '💡';
        }
    }

    showHintModal(hint, level) {
        const modal = document.getElementById('hintModal');
        const content = document.getElementById('hintModalContent');

        this.viewingHintLevel = level;
        content.innerHTML = `<div class="hint-modal-body">${this.renderHintContent(hint)}</div>`;
        this.updateHintDots();
        this.updateHintNavButtons();
        modal.style.display = 'flex';
    }

    async regenerateHints() {
        if (!this.currentProblem) return;
        this.hintLevel = 0;
        this.viewingHintLevel = 1;
        this.currentHints = [];
        this.updateHintButton();
        document.getElementById('hintModalContent').innerHTML = this.getHintSkeleton();
        await this._fetchHintAtLevel(1, true);
    }

    renderHintContent(text) {
        // Convert markdown code blocks to HTML
        let result = text;

        // Replace code blocks with pre/code tags
        result = result.replace(/```python\n([\s\S]*?)```/g, (match, code) => {
            return `<pre class="hint-code-block"><code>${this.escapeHtml(code.trim())}</code></pre>`;
        });

        result = result.replace(/```\n([\s\S]*?)```/g, (match, code) => {
            return `<pre class="hint-code-block"><code>${this.escapeHtml(code.trim())}</code></pre>`;
        });

        // Replace inline code with code tags
        result = result.replace(/`([^`]+)`/g, '<code class="hint-inline-code">$1</code>');

        // Convert newlines to <br> for non-code text
        result = result.replace(/\n/g, '<br>');

        return result;
    }

    clearHints() {
        this.hintLevel = 0;
        this.currentHints = [];
    }

    async regenerateCurrentHint() {
        if (!this.currentProblem) return;
        const level = this.viewingHintLevel || 1;
        // Clear cached hint for this level so it will be re-fetched
        this.currentHints[level - 1] = '';
        document.getElementById('hintModalContent').innerHTML = this.getHintSkeleton();
        const btn = document.getElementById('hintNewAngleBtn');
        if (btn) { btn.disabled = true; btn.textContent = '⟳ Generating…'; }
        try {
            await this._fetchHintAtLevel(level, true);
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = '🔄 New Angle'; }
        }
    }

    navigateToPrevHint() {
        if (this.viewingHintLevel <= 1) return;
        const newLevel = this.viewingHintLevel - 1;
        if (this.currentHints[newLevel - 1]) {
            this.viewingHintLevel = newLevel;
            this.showHintModal(this.currentHints[newLevel - 1], newLevel);
        }
    }

    async navigateToNextHint() {
        const newLevel = this.viewingHintLevel + 1;
        if (newLevel > 3) return;

        if (this.currentHints[newLevel - 1]) {
            // Already fetched — just show it
            this.viewingHintLevel = newLevel;
            this.showHintModal(this.currentHints[newLevel - 1], newLevel);
        } else {
            // Need to fetch
            document.getElementById('hintModalContent').innerHTML = this.getHintSkeleton();
            this.viewingHintLevel = newLevel;
            this.updateHintDots();
            this.updateHintNavButtons();
            const btn = document.getElementById('hintNextBtn');
            if (btn) btn.disabled = true;
            try {
                await this._fetchHintAtLevel(newLevel, false);
            } finally {
                if (btn) btn.disabled = false;
            }
        }
    }

    applyHintToEditor() {
        const level = this.viewingHintLevel;
        const hint = this.currentHints[level - 1];
        if (!hint) return;

        // Extract raw code without markdown fences
        let code = hint;
        const fenced = hint.match(/```(?:python)?\n([\s\S]*?)```/);
        if (fenced) {
            code = fenced[1].trim();
        }

        this.setEditorValue(code);
        this.focusEditor();
        document.getElementById('hintModal').style.display = 'none';
        this.showToast('Hint inserted into editor', 'success');
    }

    resetCode() {
        if (!this.currentProblem) return;
        if (!confirm('Reset editor to starter code? Your current code will be lost.')) return;
        this.loadStarterCode(this.currentProblem);
        if (this.draftBadge) this.draftBadge.style.display = 'none';
        this.showToast('Editor reset to starter code', 'info');
    }

    async _fetchHintAtLevel(level, regenerate) {
        if (!this.currentProblem) return;
        const problemId = String(this.currentProblem.id || this.currentProblem.frontend_id);
        const problemTitle = this.currentProblem.title || '';
        const problemDescription = (this.currentProblem.content || this.currentProblem.description || '').substring(0, 3000);
        const snippets = this.currentProblem.code_snippets || [];
        const pythonSnippet = snippets.find(s => s.lang === 'python3' || s.lang === 'python');
        const starterCode = pythonSnippet ? pythonSnippet.code : '';

        try {
            const response = await fetch('/api/hints', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    problem_id: problemId,
                    hint_level: level,
                    regenerate,
                    problem_title: problemTitle,
                    problem_description: problemDescription,
                    starter_code: starterCode
                })
            });

            if (!response.ok) {
                const err = await response.text();
                this.showToast(`Hint error: server returned ${response.status}`, 'error');
                document.getElementById('hintModalContent').innerHTML =
                    `<div class="hint-modal-body" style="color:var(--error)">Failed to load hint. Please try again.</div>`;
                return;
            }

            const result = await response.json();
            if (result.error) {
                this.showToast('Hint error: ' + result.error, 'error');
                document.getElementById('hintModalContent').innerHTML =
                    `<div class="hint-modal-body" style="color:var(--error)">${this.escapeHtml(result.error)}</div>`;
                return;
            }

            if (result.hint) {
                // Track max fetched level
                if (level > this.hintLevel) this.hintLevel = level;
                while (this.currentHints.length < level) this.currentHints.push('');
                this.currentHints[level - 1] = result.hint;
                this.updateHintButton();

                // Render in the open modal
                const content = document.getElementById('hintModalContent');
                if (content) {
                    content.innerHTML = `<div class="hint-modal-body">${this.renderHintContent(result.hint)}</div>`;
                }
                this.viewingHintLevel = level;
                this.updateHintDots();
                this.updateHintNavButtons();
            }
        } catch (error) {
            console.error('Failed to get hint:', error);
            this.showToast('Failed to connect to hint service', 'error');
            document.getElementById('hintModalContent').innerHTML =
                `<div class="hint-modal-body" style="color:var(--error)">Connection failed. Please try again.</div>`;
        }
    }

    updateHintButton() {
        if (!this.hintBadge) return;
        if (this.hintLevel > 0) {
            this.hintBadge.textContent = `${this.hintLevel}/3`;
            this.hintBadge.style.display = '';
        } else {
            this.hintBadge.style.display = 'none';
        }
    }

    updateHintDots() {
        const dots = document.querySelectorAll('#hintProgressDots .hint-dot');
        dots.forEach(dot => {
            const dotLevel = parseInt(dot.dataset.level, 10);
            dot.classList.toggle('revealed', dotLevel <= this.hintLevel && dotLevel !== this.viewingHintLevel);
            dot.classList.toggle('active', dotLevel === this.viewingHintLevel);
        });
    }

    updateHintNavButtons() {
        const prevBtn = document.getElementById('hintPrevBtn');
        const nextBtn = document.getElementById('hintNextBtn');
        const insertBtn = document.getElementById('hintInsertBtn');

        if (prevBtn) prevBtn.disabled = this.viewingHintLevel <= 1;

        if (nextBtn) {
            const isLastLevel = this.viewingHintLevel >= 3;
            nextBtn.disabled = isLastLevel;
            nextBtn.textContent = isLastLevel ? 'Max hints reached' : 'Next Hint →';
        }

        if (insertBtn) {
            const hasCode = this.currentHints[this.viewingHintLevel - 1];
            insertBtn.disabled = !hasCode || !this.editorExists();
        }
    }

    getHintSkeleton() {
        return `<div class="hint-skeleton">
            <div class="hint-skeleton-line"></div>
            <div class="hint-skeleton-line"></div>
            <div class="hint-skeleton-line"></div>
            <div class="hint-skeleton-line"></div>
            <div class="hint-skeleton-line"></div>
        </div>`;
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icons = { info: 'ℹ', success: '✓', error: '✗', warning: '⚠' };
        toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${this.escapeHtml(message)}</span>`;
        container.appendChild(toast);

        // Auto-remove
        const remove = () => {
            toast.classList.add('toast-hiding');
            toast.addEventListener('animationend', () => toast.remove(), { once: true });
        };
        setTimeout(remove, type === 'error' ? 5000 : 3000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new LeetCodeApp();
});
