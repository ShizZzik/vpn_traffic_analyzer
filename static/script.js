document.addEventListener("DOMContentLoaded", () => {
    const tbody = document.getElementById("trafficBody");
    const errorDiv = document.getElementById("error");
    const table = document.getElementById("trafficTable");
    const themeToggle = document.getElementById("themeToggle");
    const toggleDataReceived = document.getElementById("toggleDataReceived");
    const toggleDataSent = document.getElementById("toggleDataSent");
    let sortDirection = {};
    let currentTheme = localStorage.getItem("theme") || "dark";  // Тёмная тема по умолчанию
    let columnVisibility = {
        "dataReceived": toggleDataReceived.checked,
        "dataSent": toggleDataSent.checked
    };

    document.body.classList.toggle("dark-theme", currentTheme === "dark");
    themeToggle.textContent = currentTheme === "dark" ? "Светлая тема" : "Тёмная тема";

    themeToggle.addEventListener("click", () => {
        currentTheme = currentTheme === "light" ? "dark" : "light";
        document.body.classList.toggle("dark-theme");
        themeToggle.textContent = currentTheme === "dark" ? "Светлая тема" : "Тёмная тема";
        localStorage.setItem("theme", currentTheme);
    });

    fetch("/api/traffic")
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data.length === 0) {
                errorDiv.textContent = "Данные не найдены. Проверьте конфигурацию сервера или users.json.";
                return;
            }
            renderTable(data);

            table.querySelectorAll("th[data-sort]").forEach(th => {
                th.addEventListener("click", () => {
                    const key = th.getAttribute("data-sort");
                    sortDirection[key] = !sortDirection[key];
                    const sortedData = [...data].sort((a, b) => {
                        const aVal = a[key] || (key === "latestHandshakeTimestamp" ? 0 : "");
                        const bVal = b[key] || (key === "latestHandshakeTimestamp" ? 0 : "");
                        if (key === "transferRx" || key === "transferTx") {
                            const aBytes = parseBytes(aVal);
                            const bBytes = parseBytes(bVal);
                            return sortDirection[key] ? aBytes - bBytes : bBytes - aBytes;
                        }
                        if (key === "latestHandshakeTimestamp") {
                            return sortDirection[key] ? aVal - bVal : bVal - aVal;
                        }
                        return sortDirection[key] ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                    });
                    renderTable(sortedData);
                    updateColumnVisibility("dataReceived", columnVisibility["dataReceived"]);
                    updateColumnVisibility("dataSent", columnVisibility["dataSent"]);
                });
            });

            toggleDataReceived.addEventListener("change", () => {
                columnVisibility["dataReceived"] = toggleDataReceived.checked;
                updateColumnVisibility("dataReceived", toggleDataReceived.checked);
            });
            toggleDataSent.addEventListener("change", () => {
                columnVisibility["dataSent"] = toggleDataSent.checked;
                updateColumnVisibility("dataSent", toggleDataSent.checked);
            });
            updateColumnVisibility("dataReceived", columnVisibility["dataReceived"]);
            updateColumnVisibility("dataSent", columnVisibility["dataSent"]);
        })
        .catch(error => {
            errorDiv.textContent = `Ошибка загрузки данных: ${error.message}`;
            console.error("Fetch error:", error);
        });

    function parseBytes(value) {
        const units = { "B": 1, "KiB": 1024, "MiB": 1024 * 1024, "GiB": 1024 * 1024 * 1024 };
        const match = value.match(/^([\d.]+)\s*([A-Za-z]+)$/);
        if (!match) return 0;
        const num = parseFloat(match[1]);
        const unit = match[2];
        return num * (units[unit] || 1);
    }

    function formatBytes(bytes) {
        if (bytes === 0) return "0 B";
        const units = ["B", "KiB", "MiB", "GiB"];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
    }

    function formatHandshake(timestamp) {
        if (timestamp === 0) return "Нет активности";
        const now = Math.floor(Date.now() / 1000);
        const delta = now - timestamp;
        const hours = Math.floor(delta / 3600);
        const minutes = Math.floor((delta % 3600) / 60);
        const seconds = delta % 60;
        return `<span class="time-hours">${hours}h</span>, <span class="time-minutes">${minutes}m</span>, <span class="time-seconds">${seconds}s ago</span>`;
    }

    function renderTable(data) {
        tbody.innerHTML = "";
        data.forEach(user => {
            const endpointParts = user.endpoint.split(":");
            const endpointHTML = endpointParts.length > 1 
                ? `<span class="ip-address">${endpointParts[0]}</span>:<span class="endpoint-port">${endpointParts[1]}</span>`
                : user.endpoint;
            const handshakeHTML = formatHandshake(user.latestHandshakeTimestamp);
            const now = Math.floor(Date.now() / 1000);
            const delta = now - user.latestHandshakeTimestamp;
            const isRecent = delta < 900;  // 15 минут
            const rowClass = delta > 3600 ? "old-handshake" : "";

            const row = document.createElement("tr");
            row.className = rowClass;
            row.innerHTML = `
                <td class="avatar-cell">
                    <div class="avatar-wrapper">
                        <img src="/static/avatars/${user.safeClientId}.png" alt="Аватар" class="avatar${isRecent ? ' online' : ''}" onerror="this.src='/static/avatars/default.png'">
                    </div>
                </td>
                <td><a href="/user/${encodeURIComponent(user.clientName)}">${user.clientName}</a></td>
                <td><span class="ip-address">${user.allowedIps}</span></td>
                <td class="traffic-in toggleable" data-column="dataReceived">${user.dataReceived}</td>
                <td class="traffic-out toggleable" data-column="dataSent">${user.dataSent}</td>
                <td class="traffic-in">${user.transferRx}</td>
                <td class="traffic-out">${user.transferTx}</td>
                <td>${handshakeHTML}</td>
                <td>${endpointHTML}</td>
            `;
            tbody.appendChild(row);
        });

        const totalClients = data.length;
        const totalRx = data.reduce((sum, user) => sum + parseBytes(user.transferRx), 0);
        const totalTx = data.reduce((sum, user) => sum + parseBytes(user.transferTx), 0);

        const totalRow = document.createElement("tr");
        totalRow.className = "total-row";
        totalRow.innerHTML = `
            <td colspan="2">Всего клиентов: ${totalClients}</td>
            <td></td>
            <td class="toggleable" data-column="dataReceived"></td>
            <td class="toggleable" data-column="dataSent"></td>
            <td class="traffic-in">Принято: ${formatBytes(totalRx)}</td>
            <td class="traffic-out">Отправлено: ${formatBytes(totalTx)}</td>
            <td colspan="2"></td>
        `;
        tbody.appendChild(totalRow);
    }

    function updateColumnVisibility(column, isVisible) {
        document.querySelectorAll(`[data-column="${column}"]`).forEach(el => {
            el.style.display = isVisible ? "" : "none";
        });
    }
});
