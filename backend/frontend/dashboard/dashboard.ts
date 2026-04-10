/**
 * ELIZA SYSTEM DASHBOARD - CORE LOGIC
 * Built with pure TypeScript
 */

interface SystemStatus {
    status: string;
    uptime: string;
    version: string;
    engine: string;
}

interface LogEntry {
    id: number;
    message: string;
    timestamp: string;
}

interface PersonaList {
    personas: string[];
}

interface Task {
    id: number;
    name: string;
    status: string;
}

interface MemoryStatus {
    total_nodes: number;
    indexed_relations: number;
    last_vacuum: string;
    status: string;
}

class Dashboard {
    private currentSection: string = 'status';
    private statusInterval: number | null = null;

    constructor() {
        this.initEventListeners();
        this.showSection('status');
        this.startStatusPolling();
    }

    private initEventListeners(): void {
        const navList = document.getElementById('nav-list');
        if (navList) {
            navList.addEventListener('click', (e) => {
                const target = e.target as HTMLElement;
                if (target.tagName === 'LI') {
                    const section = target.getAttribute('data-section');
                    if (section) this.showSection(section);
                }
            });
        }

        const btnExecute = document.getElementById('btn-execute');
        if (btnExecute) {
            btnExecute.addEventListener('click', () => this.executeApiTest());
        }
    }

    private async showSection(sectionId: string): Promise<void> {
        this.currentSection = sectionId;

        // Update Nav UI
        const navItems = document.querySelectorAll('.sidebar li');
        navItems.forEach(item => {
            if (item.getAttribute('data-section') === sectionId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Hide all sections
        const sections = document.querySelectorAll('main section');
        sections.forEach(s => (s as HTMLElement).style.display = 'none');

        // Show selected section
        const activeSection = document.getElementById(`section-${sectionId}`);
        if (activeSection) activeSection.style.display = 'block';

        // Load data based on section
        switch (sectionId) {
            case 'personas': await this.fetchPersonas(); break;
            case 'tasks': await this.fetchTasks(); break;
            case 'memory': await this.fetchMemoryStatus(); break;
            case 'logs': await this.fetchLogs(); break;
        }
    }

    private startStatusPolling(): void {
        this.fetchStatus(); // Initial fetch
        this.statusInterval = window.setInterval(() => this.fetchStatus(), 2000);
    }

    private async fetchStatus(): Promise<void> {
        try {
            const response = await fetch('/api/status');
            const data: SystemStatus = await response.json();
            
            this.updateElement('stat-status', data.status);
            this.updateElement('stat-uptime', data.uptime);
            this.updateElement('stat-version', data.version);
            this.updateElement('stat-engine', data.engine);
            
            const connIndicator = document.getElementById('connection-status');
            if (connIndicator) {
                connIndicator.innerText = 'SYSTEM ONLINE';
                connIndicator.style.color = '#10b981';
            }
        } catch (error) {
            console.error('Status fetch failed', error);
            const connIndicator = document.getElementById('connection-status');
            if (connIndicator) {
                connIndicator.innerText = 'SYSTEM OFFLINE';
                connIndicator.style.color = '#ef4444';
            }
        }
    }

    private async fetchPersonas(): Promise<void> {
        try {
            const response = await fetch('/api/personas');
            const data: PersonaList = await response.json();
            const list = document.getElementById('personas-list');
            if (list) {
                list.innerHTML = data.personas.map(p => `<div class="list-item">${p}</div>`).join('');
            }
        } catch (error) {
            console.error('Personas fetch failed', error);
        }
    }

    private async fetchTasks(): Promise<void> {
        try {
            const response = await fetch('/api/tasks');
            const data: { tasks: Task[] } = await response.json();
            const body = document.getElementById('tasks-body');
            if (body) {
                body.innerHTML = data.tasks.map(t => `
                    <tr>
                        <td>${t.id}</td>
                        <td>${t.name}</td>
                        <td style="color: ${t.status === 'completed' ? '#10b981' : '#f59e0b'}">${t.status.toUpperCase()}</td>
                    </tr>
                `).join('');
            }
        } catch (error) {
            console.error('Tasks fetch failed', error);
        }
    }

    private async fetchMemoryStatus(): Promise<void> {
        try {
            const response = await fetch('/api/memory/status');
            const data: MemoryStatus = await response.json();
            this.updateElement('mem-nodes', data.total_nodes.toString());
            this.updateElement('mem-relations', data.indexed_relations.toString());
            this.updateElement('mem-status', data.status.toUpperCase());
        } catch (error) {
            console.error('Memory fetch failed', error);
        }
    }

    private async fetchLogs(): Promise<void> {
        try {
            const response = await fetch('/api/logs');
            const data: { logs: LogEntry[] } = await response.json();
            const viewer = document.getElementById('log-viewer');
            if (viewer) {
                viewer.innerHTML = data.logs.map(l => `[${l.timestamp}] ${l.message}`).join('<br>');
                viewer.scrollTop = viewer.scrollHeight;
            }
        } catch (error) {
            console.error('Logs fetch failed', error);
        }
    }

    private async executeApiTest(): Promise<void> {
        const endpoint = (document.getElementById('api-endpoint') as HTMLInputElement).value;
        const method = (document.getElementById('api-method') as HTMLSelectElement).value;
        const payloadStr = (document.getElementById('api-payload') as HTMLTextAreaElement).value;
        const responsePre = document.getElementById('api-response');

        if (!responsePre) return;

        responsePre.innerText = 'Executing...';

        try {
            const options: RequestInit = { method };
            if (method === 'POST' && payloadStr) {
                options.headers = { 'Content-Type': 'application/json' };
                options.body = payloadStr;
            }

            const response = await fetch(endpoint, options);
            const data = await response.json();
            responsePre.innerText = JSON.stringify(data, null, 2);
        } catch (error) {
            responsePre.innerText = `Error: ${error}`;
        }
    }

    private updateElement(id: string, value: string): void {
        const el = document.getElementById(id);
        if (el) el.innerText = value;
    }
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    // Ensure sidebar exists
    let sidebar = document.querySelector('.sidebar');
    if (!sidebar) {
        sidebar = document.createElement('div');
        sidebar.className = 'sidebar';
        document.body.appendChild(sidebar);
    }
    // Ensure nav-list exists
    let navList = document.getElementById('nav-list');
    if (!navList) {
        navList = document.createElement('ul');
        navList.id = 'nav-list';
        sidebar.appendChild(navList);
    }

    new Dashboard();
});
