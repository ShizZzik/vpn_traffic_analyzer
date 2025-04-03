document.addEventListener("DOMContentLoaded", () => {
    const tbody = document.getElementById("trafficBody");
    const errorDiv = document.getElementById("error");
    const table = document.getElementById("trafficTable");
    const themeToggle = document.getElementById("themeToggle");
    let sortDirection = {};
    let currentTheme = localStorage.getItem("theme") || "light";

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
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
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
                        const aVal = a[key] || "";
                        const bVal = b[key] || "";
                        if (key === "transferRx" || key === "transferTx") {
                            const aNum = parseFloat(aVal) || 0;
                            const bNum = parseFloat(bVal) || 0;
                            return sortDirection[key] ? aNum - bNum : bNum - aNum;
                        }
                        return sortDirection[key] ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                    });
                    renderTable(sortedData);
                });
            });
        })
        .catch(error => {
            errorDiv.textContent = `Ошибка загрузки данных: ${error.message}`;
            console.error("Fetch error:", error);
        });

    function renderTable(data) {
        tbody.innerHTML = "";
        data.forEach(user => {
            const endpointParts = user.endpoint.split(":");
            const endpointHTML = endpointParts.length > 1 
                ? `<span class="endpoint-ip">${endpointParts[0]}</span>:<span class="endpoint-port">${endpointParts[1]}</span>`
                : user.endpoint;
            const handshakeHTML = user.latestHandshake === "Нет активности"
                ? user.latestHandshake
                : `<span class="time-hours">${user.latestHandshake.split(',')[0]}</span>, <span class="time-minutes">${user.latestHandshake.split(',')[1]}</span>, <span class="time-seconds">${user.latestHandshake.split(',')[2]}</span>`;
            const row = document.createElement("tr");
            row.innerHTML = `
                <td><img src="/static/avatars/${user.clientId}.png" alt="Аватар" class="avatar" onerror="this.src='/static/avatars/default.png'"></td>
                <td><a href="/user/${encodeURIComponent(user.clientName)}">${user.clientName}</a></td>
                <td><span class="ip-address">${user.allowedIps}</span></td>
                <td class="traffic-in">${user.dataReceived}</td>
                <td class="traffic-out">${user.dataSent}</td>
                <td class="traffic-in">${user.transferRx}</td>
                <td class="traffic-out">${user.transferTx}</td>
                <td>${handshakeHTML}</td>
                <td>${endpointHTML}</td>
            `;
            tbody.appendChild(row);
        });
    }
});
