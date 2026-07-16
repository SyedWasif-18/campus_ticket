document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // Theme Toggle Logic
    // ----------------------------------------------------
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const root = document.documentElement;
    
    // Check local storage or system preference
    const storedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    const currentTheme = storedTheme || (systemPrefersDark ? 'dark' : 'light');
    root.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);
    
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = root.getAttribute('data-theme') === 'dark';
            const newTheme = isDark ? 'light' : 'dark';
            root.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
            
            // Re-render Chart.js if present
            if (typeof Chart !== 'undefined') {
                Chart.instances.forEach(chart => {
                    const isNowDark = newTheme === 'dark';
                    const textColor = isNowDark ? '#94a3b8' : '#475569';
                    const gridColor = isNowDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)';
                    
                    if (chart.options.plugins && chart.options.plugins.legend) {
                        chart.options.plugins.legend.labels.color = textColor;
                    }
                    if (chart.options.scales && chart.options.scales.x && chart.options.scales.x.ticks) {
                        chart.options.scales.x.ticks.color = textColor;
                        if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = gridColor;
                    }
                    if (chart.options.scales && chart.options.scales.y && chart.options.scales.y.ticks) {
                        chart.options.scales.y.ticks.color = textColor;
                        if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = gridColor;
                    }
                    chart.update();
                });
            }
        });
    }
    
    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'dark') {
            themeIcon.classList.remove('bi-moon-fill');
            themeIcon.classList.add('bi-sun-fill');
        } else {
            themeIcon.classList.remove('bi-sun-fill');
            themeIcon.classList.add('bi-moon-fill');
        }
    }

    // ----------------------------------------------------
    // Sidebar Mobile Toggle
    // ----------------------------------------------------
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
                if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                    sidebar.classList.remove('open');
                }
            }
        });
    }

    // ----------------------------------------------------
    // Auto-dismiss Flash Messages
    // ----------------------------------------------------
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.animation = 'fadeOut 0.4s forwards';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // ----------------------------------------------------
    // WebSockets / Notifications Logic
    // ----------------------------------------------------
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = wsProtocol + window.location.host + '/ws/notifications/';
    let socket;
    
    function connectWebSocket() {
        socket = new WebSocket(wsUrl);
        
        socket.onopen = function(e) {
            console.log("[WebSocket] Connected successfully");
        };
        
        socket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            console.log("[WebSocket] Message received:", data);
            
            // Show toast notification
            showToast(data.message, data.ticket_id);
            
            // Update nav badges
            updateNotificationBadges();
            
            // If on attender dashboard, update the live feed
            if (document.getElementById('pending-tickets-table')) {
                handleAttenderLiveFeed(data);
            }
        };
        
        socket.onclose = function(e) {
            console.log("[WebSocket] Disconnected. Reconnecting in 3s...");
            setTimeout(connectWebSocket, 3000);
        };
    }
    
    // Only connect if user is authenticated (indicated by existence of sidebar footer/badge)
    if (document.querySelector('.sidebar-footer')) {
        connectWebSocket();
    }
    
    function showToast(message, ticketId) {
        const container = document.getElementById('ws-toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = 'ws-toast';
        
        // Default URL path based on presence of a template variable. 
        // Fallback gracefully.
        let linkHtml = '';
        if (ticketId) {
            // Using a generic URL path structure. Real links are better built using Django template injection.
            linkHtml = `<a href="/tickets/${ticketId}/" style="font-size: 0.8rem; margin-top: 4px; display: inline-block;">View Ticket</a>`;
        }
        
        toast.innerHTML = `
            <div style="font-size: 1.5rem; color: var(--primary);">
                <i class="bi bi-info-circle-fill"></i>
            </div>
            <div style="flex: 1;">
                <p style="font-size: 0.875rem; margin-bottom: 2px;">${message}</p>
                ${linkHtml}
            </div>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: var(--text-muted); cursor: pointer; align-self: flex-start;">
                <i class="bi bi-x-lg"></i>
            </button>
        `;
        
        container.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            if(toast.parentElement) {
                toast.style.animation = 'fadeOut 0.4s forwards';
                setTimeout(() => toast.remove(), 400);
            }
        }, 6000);
    }
    
    function updateNotificationBadges() {
        const notifBadge = document.getElementById('notif-badge');
        const sidebarBadge = document.getElementById('sidebar-badge');
        
        if (notifBadge) notifBadge.style.display = 'block';
        if (sidebarBadge) {
            sidebarBadge.style.display = 'inline-block';
            let current = parseInt(sidebarBadge.innerText) || 0;
            sidebarBadge.innerText = current + 1;
        }
    }
    
    function handleAttenderLiveFeed(data) {
        const tbody = document.getElementById('pending-tbody');
        const emptyMsg = document.getElementById('no-pending-msg');
        const countBadge = document.getElementById('pending-count-badge');
        const kpiPending = document.getElementById('kpi-pending');
        
        // If a ticket is accepted/cancelled, remove it from the pending table
        if (data.action === 'LOCK' || data.action === 'CANCEL') {
            const row = document.getElementById(`ticket-row-${data.ticket_id}`);
            if (row) {
                row.remove();
                updateCounts(-1);
            }
        }
        
        if (data.action === 'CREATE') {
            updateCounts(1);
            if (emptyMsg) emptyMsg.style.display = 'none';
            
            if (data.ticket_data) {
                const tr = document.createElement('tr');
                tr.className = 'table-row-animate';
                tr.id = `ticket-row-${data.ticket_id}`;
                
                let descHtml = data.ticket_data.description ? `<small class="text-muted">${data.ticket_data.description.substring(0, 40)}</small>` : '';
                
                tr.innerHTML = `
                    <td><span class="ticket-id">#${data.ticket_data.id}</span></td>
                    <td>
                        <div class="ticket-category">
                            <span class="category-dot cat-${data.ticket_data.category_class}"></span>
                            ${data.ticket_data.sub_category}
                        </div>
                        ${descHtml}
                    </td>
                    <td>${data.ticket_data.room_number}</td>
                    <td><span class="priority-badge priority-${data.ticket_data.priority_class}">${data.ticket_data.priority_display}</span></td>
                    <td>${data.ticket_data.faculty_name}</td>
                    <td>Just now</td>
                    <td>
                        <a href="/tickets/${data.ticket_id}/accept/" class="btn btn-primary-sm">
                            <i class="bi bi-check2-circle"></i> Accept
                        </a>
                        <a href="/tickets/${data.ticket_id}/" class="btn btn-ghost-sm">
                            <i class="bi bi-eye-fill"></i>
                        </a>
                    </td>
                `;
                tbody.insertBefore(tr, tbody.firstChild);
            } else {
                const tr = document.createElement('tr');
                tr.className = 'table-row-animate';
                tr.innerHTML = `
                    <td colspan="7" style="text-align: center; color: var(--primary);">
                        <i class="bi bi-arrow-clockwise"></i> New ticket raised! Please refresh the page to view details.
                    </td>
                `;
                tbody.insertBefore(tr, tbody.firstChild);
            }
        }
        
        function updateCounts(diff) {
            let current = parseInt(countBadge.innerText) || 0;
            let newVal = current + diff;
            if (newVal < 0) newVal = 0;
            if (countBadge) countBadge.innerText = newVal;
            if (kpiPending) kpiPending.innerText = newVal;
            
            if (newVal === 0 && tbody && tbody.children.length === 0 && emptyMsg) {
                emptyMsg.style.display = 'block';
            }
        }
    }
});
